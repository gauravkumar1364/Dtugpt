# DTU PYQ Assistant - Architecture & Workflow

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DTU PYQ ASSISTANT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FRONTEND                 BACKEND                   DATABASE    │
│  ┌────────┐              ┌──────────────┐          ┌────────┐  │
│  │ React  │              │ FastAPI      │          │MongoDB │  │
│  │ App    │◄────────────►│ Server       │◄────────►│ Atlas  │  │
│  └────────┘              │              │          └────────┘  │
│                          │ Services:    │             ▲        │
│                          │ • pdf_       │             │        │
│                          │   service.py │          Embeddings  │
│                          │ • embedding  │          & Questions  │
│                          │   .py        │                      │
│                          │ • query_     │          ┌────────┐  │
│                          │   service.py │          │ FAISS  │  │
│                          │ • analytics  │          │ Index  │  │
│                          │   .py        │          └────────┘  │
│                          └──────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Workflow Diagrams

### 1️⃣ UPLOAD (One-time Process)

```
User uploads PDF
       ↓
📄 Extract text with pdfplumber / OCR
       ↓
🧹 Clean OCR noise (regex + LLM)
       ↓
❓ Extract questions with LLM
       ↓
🔍 Check for duplicates in MongoDB
       ↓
💾 Store in MongoDB (new questions only)
       ↓
🔢 Generate embeddings (SentenceTransformer)
       ↓
📦 Build FAISS index
       ↓
✅ Response: "14 questions extracted"
```

**Code Flow:**
```
POST /uploadfile
  ├─ extract_text_from_pdf() [pdf_service.py]
  ├─ clean_and_extract_questions_with_llm() [pdf_service.py]
  ├─ store_questions() [embedding.py]
  │   ├─ Check duplicates (MongoDB)
  │   ├─ Insert new questions
  │   ├─ Generate embeddings
  │   └─ Add to FAISS index
  └─ Return response
```

---

### 2️⃣ SERVER START (Initialization)

```
Server starts (uvicorn main:app)
       ↓
🔄 Lifespan startup event triggered
       ↓
📥 load_questions_from_db() [embedding.py]
       ↓
🔌 Connect to MongoDB Atlas
       ↓
📊 Fetch ALL questions from DB
       ↓
🔢 Generate embeddings for missing ones
       ↓
🏗️ Build/reset FAISS index
       ↓
✅ Ready to serve requests
```

**Code Flow:**
```
@asynccontextmanager
async def lifespan(app: FastAPI)
  ├─ startup:
  │   └─ load_questions_from_db() [embedding.py]
  │       ├─ Clear in-memory DB
  │       ├─ Reset FAISS index
  │       ├─ Load all from MongoDB
  │       ├─ Generate missing embeddings
  │       └─ Rebuild FAISS index
  ├─ yield (server running)
  └─ shutdown: cleanup
```

---

### 3️⃣ QUERY (Runtime - Answer Generation)

```
User asks: "What is entropy?"
       ↓
🔗 Convert query to embedding
       ↓
🔍 FAISS similarity search (top 5)
       ↓
📚 Get matched PYQ questions
       ↓
🤖 LLM generates answer using context
       ↓
📤 Send back: answer + matched_questions
       ↓
✅ Frontend displays answer
```

**Code Flow:**
```
POST /ask
  ├─ search_similar() [embedding.py]
  │   ├─ Encode query (SentenceTransformer)
  │   ├─ FAISS similarity search
  │   └─ Return top-k questions
  ├─ answer_query() [query_service.py]
  │   ├─ Build LLM prompt with context
  │   ├─ Call ChatGroq LLM
  │   └─ Format response
  └─ Return: {answer, matched_questions}
```

---

## 🗂️ File Structure & Responsibilities

```
Backend/
├── main.py                     # Routes ONLY (clean entry point)
│   ├── POST /chat              # General chat
│   ├── POST /uploadfile        # Upload & process PDFs
│   ├── POST /ask               # Query & answer
│   ├── GET /important-questions # Most asked Qs
│   ├── GET /stats              # Analytics
│   └── GET /health             # Health check
│
├── models.py                   # Request/Response schemas
│   ├── ChatRequest
│   ├── AskRequest
│   └── QuestionDocument
│
├── db.py                       # MongoDB connection
│   └── questions_collection    # Main data store
│
└── services/
    ├── pdf_service.py          # PDF → Questions
    │   ├── extract_text_from_pdf()
    │   ├── clean_text()
    │   ├── clean_and_extract_questions_with_llm()
    │   └── extract_questions_fallback()
    │
    ├── embedding.py            # Embeddings & Search
    │   ├── store_questions()           # Save to MongoDB + FAISS
    │   ├── search_similar()            # FAISS search
    │   └── load_questions_from_db()    # Startup reload
    │
    ├── query_service.py        # Answer Generation
    │   └── answer_query()      # LLM-based answer
    │
    └── analytics.py            # Statistics
        ├── get_most_asked_questions()
        ├── get_subjects_stats()
        └── get_question_count()
```

---

## 🔄 Data Flow Sequence

```
Timeline: Upload → Start → Query

[1] UPLOAD TIME
    PDF ──► pdf_service ──► MongoDB ──► FAISS Index
                                           │
                                           ▼
                                     (questions_db)

[2] SERVER START
    MongoDB ──► load_questions_from_db() ──► FAISS Index
                                               │
                                               ▼
                                         (questions_db)

[3] RUNTIME (QUERY)
    User Query ──► Embed ──► FAISS Search
                                │
                                ├── Get similar Qs
                                │
                                ├── Build prompt
                                │
                                ├── ChatGroq LLM
                                │
                                └── Return Answer
```

---

## 🛡️ Data Integrity Features

### 1. Duplicate Prevention
```python
# In store_questions() [embedding.py]
if questions_collection.find_one({"question": q}):
    print("⏭️  Skipping duplicate...")
    continue
```

### 2. Embedding Generation on Load
```python
# In load_questions_from_db() [embedding.py]
# Auto-generate embeddings for old questions
if "embedding" not in doc or not doc["embedding"]:
    # Generate new embedding
    new_embeddings = embed_model.encode(questions_to_embed)
    # Store back in MongoDB
```

### 3. FAISS Index Reconstruction
```python
# On every startup, FAISS is rebuilt fresh from MongoDB
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings, dtype=np.float32))
```

---

## 📊 Data Flow Example

### Upload Scenario
```
PDF: "CO305_ITC_2018_Nov.pdf"
│
├─ Page 1: "What are the properties of linear block codes?"
├─ Page 2: "a) Explain the entropy concept"
├─ Page 2: "b) Show that entropy is maximum when..."
├─ Page 3: "What is the Hamming code?"
└─ ...

After Processing:
MongoDB documents:
{
  "_id": ObjectId("..."),
  "subject": "CO305_ITC_2018_Nov",
  "question": "What are the properties of linear block codes?",
  "embedding": [0.12, 0.45, 0.67, ...]
}

FAISS Index:
[embedding1, embedding2, embedding3, ...]

questions_db (in-memory):
[
  {"subject": "...", "question": "...", "embedding": [...]},
  {"subject": "...", "question": "...", "embedding": [...]},
  ...
]
```

### Query Scenario
```
User Query: "What is block code?"
│
├─ Embedding: [0.13, 0.46, 0.68, ...]
│
├─ FAISS Search (top 5):
│  └─ Similar questions found:
│     1. "What are the properties of linear block codes?" (score: 0.92)
│     2. "Explain cyclic codes" (score: 0.87)
│     3. "What is Hamming code?" (score: 0.84)
│     4. "Generate a linear code" (score: 0.79)
│     5. "Properties of BCH codes" (score: 0.76)
│
├─ LLM Prompt:
│  "Based on these PYQs: [above questions]
│   Answer: What is block code?"
│
└─ Response:
   {
     "answer": "A block code is... [detailed answer]",
     "matched_questions": [...] 
   }
```

---

## 🚀 Performance Optimization

| Component | Optimization | Impact |
|-----------|--------------|--------|
| **PDF Extraction** | pdfplumber (fast) + OCR (fallback) | ⚡ <2s for typical PDF |
| **LLM Cleaning** | Pre-clean with regex before LLM | 💰 Reduce token usage |
| **Embeddings** | SentenceTransformer (384-dim) | ⚡ Sub-second queries |
| **FAISS Search** | L2 distance, flat index | ⚡ <10ms for 10k docs |
| **MongoDB** | Indexes on subject + question | 📊 Fast lookups |
| **Memory** | In-memory questions_db | 🚀 No DB lookup during runtime |

---

## ✅ Checklist: What's Working

- [x] PDF upload and text extraction
- [x] OCR noise cleaning with LLM
- [x] Question extraction (handles multi-part Qs)
- [x] Duplicate detection
- [x] MongoDB persistence
- [x] FAISS embedding + indexing
- [x] Similarity search
- [x] LLM-based answer generation
- [x] Analytics endpoints
- [x] Lifespan event handling (no deprecation)
- [x] Subject-aware storage

---

## 🔜 Next Steps (Optional Enhancements)

- [ ] Vector embeddings with Atlas Search ($vectorSearch)
- [ ] Question clustering for better analytics
- [ ] User feedback loop (question rating)
- [ ] Caching layer (Redis)
- [ ] API rate limiting
- [ ] Authentication & authorization
- [ ] Batch PDF upload
- [ ] Question categorization

---

## 📞 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "No questions found" | MongoDB empty on startup | Upload PDFs first |
| Slow search | FAISS index not built | Check startup logs |
| Duplicate questions | Skipped validation | Check MongoDB for duplicates |
| Embedding mismatch | Old data without embeddings | Restart server to regenerate |

