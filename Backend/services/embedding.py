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
    Encode questions and store in FAISS + MongoDB (with duplicate check)
    """
    global questions_db, index
    
    if not questions:
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
    Critical for data persistence across restarts
    """
    global questions_db, index
    
    questions_db.clear()
    index = faiss.IndexFlatL2(dimension)
    
    all_questions = list(questions_collection.find({}, {"_id": 0}))
    
    if not all_questions:
        print("ℹ️  No questions in MongoDB yet")
        return
    
    # Extract questions that need embeddings
    questions_to_embed = []
    for doc in all_questions:
        if "embedding" not in doc or not doc["embedding"]:
            questions_to_embed.append(doc["question"])
    
    # Generate embeddings for missing ones
    if questions_to_embed:
        print(f"🔄 Generating embeddings for {len(questions_to_embed)} questions...")
        new_embeddings = embed_model.encode(questions_to_embed)
        
        for question, embedding in zip(questions_to_embed, new_embeddings):
            questions_collection.update_one(
                {"question": question},
                {"$set": {"embedding": embedding.tolist()}}
            )
    
    # Reload all questions with complete embeddings
    all_questions = list(questions_collection.find({}, {"_id": 0}))
    
    # Build FAISS index
    embeddings = []
    for doc in all_questions:
        questions_db.append(doc)
        embeddings.append(doc["embedding"])
    
    if embeddings:
        index.add(np.array(embeddings, dtype=np.float32))
        print(f"✅ Loaded {len(embeddings)} questions into FAISS from MongoDB")
