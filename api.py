from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer, util
import numpy as np
import json

app = FastAPI(title="SHL Assessment Recommender API")

# Load model and data once
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

with open("shl_embeddings_cleaned.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

docs = []
embeddings = []

for entry in raw_data:
    docs.append(entry)
    embeddings.append(np.array(entry["embedding"], dtype=np.float32))

embeddings = np.stack(embeddings)


# Define response model
class Assessment(BaseModel):
    name: str
    url: str
    duration: str
    test_type: str
    remote_testing: str
    adaptive_irt: str
    score: float


@app.get("/recommend", response_model=List[Assessment])
def recommend_assessments(
    query: str = Query(..., description="Natural language query or JD"),
    top_k: int = Query(5, ge=1, le=10, description="Number of results to return"),
    min_score: float = Query(
        0.5, ge=0.0, le=1.0, description="Minimum cosine similarity score"
    ),
):
    query_embedding = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_embedding, embeddings)[0].cpu().numpy()
    sorted_indices = scores.argsort()[::-1]

    seen = set()
    results = []

    for idx in sorted_indices:
        doc = docs[idx]
        name_url = (doc["name"], doc["url"])
        if name_url in seen:
            continue
        seen.add(name_url)

        score = float(scores[idx])
        if score < min_score:
            continue

        results.append(
            Assessment(
                name=doc["name"],
                url=doc["url"],
                duration=doc.get("duration", ""),
                test_type=doc.get("test_type", ""),
                remote_testing=doc.get("remote_testing", ""),
                adaptive_irt=doc.get("adaptive_irt", ""),
                score=score,
            )
        )

        if len(results) >= top_k:
            break

    return results
