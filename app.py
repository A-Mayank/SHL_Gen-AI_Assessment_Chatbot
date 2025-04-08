import streamlit as st
import json
import numpy as np
from sentence_transformers import SentenceTransformer, util
import pandas as pd
import io


# Load model + cache data
@st.cache_resource
def load_model():
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


@st.cache_data
def load_data():
    with open("shl_embeddings_cleaned.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    docs = []
    embeddings = []
    for entry in raw:
        docs.append(entry)
        embeddings.append(np.array(entry["embedding"], dtype=np.float32))

    return docs, np.stack(embeddings)


model = load_model()
docs, embeddings = load_data()

# ------------------------------
# UI Layout
# ------------------------------
st.set_page_config(
    page_title="SHL Assessment Finder",
    layout="wide",
    page_icon="🔍"
)

st.title("🧠 SHL Assessment Recommender")
st.markdown(
    "Use natural language or a job description to discover the best SHL assessments for your role."
)

col1, col2 = st.columns([2, 1])

# User input
with col1:
    query_text = st.text_area("✍️ Paste a job description or query:", height=200)
    uploaded_file = st.file_uploader("📄 ...or upload a .txt file", type=["txt"])

with col2:
    top_k = st.slider("🔢 Top N Results", 1, 10, 5)
    min_score = st.slider("📈 Minimum Similarity Score", 0.5, 1.0, 0.75, step=0.01)
    filter_remote = st.checkbox("🧪 Remote Testing Only", value=False)
    filter_adaptive = st.checkbox("📊 Adaptive/IRT Only", value=False)


# ------------------------------
# Helper: Run search
# ------------------------------
def find_best_matches(user_query, top_k=5, min_score=0.75):
    query_embedding = model.encode(user_query, convert_to_tensor=True)
    scores = util.cos_sim(query_embedding, embeddings)[0].cpu().numpy()
    sorted_indices = scores.argsort()[::-1]

    seen = set()
    results = []

    for idx in sorted_indices:
        doc = docs[idx]
        if (doc["name"], doc["url"]) in seen:
            continue
        seen.add((doc["name"], doc["url"]))

        score = float(scores[idx])
        if score < min_score:
            continue
        if filter_remote and doc.get("remote_testing", "").lower() != "yes":
            continue
        if filter_adaptive and doc.get("adaptive_irt", "").lower() != "yes":
            continue

        results.append(
            {
                "name": doc["name"],
                "url": doc["url"],
                "score": score,
                "description": doc.get("description", ""),
                "duration": doc.get("duration", ""),
                "test_type": doc.get("test_type", ""),
                "remote_testing": doc.get("remote_testing", ""),
                "adaptive_irt": doc.get("adaptive_irt", ""),
            }
        )

        if len(results) == top_k:
            break

    return results


# ------------------------------
# Trigger search
# ------------------------------
if st.button("🔍 Find Recommendations"):
    query = query_text.strip()

    if uploaded_file and not query:
        query = uploaded_file.read().decode("utf-8")

    if not query:
        st.warning("Please enter a query or upload a file.")
    else:
        with st.spinner("Thinking..."):
            results = find_best_matches(query, top_k=top_k, min_score=min_score)

        if not results:
            st.error("No relevant assessments found.")
        else:
            st.success(f"Top {len(results)} assessments matched!")

            # Display results
            for res in results:
                with st.container():
                    st.markdown(f"### 🔹 [{res['name']}]({res['url']})")
                    col1, col2, col3 = st.columns(3)
                    col1.markdown(f"⏱️ **Duration**: {res['duration']}")
                    col2.markdown(f"🔬 **Type**: {res['test_type']}")
                    col3.markdown(f"📈 **Score**: {res['score']:.2f}")
                    st.markdown(
                        f"🛰️ **Remote Testing**: {res['remote_testing']} | 🧠 **IRT**: {res['adaptive_irt']}"
                    )
                    st.markdown(f"*{res['description']}*")
                    st.markdown("---")
