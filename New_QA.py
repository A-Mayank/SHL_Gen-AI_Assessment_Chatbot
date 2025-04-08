import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

# Load your embeddings JSON
with open("shl_embeddings_cleaned.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Load Hugging Face model (same one used to generate embeddings)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Convert embeddings and keep metadata
docs = []
embeddings = []

for entry in data:
    docs.append(
        {
            "name": entry["name"],
            "url": entry["url"],
            "description": entry["description"],
            "duration": entry["duration"],
            "test_type": entry["test_type"],
            "remote_testing": entry["remote_testing"],
            "adaptive_irt": entry["adaptive_irt"],
        }
    )
    embeddings.append(np.array(entry["embedding"], dtype=np.float32))

embeddings = np.stack(embeddings)


def find_best_matches(user_query, top_k=5):
    # Encode the query
    query_embedding = model.encode(user_query, convert_to_tensor=True)

    # Compute cosine similarity
    scores = util.cos_sim(query_embedding, embeddings)[0].cpu().numpy()

    # Get all indices sorted by score
    sorted_indices = scores.argsort()[::-1]

    # Collect top unique results
    results = []
    seen_names = set()
    seen_urls = set()

    for idx in sorted_indices:
        doc = docs[idx]
        name = doc["name"]
        url = doc["url"]

        if name in seen_names or url in seen_urls:
            continue  # Skip duplicate

        seen_names.add(name)
        seen_urls.add(url)

        results.append(
            {
                "name": name,
                "url": url,
                "score": float(scores[idx]),
                "duration": doc["duration"],
                "test_type": doc["test_type"],
                "remote_testing": doc["remote_testing"],
                "adaptive_irt": doc["adaptive_irt"],
            }
        )

        if len(results) == top_k:
            break

    return results


# Example
if __name__ == "__main__":
    query = "I'm hiring a customer service associate with strong communication skills and basic office management experience"
    matches = find_best_matches(query, top_k=5)

    for match in matches:
        print(f"\n🔹 {match['name']} ({match['score']:.2f})")
        print(f"URL: {match['url']}")
        print(f"Duration: {match['duration']} | Type: {match['test_type']}")
        print(
            f"Remote Testing: {match['remote_testing']} | IRT: {match['adaptive_irt']}"
        )
