require "test_helper"

class ImageCoreTest < ActiveSupport::TestCase
  # The cleaning regex before multilingual support, kept to prove ASCII input is unaffected.
  LEGACY_CLEAN = ->(text) { text.downcase.strip.gsub(/[^a-z0-9,.!?']/, " ").gsub(/\s+/, " ") }

  test "a description without Latin words produces embeddings" do
    image_core = image_cores(:one)
    image_core.update_column(:description, "Скелет сидит на скамейке и ждёт")

    assert_nothing_raised { image_core.refresh_description_embeddings }

    snippets = ImageEmbedding.where(image_core_id: image_core.id).order(:id).pluck(:snippet)
    assert_equal [
      "скелет сидит на скамейке и ждёт",
      "скелет сидит на скамейке",
      "на скамейке и ждёт",
      "и ждёт"
    ], snippets
    assert ImageEmbedding.where(image_core_id: image_core.id).all? { |embedding| embedding.embedding.length == 384 }
  end

  test "chunk_text keeps Cyrillic words and handles punctuation as before" do
    chunks = ImageCore.new.send(:chunk_text, "Кот сказал: «Нет!» и ушёл, cat said no?")

    assert_equal [
      "кот сказал: «нет!» и ушёл, cat said no?",
      "кот сказал нет! и",
      "нет! и ушёл, cat",
      "ушёл, cat said no?",
      "said no?"
    ], chunks
  end

  test "clean_word keeps letters and digits of other scripts" do
    assert_equal "café 東京 2024 ½", ImageCore.new.send(:clean_word, "Café 東京 2024 ½")
  end

  test "clean_word output for ASCII input is unchanged" do
    every_ascii_char = (0..127).map(&:chr).join
    samples = [
      every_ascii_char,
      "  This image says: DID you just take BOTH pills?! (yes) #meme @user 100% ",
      "don't stop-me_now\tplease\nok."
    ]

    samples.each do |sample|
      assert_equal LEGACY_CLEAN.call(sample), ImageCore.new.send(:clean_word, sample)
    end
  end
end
