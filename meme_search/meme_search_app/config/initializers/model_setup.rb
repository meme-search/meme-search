require "informers"

# The default stays English MiniLM so existing installs keep comparable vectors; any other model
# must also produce 384 dimensions (see ImageEmbedding), and switching needs `bin/rails embeddings:rebuild`.
embedding_model_name = ENV["EMBEDDING_MODEL"].presence || "sentence-transformers/all-MiniLM-L6-v2"
$embedding_model = Informers.pipeline("embedding", embedding_model_name)
