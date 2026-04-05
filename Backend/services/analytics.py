from db import questions_collection
from collections import Counter


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
