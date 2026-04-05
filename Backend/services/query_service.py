from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize LLM
llm_model = ChatGroq(model="qwen/qwen3-32b")


async def answer_query(query: str, context_questions: list[dict]) -> dict:
    """
    Generate answer based on similar questions and user query
    """
    # Build context from matched questions
    context = "\n".join([f"- {q['question']}" for q in context_questions])
    
    prompt = f"""
You are a DTU exam assistant that helps students with exam preparation.

Based on previous year questions:
{context}

Answer the student's query:
{query}

Provide a concise, exam-oriented answer with clear explanations.
"""
    
    response = llm_model.invoke(prompt)
    
    return {
        "answer": response.content,
        "matched_questions": context_questions
    }
