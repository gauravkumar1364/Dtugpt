from db import questions_collection
from collections import Counter
import numpy as np
from numpy import dot
from numpy.linalg import norm


def cosine_similarity(a, b):
    """
    Calculate cosine similarity between two embedding vectors
    Returns value between 0 and 1 (higher = more similar)
    """
    try:
        # Convert to numpy arrays if needed
        a = np.array(a)
        b = np.array(b)
        return dot(a, b) / (norm(a) * norm(b))
    except Exception as e:
        print(f"Similarity calculation error: {e}")
        return 0.0


def cluster_questions(questions: list[dict], similarity_threshold: float = 0.75) -> list[list[dict]]:
    """
    Cluster similar questions together using cosine similarity
    Questions with embedding similarity > threshold are grouped
    
    Args:
        questions: List of question dicts with 'embedding' field
        similarity_threshold: Minimum similarity to group questions (0-1)
    
    Returns:
        List of clusters, each cluster is a list of similar questions
    """
    if not questions:
        return []
    
    clusters = []
    
    for q in questions:
        placed = False
        
        # Try to place in existing cluster
        for cluster in clusters:
            # Compare with first question in cluster
            sim = cosine_similarity(q["embedding"], cluster[0]["embedding"])
            
            if sim > similarity_threshold:
                cluster.append(q)
                placed = True
                break
        
        # Create new cluster if not similar to any existing
        if not placed:
            clusters.append([q])
    
    return clusters


def get_most_asked_topics(subject: str = None, limit: int = 10) -> list[dict]:
    """
    Get most repeated topics by clustering similar questions
    Groups semantically similar questions together
    """
    # Get questions from DB
    query = {}
    if subject:
        query = {"subject": subject}
    
    all_questions = list(questions_collection.find(query, {"_id": 0}))
    
    if not all_questions:
        return []
    
    # Filter questions with embeddings
    questions_with_embeddings = [
        q for q in all_questions if "embedding" in q and q["embedding"]
    ]
    
    if not questions_with_embeddings:
        return []
    
    # Cluster similar questions
    clusters = cluster_questions(questions_with_embeddings, similarity_threshold=0.75)
    
    # Sort by cluster size (most asked first)
    clusters.sort(key=lambda x: len(x), reverse=True)
    
    # Format results
    results = []
    for cluster in clusters[:limit]:
        results.append({
            "topic": cluster[0]["question"],  # Representative question
            "frequency": len(cluster),  # How many similar questions
            "subject": cluster[0].get("subject", "Unknown"),
            "related_questions": [q["question"] for q in cluster[:3]]  # Show up to 3 related
        })
    
    return results


def get_most_asked_questions(subject: str = None, limit: int = 10) -> list[dict]:
    """
    Get most frequently asked questions, optionally filtered by subject
    """
    query = {}
    if subject:
        query = {"subject": subject}
    
    # Count questions by content
    all_questions = list(questions_collection.find(query, {"question": 1, "subject": 1}))
    
    if not all_questions:
        return []
    
    # Group by subject and question
    question_counts = Counter()
    for doc in all_questions:
        key = (doc.get("subject", "Unknown"), doc["question"])
        question_counts[key] += 1
    
    # Sort by frequency
    sorted_questions = sorted(question_counts.items(), key=lambda x: x[1], reverse=True)
    
    results = []
    for (subj, question), count in sorted_questions[:limit]:
        results.append({
            "subject": subj,
            "question": question,
            "frequency": count
        })
    
    return results


def get_subjects_stats() -> list[dict]:
    """
    Get statistics per subject
    """
    # Aggregate by subject
    pipeline = [
        {"$group": {"_id": "$subject", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    stats = list(questions_collection.aggregate(pipeline))
    
    result = []
    for stat in stats:
        result.append({
            "subject": stat["_id"],
            "question_count": stat["count"]
        })
    
    return result


def get_question_count() -> int:
    """
    Get total question count
    """
    return questions_collection.count_documents({})
