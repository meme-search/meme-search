require "test_helper"

class ModelSetupTest < ActiveSupport::TestCase
  INITIALIZER = Rails.root.join("config", "initializers", "model_setup.rb")

  setup do
    @original_model = $embedding_model
    @original_env = ENV["EMBEDDING_MODEL"]
  end

  teardown do
    $embedding_model = @original_model
    @original_env.nil? ? ENV.delete("EMBEDDING_MODEL") : ENV["EMBEDDING_MODEL"] = @original_env
  end

  test "uses the English MiniLM model when EMBEDDING_MODEL is unset" do
    ENV.delete("EMBEDDING_MODEL")

    assert_equal "sentence-transformers/all-MiniLM-L6-v2", loaded_model_name
  end

  test "treats a blank EMBEDDING_MODEL as unset" do
    ENV["EMBEDDING_MODEL"] = ""

    assert_equal "sentence-transformers/all-MiniLM-L6-v2", loaded_model_name
  end

  test "loads the model named by EMBEDDING_MODEL" do
    ENV["EMBEDDING_MODEL"] = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    assert_equal "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", loaded_model_name
  end

  private

    def loaded_model_name
      loaded = nil
      Informers.stub(:pipeline, ->(task, model) { loaded = [ task, model ] }) { load INITIALIZER }
      assert_equal "embedding", loaded.first
      loaded.last
    end
end
