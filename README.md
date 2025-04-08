# 🧠 SHL Assessment Recommender (GenAI + Streamlit)

This is a **GenAI-powered SHL assessment recommendation tool** built with **Hugging Face embeddings**, **Streamlit**, and **semantic similarity search**.

Give it a **job description** or **natural language query**, and it will recommend the most relevant SHL assessments.

---

## 🚀 Live Demo

🔗 [Hugging Face Spaces](https://huggingface.co/spaces/A-Mayank/SHLGenAI))

---

## 🧩 Features

- 🔍 Semantic search using `sentence-transformers/all-MiniLM-L6-v2`
- 📥 Upload `.txt` job descriptions or paste text
- 🎯 Returns top-N relevant SHL assessments
- ✅ Shows:
  - Assessment name (with link)
  - Description
  - Duration, Test Type
  - Remote Testing Support
  - Adaptive IRT Support

```bash
git clone https://github.com/A-Mayank/SHL_Gen-AI_Assessment_Chatbot
cd shl-assessment-bot
pip install -r requirements.txt
streamlit run app.py
