# 🚀 DTU GPT

> AI-powered exam assistant for DTU students — built using LLMs + retrieval systems

---

## 📌 Problem Statement

Students often struggle with:

* Identifying **important exam topics**
* Practicing **relevant questions**
* Understanding concepts **quickly before exams**

DTU GPT solves this by combining **AI + previous year paper analysis** to provide **targeted exam preparation**.

---

## ✨ Key Features

* 💬 Chat-based academic assistant
* 📊 **Trend Analysis Mode** – identifies frequently asked topics
* ❓ **Question Prediction Mode** – generates expected exam questions
* 📖 **Explanation Mode** – concise, exam-focused concepts
* 📄 PDF ingestion for PYQs
* ⚡ Semantic search using **FAISS + embeddings**
* 🔐 Authentication with Clerk
* 📱 Responsive UI + chat history persistence

---

## 🧠 Tech Stack

**Frontend**

* React + Vite
* Tailwind CSS
* Clerk Authentication

**Backend**

* FastAPI
* LangChain + Groq
* Sentence Transformers
* FAISS (vector search)
* MongoDB (data storage)

---

## 🏗️ System Architecture

DTU GPT follows a **Retrieval-Augmented Generation (RAG)** architecture:

1. 📄 PDFs (PYQs) are processed and embedded
2. 🧠 Stored in FAISS + MongoDB
3. 🔍 User query → semantic search
4. 🤖 LLM (Groq) generates contextual response

This ensures:

* Accurate answers
* Exam-relevant context
* Fast response time

---

## ⚙️ Setup (Quick Start)

```bash
git clone https://github.com/gauravkumar1364/Dtugpt.git
cd Dtugpt
```

### Backend

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Create `.env`:

```
MONGODB_URL=your_mongodb_atlas_url
GROQ_API_KEY=your_groq_api_key
```

---

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

---

## 🔌 Core API

* `POST /chat` → Main assistant
* `POST /uploadfile` → Upload PYQs
* `GET /stats` → Topic analytics

---

## 🚀 Deployment

* Backend: Render
* Frontend: Vercel 

---

## 📈 Highlights

* Designed a **multi-mode AI assistant** (analysis, prediction, explanation)
* Implemented **RAG pipeline** with FAISS + embeddings
* Built **scalable backend with FastAPI**
* Optimized for **low-latency responses**
* Integrated **real-world academic data (PYQs)**

---

## 👨‍💻 Author

**Gaurav Kumar**
🔗 https://github.com/gauravkumar1364

---

## ⭐ Support

If you like this project:

* Star ⭐ the repo
* Share with others
* Contribute 🚀

---

## 📜 License

MIT License
