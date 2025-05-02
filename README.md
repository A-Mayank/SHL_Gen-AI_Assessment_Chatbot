
## Related Links

Check out our Hugging Face Space for interactive demos: [Hugging Face Space](https://huggingface.co/spaces/A-Mayank/SHLGenAI)

# SHL Assessment Recommender

This project implements a semantic search system for recommending SHL assessments based on a natural language job description or query. It leverages sentence embeddings to find the most relevant assessments from a precomputed list.

## 🔧 Implementation

### Overview

The core functionality of the script involves:

- Loading SHL assessment data with precomputed sentence embeddings from a JSON file (`shl_embeddings_cleaned.json`).
- Using the `all-MiniLM-L6-v2` model from [SentenceTransformers](https://www.sbert.net/) to encode user queries.
- Computing cosine similarity between the query and stored embeddings.
- Returning the top-k most relevant SHL assessments with associated metadata (e.g., duration, test type, remote testing availability, adaptive IRT support).

### How it Works

1. Load and parse the JSON data containing assessments and their embeddings.
2. Initialize the sentence transformer model (`all-MiniLM-L6-v2`).
3. Encode the user's query into an embedding.
4. Compute cosine similarity scores between the query and each stored assessment.
5. Return the top-k matches, filtering out duplicates by name and URL.

### Requirements

- Python 3.7+
- `sentence-transformers`
- `numpy`
- `torch`

Install dependencies:

```bash
python New_QA.py
```
## 📊 Evaluation

This recommendation system ranks SHL assessments using **cosine similarity** between the user's query and each assessment description embedding.

### 🔹 Cosine Similarity

We use the `all-MiniLM-L6-v2` model to generate embeddings for the query and assessment descriptions.

The similarity between embeddings is calculated as:

cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)


Assessments are ranked by similarity score, and the top results are returned after removing duplicates.

---

### 🔹 Accuracy Metrics

While cosine similarity is used for ranking, the system can be evaluated using two standard information retrieval metrics:

#### 1. Mean Recall@K

This measures how many of the relevant assessments are present in the top K predictions.

Recall@K = (Number of relevant assessments in Top K) / (Total relevant assessments)

Mean Recall@K = Average of Recall@K across all queries


#### 2. Mean Average Precision@K (MAP@K)

This evaluates both the relevance and the order of the results.

AP@K = (1 / min(K, R)) × sum of (Precision@k × relevance(k))

MAP@K = Average of AP@K across all queries


Where:
- `Precision@k` is the precision at rank k.
- `relevance(k) = 1` if the result at position k is relevant, otherwise 0.
- `R` is the total number of relevant results for the query.

---

### 🔹 Sample Evaluation Setup

To evaluate the model, prepare a test set like this:

```python
🔹 Customer Service Skills Test (0.87)
URL: https://www.shl.com/test-url
Duration: 20 mins | Type: Skills
Remote Testing: Yes | IRT: No







