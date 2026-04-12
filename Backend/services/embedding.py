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

# FAISS index - lazy-built on first search
dimension = 384
index = None  # Will be built only once
index_built = False  # Track if index has been built

# In-memory DB (will be replaced with MongoDB)
questions_db = []


def store_questions(subject: str, questions: list[str]) -> None:
    """
    Encode questions and store in FAISS + MongoDB (with duplicate check)
    """
    global questions_db, index, index_built
    
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
        
        # Add to FAISS index if it exists
        if index is not None:
            index.add(np.array([embeddings[i]], dtype=np.float32))
        else:
            # Reset index flag so it rebuilds next search
            index_built = False


def search_similar(query: str, top_k: int = 5, subject: str = None) -> list[dict]:
    """
    Search for similar questions using FAISS
    Build index only once on first search
    """
    global index, index_built, questions_db
    
    if len(questions_db) == 0:
        return []
    
    # Build FAISS index only once on first search
    if not index_built:
        print("⏳ Building FAISS index on first search...")
        try:
            index = faiss.IndexFlatL2(dimension)
            
            # Extract embeddings from questions_db
            embeddings_to_add = []
            for q in questions_db:
                if "embedding" in q:
                    embeddings_to_add.append(q["embedding"])
            
            if embeddings_to_add:
                embeddings_array = np.array(embeddings_to_add, dtype=np.float32)
                index.add(embeddings_array)
                print(f"✅ FAISS index built with {len(embeddings_to_add)} embeddings")
            else:
                print("⚠️  No embeddings found in questions_db")
                return []
                
        except Exception as e:
            print(f"❌ Failed to build FAISS index: {e}")
            return []
        finally:
            index_built = True
    
    # Get embedding model
    embed_model = get_embed_model()
    if not embed_model:
        print("⚠️  Embedding model unavailable - search disabled")
        return []
    
    # Encode query
    query_embedding = embed_model.encode([query])
    
    # Search in FAISS (get more results to account for filtering)
    search_k = min(top_k * 3 if subject else top_k, len(questions_db))
    
    try:
        distances, indices = index.search(np.array(query_embedding, dtype=np.float32), search_k)
    except Exception as e:
        print(f"❌ FAISS search failed: {e}")
        return []
    
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
    FAISS index will be built on first search request
    """
    global questions_db, index_built
    
    try:
        print("⏳ Loading questions from MongoDB...")
        questions_db.clear()
        index_built = False  # Reset index flag so it rebuilds on first search
        
        all_questions = list(questions_collection.find({}, {"_id": 0}))
        
        if not all_questions:
            print("ℹ️  No questions in MongoDB yet")
            return
        
        # Load into memory - FAISS index will build on first search
        questions_db = all_questions
        print(f"✅ Loaded {len(all_questions)} questions into memory (FAISS will build on first search)")
        
    except Exception as e:
        print(f"⚠️  Error loading questions on startup: {e}")
        print("💡 Questions will load from MongoDB on-demand")
