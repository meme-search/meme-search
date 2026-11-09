require "test_helper"
require "rake"

class EmbeddingsRakeTest < ActiveSupport::TestCase
  setup do
    Rails.application.load_tasks unless Rake::Task.task_defined?("embeddings:rebuild")
    @task = Rake::Task["embeddings:rebuild"]
    @original_model = $embedding_model
    # A constant vector proves each snippet was embedded again by the current model.
    $embedding_model = ->(_snippet) { Array.new(384, 0.5) }
  end

  teardown do
    $embedding_model = @original_model
    @task.reenable
  end

  test "rebuild replaces the embeddings of every described meme" do
    image_cores(:two).update_column(:description, nil)
    image_cores(:three).update_column(:description, "")
    stale_ids = ImageEmbedding.where(image_core: [ image_cores(:one), image_cores(:four) ]).ids

    stdout, _stderr = capture_io { @task.invoke }

    assert_empty ImageEmbedding.where(id: stale_ids)
    [ image_cores(:one), image_cores(:four) ].each do |image_core|
      embeddings = ImageEmbedding.where(image_core: image_core)
      assert embeddings.any?
      assert embeddings.all? { |embedding| embedding.embedding == Array.new(384, 0.5) }
    end
    assert_match(%r{Rebuilt embeddings for 2/2 memes}, stdout)
  end

  test "rebuild leaves memes without a description untouched" do
    image_cores(:two).update_column(:description, nil)
    untouched_ids = ImageEmbedding.where(image_core: image_cores(:two)).ids

    capture_io { @task.invoke }

    assert_equal untouched_ids.sort, ImageEmbedding.where(image_core: image_cores(:two)).ids.sort
  end
end
