namespace :embeddings do
  desc "Recompute all description embeddings, required after changing EMBEDDING_MODEL or the snippet cleaning"
  task rebuild: :environment do
    # Vectors from different models are not comparable, so every described meme is redone, not only missing ones.
    image_cores = ImageCore.where.not(description: [ nil, "" ])
    total = image_cores.count
    done = 0

    image_cores.find_each do |image_core|
      image_core.refresh_description_embeddings
      done += 1
      puts "Rebuilt embeddings for #{done}/#{total} memes" if (done % 100).zero? || done == total
    end
    puts "No described memes to rebuild" if total.zero?
  end
end
