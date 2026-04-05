# 🚀 DTU PYQ Assistant - Operations Guide

## ⚙️ Setup & Configuration

### 1. Environment Variables (.env)
```
GROQ_API_KEY=your_groq_api_key
MONGODB_URL=your_mongodb_atlas_connection_string
```

### 2. Start Server
```bash
cd Backend
uvicorn main:app --reload
```

Server starts at: `http://localhost:8000`

---

## 📱 API Endpoints

### 1. Upload PDF & Extract Questions
```http
POST /uploadfile
Content-Type: multipart/form-data

file: <your_pdf_file>
```

**Response:**
```json
{
  "message": "PDF processed successfully",
  "subject": "CO305_ITC_2018_Nov",
  "questions_extracted": 14,
  "sample_questions": [
    "What are the properties of linear block codes?",
    "Explain how to generate a linear code",
    ...
  ]
}
```

---

### 2. Ask a Question
```http
POST /ask
Content-Type: application/json

{
  "query": "What is entropy in information theory?"
}
```

**Response:**
```json
{
  "answer": "Entropy is a measure of uncertainty... [detailed answer]",
  "matched_questions": [
    {
      "subject": "CO305_ITC_2018",
      "question": "What is Entropy? Show that entropy is maximum...",
      "embedding": [0.12, 0.45, ...]
    },
    ...
  ]
}
```

---

### 3. Get Most Asked Questions
```http
GET /important-questions?subject=CO305&limit=10
```

**Response:**
```json
{
  "status": "success",
  "questions": [
    {
      "subject": "CO305",
      "question": "What is Hamming code?",
      "frequency": 5
    },
    ...
  ]
}
```

---

### 4. Get Statistics
```http
GET /stats
```

**Response:**
```json
{
  "total_questions": 142,
  "subjects": [
    {
      "subject": "CO305_ITC_2018",
      "question_count": 45
    },
    {
      "subject": "CO302_DSA_2017",
      "question_count": 28
    },
    ...
  ]
}
```

---

### 5. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "total_questions": 142
}
```

---

### 6. General Chat
```http
POST /chat
Content-Type: application/json

{
  "message": "Explain what is Data Structure"
}
```

**Response:**
```json
{
  "reply": "A data structure is...",
  "thinking": "[Optional reasoning if model returns thinking tags]"
}
```

---

## 🔄 Typical Usage Flow

### First Time Setup
```
1. Start Server
   └─ Server loads all questions from MongoDB
   └─ Builds FAISS index
   └─ Ready to serve

2. Upload PDFs
   POST /uploadfile → Extract questions → Store in DB → Add to FAISS

3. Check Stats
   GET /stats → See how many questions loaded

4. Ask Questions
   POST /ask → Get answers from PYQs
```

### After Server Restart
```
1. All questions automatically reloaded from MongoDB
2. FAISS index rebuilt
3. No need to re-upload PDFs
4. Ready to answer queries immediately
```

---

## 🐛 Debugging & Monitoring

### Server Logs
```bash
# Watch real-time logs
tail -f backend.log

# Look for:
✅ "Loaded X questions into FAISS from MongoDB"
⚠️  "Skipping duplicate: ..."
ℹ️  "No questions in MongoDB yet"
🔄 "Generating embeddings for X questions..."
```

### Check MongoDB
```javascript
// MongoDB CLI
db.questions.find({}).count()  // Total questions
db.questions.findOne()  // Sample question
db.questions.find({"subject": "CO305"}).count()  // By subject
```

### Test FAISS
```python
# Python script
from services.embedding import search_similar
results = search_similar("What is entropy?", top_k=5)
for r in results:
    print(r["question"])
```

---

## 📊 Data Flow Examples

### Example 1: Upload & Search
```
1. Upload: CO305_ITC_2018_Nov.pdf
   → 14 questions extracted
   → Stored in MongoDB
   → Embeddings added to FAISS

2. Query: "block codes"
   → Search FAISS
   → Return top 5 similar questions
   → Generate answer with LLM

3. User gets answer + relevant PYQs
```

### Example 2: Multi-subject Queries
```
1. Upload: CO305_ITC_2018_Nov.pdf (14 Qs)
2. Upload: CO302_DSA_2017_Dec.pdf (12 Qs)
3. Upload: CO304_Algorithms_2019.pdf (18 Qs)

Total: 44 questions in system

Query: "complexity analysis"
→ FAISS searches all 44 questions
→ Returns relevant ones from any subject
→ LLM answers using all context
```

---

## ⚠️ Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **MongoDB not connected** | Error on startup | Check MONGODB_URL in .env |
| **No questions found** | "No data in DB" message | Upload a PDF first |
| **Slow search** | Takes >1s per query | FAISS index building, restart if stuck |
| **Same question twice** | Duplicates in results | Auto-removed on next upload |
| **Embedding mismatch** | Old questions have errors | Restart server to regenerate |
| **GROQ API fails** | LLM answer is empty | Check GROQ_API_KEY, rate limits |

---

## 🎯 Performance Benchmarks

Expected performance:

| Operation | Time | Notes |
|-----------|------|-------|
| PDF upload (5 pages) | 2-5s | Includes OCR if needed |
| Question extraction | 1-2s | LLM processing |
| FAISS search (10k Qs) | <10ms | Very fast |
| LLM answer generation | 1-3s | Depends on query complexity |
| Total query time | 2-5s | End-to-end |

---

## 📈 Scaling Tips

### For 1,000+ questions:
- Use MongoDB Atlas (built-in scalability)
- Consider FAISS GPU acceleration (if using GPU)
- Add Redis caching for frequent queries
- Implement rate limiting

### For 10,000+ questions:
- Use HNSW index instead of flat (faster search)
- Consider sampling for initial search
- Add approximate nearest neighbor search
- Implement pagination for results

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Server starts without errors
- [ ] MongoDB shows connected
- [ ] Upload a test PDF successfully
- [ ] See questions extracted in response
- [ ] Ask a test question and get answer
- [ ] Check `/stats` endpoint
- [ ] Check `/health` endpoint
- [ ] Restart server and ask question again (data persists)

---

## 🔗 Quick Links

- **FastAPI Docs**: http://localhost:8000/docs
- **MongoDB Atlas**: https://cloud.mongodb.com
- **Groq Console**: https://console.groq.com
- **GitHub Repo**: https://github.com/gauravkumar1364/Dtugpt

