require "informers"
require "net/http"
require "uri"


class ImageCore < ApplicationRecord
  DESCRIPTION_MAX_LENGTH = 500

  class FileDeletionError < StandardError; end
  class UnsafeSourceFileError < StandardError; end

  # keyword search scope
  include PgSearch::Model
  pg_search_scope :search_any_word,
                  against: [ :description ],
                  using: {
                    tsearch: { any_word: true }
                  }

  # tag association + lookup scope
  belongs_to :image_path
  has_many :image_tags, dependent: :destroy
  has_many :image_description_generation_attempts, dependent: :destroy
  has_many :image_description_bulk_operations, through: :image_description_generation_attempts
  accepts_nested_attributes_for :image_tags, allow_destroy: true

  # tag lookup scope
  scope :with_selected_tag_names, ->(selected_tag_names) {
    joins(image_tags: :tag_name)
      .where(tag_names: { name: selected_tag_names })
      .select("DISTINCT image_cores.*")
  }

  # embedding association + lookup scope
  has_many :image_embeddings, dependent: :destroy

  # embedding lookup scope
  scope :without_embeddings, -> {
    left_outer_joins(:image_embeddings).where(image_embeddings: { id: nil })
  }

  # validations
  validates_length_of :name, presence: true, minimum: 0, maximum: 100, allow_blank: false
  validates_length_of :description, minimum: 0, maximum: DESCRIPTION_MAX_LENGTH, allow_blank: true
  enum :status, [
    :not_started,
    :in_queue,
    :processing,
    :done,
    :removing,
    :failed
  ]
  validates :status, presence: true

  before_destroy :remove_image_text_job

  # before save create description embeddings
  # before_save :refresh_description_embeddings

  def self.delete_all(*args)
    ImageDescriptionGenerationAttempt.where(image_core_id: all.select(:id)).delete_all
    super
  end

  def active_description_generation_attempt
    image_description_generation_attempts.active.order(created_at: :desc).first
  end

  def start_description_generation_attempt!(provider:, provider_settings: {}, bulk_operation: nil)
    with_lock do
      active_attempt = active_description_generation_attempt
      raise ActiveRecord::RecordInvalid, active_attempt if active_attempt.present?

      image_description_generation_attempts.create!(
        provider: provider,
        provider_settings: provider_settings,
        image_description_bulk_operation: bulk_operation,
        status: :queued
      )
    end
  end

  def cancel_active_description_generation_attempt!
    attempt = active_description_generation_attempt
    return false unless attempt

    attempt.cancel!
  end

  def self.normalize_description(description)
    description.to_s.squish.truncate(DESCRIPTION_MAX_LENGTH, separator: /\s/, omission: "")
  end

  def source_file_path
    memes_root = Rails.root.join("public", "memes").cleanpath
    relative_path = Pathname.new(File.join(image_path.name.to_s, name.to_s)).cleanpath

    if relative_path.absolute? || relative_path.each_filename.any? { |segment| segment == ".." }
      raise FileDeletionError, "Refusing to access a file outside the configured meme library."
    end

    memes_root.join(relative_path).cleanpath
  end

  def safe_source_file_path
    memes_root = Rails.root.join("public", "memes").cleanpath
    path = source_file_path
    relative_path = path.relative_path_from(memes_root)
    current_path = memes_root

    relative_path.each_filename do |segment|
      current_path = current_path.join(segment)
      raise UnsafeSourceFileError, "Refusing to access a symlinked meme file." if current_path.symlink?
    end

    resolved_root = memes_root.realpath
    resolved_path = path.realpath
    root_prefix = "#{resolved_root}#{File::SEPARATOR}"
    unless resolved_path.to_s.start_with?(root_prefix) && resolved_path.file? && resolved_path.readable?
      raise UnsafeSourceFileError, "Refusing to access a file outside the configured meme library."
    end

    resolved_path
  rescue ArgumentError, Errno::ENOENT, Errno::EACCES, Errno::ELOOP, Errno::ENOTDIR, Errno::EPERM
    raise UnsafeSourceFileError, "The configured meme file is not safely accessible."
  end

  def delete_source_file!
    path = source_file_path
    return false unless path.exist?

    unless path.file?
      raise FileDeletionError, "The configured meme path is not a regular file."
    end

    path.delete
    true
  rescue Errno::EACCES, Errno::EPERM, Errno::EROFS => e
    raise FileDeletionError, "The meme file could not be deleted. Check that the mounted directory is writable. (#{e.message})"
  rescue SystemCallError => e
    raise FileDeletionError, "The meme file could not be deleted. (#{e.message})"
  end

  def remove_image_text_job
    # send request
    begin # For local / native metal testing
      uri = URI.parse("http://#{ENV["APP_HOST"]}:#{ENV["GEN_PORT"]}/remove_job/#{self.id}")
      http = Net::HTTP.new(uri.host, uri.port)

      # Try to make a request to the first URI
      request = Net::HTTP::Delete.new(uri.request_uri)
      request["Content-Type"] = "application/json"
      response = http.request(request)

      if response.is_a?(Net::HTTPSuccess)
        puts "Job removed successfully for image core #{self.id}: #{response.body}"
      else
        puts "Failed to remove job for #{self.id}: #{response.code} - #{response.body}"
      end

    rescue SocketError, Errno::ECONNREFUSED => e  # For compose runner (when app run in docker network)
      begin
        # If the connection fails, use the backup URI
        uri = URI.parse("http://image_to_text_app:8000/remove_job/#{self.id}")
        http = Net::HTTP.new(uri.host, uri.port)

        # Try to make a request to the first URI
        request = Net::HTTP::Delete.new(uri.request_uri)
        request["Content-Type"] = "application/json"
        response = http.request(request)

        if response.is_a?(Net::HTTPSuccess)
          puts "Job removed successfully for image core #{self.id}: #{response.body}"
        else
          puts "Failed to remove job for #{self.id}: #{response.code} - #{response.body}"
        end
      rescue
      end
    end
  end

  def refresh_description_embeddings
    # destroy current description embeddings
    begin
      current_embeddings = ImageEmbedding.where({ image_core_id: self.id })
      current_embeddings.map { |item| item.destroy! }
      current_embeddings = ImageEmbedding.where({ image_core_id: self.id })
    rescue StandardError => e
      puts "THE DESTROY EXCEPTION --> #{e}"
    end
    if !self.description.nil?
      if self.description.length > 0
        snippets = chunk_text(self.description)
        snippets_hash = snippets.map.with_index { |snippet, index| { image_core_id: self.id, snippet: snippet } }
        snippets_hash.map { |hash| ImageEmbedding.new(hash).save! }
      end
    end
  end

  private

    def clean_word(text)
      # clean input text - keeping only lower case letters and numbers of any script, punctuation, and single quote symbols
      cleaned_text = text.downcase.strip.gsub(/[^\p{L}\p{N},.!?']/, " ")
      cleaned_text.gsub!(/\s+/, " ")
      cleaned_text
    end

    def chunk_text(text)
      # split and clean input text
      text_split = clean_word(text).split(" ")
      text_split.reject!(&:empty?)

      # use two pointers to create chunks
      chunk_size = 4
      overlap_size = 2

      # create next chunk by moving right pointer until chunk_size is reached or line_number changes by more than 1 or end of word_sequence is reached
      left_pointer = 0
      right_pointer = chunk_size - 1
      chunks = []

      if right_pointer >= text_split.length
        chunks << text_split.join(" ")
      else
        while right_pointer < text_split.length
          # create chunk
          chunk = text_split[left_pointer..right_pointer]

          # move left pointer
          left_pointer += chunk_size - overlap_size

          # move right pointer
          right_pointer += chunk_size - overlap_size

          # store chunk
          chunks << chunk.join(" ")
        end

        # check if there is final chunk
        if left_pointer < text_split.length
          last_chunk = text_split[left_pointer..-1]
          chunks << last_chunk.join(" ")
        end
      end

      # insert the full text
      if chunks.length > 1
        chunks.insert(0, text.downcase)
      end

      chunks
    end
end
