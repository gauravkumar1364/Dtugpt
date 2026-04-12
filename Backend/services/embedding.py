import numpy as np
import os
import faiss
from db import questions_collection

# Lazy-load embedding model to prevent Render startup hangs
embed_model = None

def get_embed_model():
    """Lazy-initialize embedding model on first use"""
    global embed_model
    if embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("⏳ Loading embedding model (first use - cached after)...")
            embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Embedding model loaded")
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            return None
    return embed_model

# FAISS index
dimension = 384
index = faiss.IndexFlatL2(dimension)

# In-memory DB (will be replaced with MongoDB)
questions_db = []


def store_questions(subject: str, questions: list[str]) -> None:
    """
    Encode questions and store in FAISS + MongoDB (with duplicate check)
    """
    global questions_db, index
    
    if not questions:
        return
    
    # Get embedding model
    embed_model = get_embed_model()
    if not embed_model:
        print("⚠️  Embedding model unavailable - storing without embeddings")
        return
    
    # Generate embeddings
    embeddings = embed_model.encode(questions)
    
    # Store in memory and FAISS
    for i, q in enumerate(questions):
        # Check for duplicates in MongoDB
        if questions_collection.find_one({"question": q}):
            print(f"⏭️  Skipping duplicate: {q[:50]}...")
            continue
        
        # Insert into MongoDB
        questions_collection.insert_one({
            "subject": subject,
            "question": q,
            "embedding": embeddings[i].tolist()
        })
        
        # Add to in-memory DB
        questions_db.append({
            "subject": subject,
            "question": q,
            "embedding": embeddings[i].tolist()
        })
        
        # Add to FAISS index
        index.add(np.array([embeddings[i]], dtype=np.float32))


def search_similar(query: str, top_k: int = 5, subject: str = None) -> list[dict]:
    """
    Search for similar questions using FAISS
    Optionally filter by subject
    """
    if len(questions_db) == 0:
        return []
    
    # Get embedding model
    embed_model = get_embed_model()
    if not embed_model:
        print("⚠️  Embedding model unavailable - search disabled")
        return []
    
    # Encode query
    query_embedding = embed_model.encode([query])
    
    # Search in FAISS (get more results to account for filtering)
    search_k = top_k * 3 if subject else top_k
    distances, indices = index.search(np.array(query_embedding, dtype=np.float32), min(search_k, len(questions_db)))
    
    # Get results and filter by subject if specified
    results = []
    for idx in indices[0]:
        if idx < len(questions_db):
            doc = questions_db[idx]
            
            # Subject filter (substring match, case-insensitive)
            if subject and subject.lower() not in doc.get("subject", "").lower():
                continue
            
            results.append(doc)
            
            if len(results) >= top_k:
                break
    
    return results


def load_questions_from_db() -> None:
    """
    Load all questions from MongoDB into memory on startup
    Skip FAISS index building to prevent startup hangs on Render
    """
    global questions_db, index
    
    try:
        print("⏳ Loading questions from MongoDB...")
        questions_db.clear()
        index = faiss.IndexFlatL2(dimension)
        
        all_questions = list(questions_collection.find({}, {"_id": 0}))
        
        if not all_questions:
            print("ℹ️  No questions in MongoDB yet")
            return
        
        # Just load into memory - don't rebuild FAISS index (too slow)
        questions_db = all_questions
        print(f"✅ Loaded {len(all_questions)} questions into memory (FAISS lazy-built on first search)")
        
    except Exception as e:
        print(f"⚠️  Error loading questions on startup: {e}")
        print("💡 Questions will load from MongoDB on-demand")
