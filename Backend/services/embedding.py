import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from db import questions_collection

# Initialize embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# FAISS index
dimension = 384
index = faiss.IndexFlatL2(dimension)

# In-memory DB (will be replaced with MongoDB)
questions_db = []


def store_questions(subject: str, questions: list[str]) -> None:
    """
    Encode questions and store in FAISS + in-memory DB
    """
    global questions_db, index
    
    if not questions:
        return
    
    # Generate embeddings
    embeddings = embed_model.encode(questions)
    
    # Store in memory and FAISS
    for i, q in enumerate(questions):
        questions_db.append({
            "subject": subject,
            "question": q,
            "embedding": embeddings[i].tolist()
        })
        
        # Also store in MongoDB
        questions_collection.insert_one({
            "subject": subject,
            "question": q,
            "embedding": embeddings[i].tolist()
        })
    
    # Add to FAISS index
    index.add(np.array(embeddings, dtype=np.float32))


def search_similar(query: str, top_k: int = 5) -> list[dict]:
    """
    Search for similar questions using FAISS
    """
    if len(questions_db) == 0:
        return []
    
    # Encode query
    query_embedding = embed_model.encode([query])
    
    # Search in FAISS
    distances, indices = index.search(np.array(query_embedding, dtype=np.float32), top_k)
    
    # Get results
    results = []
    for idx in indices[0]:
        if idx < len(questions_db):
            results.append(questions_db[idx])
    
    return results


def load_questions_from_db() -> None:
    """
    Load all questions from MongoDB into memory/FAISS on startup
    """
    global questions_db, index
    
    all_questions = list(questions_collection.find({}, {"_id": 0}))
    
    if not all_questions:
        return
    
    # Rebuild FAISS index
    embeddings = []
    for doc in all_questions:
        questions_db.append(doc)
        embeddings.append(doc["embedding"])
    
    if embeddings:
        index.add(np.array(embeddings, dtype=np.float32))
        print(f"Loaded {len(embeddings)} questions from MongoDB")
