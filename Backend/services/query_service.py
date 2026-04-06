from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from .response_formatter import structure_llm_output

load_dotenv()

# Initialize LLM
llm_model = ChatGroq(model="qwen/qwen3-32b")


async def answer_query(query: str, context_questions: list[dict]) -> dict:
    """
    Generate answer based on similar questions and user query
    Uses subject context if available
    Returns structured and readable response
    """
    # Build context from matched questions
    context = "\n".join([f"- Q: {q['question']}" for q in context_questions])
    
    # Extract subject from first question if available
    subject_context = ""
    if context_questions and "subject" in context_questions[0]:
        subject_context = f"\nSubject: {context_questions[0]['subject']}"
    
    prompt = f"""
You are a DTU exam assistant that helps students with exam preparation.

Based on previous year questions from this subject:{subject_context}

{context}

Answer the student's query:
{query}

Provide a concise, exam-oriented answer with clear explanations using clear sections and bullet points.
"""
    
    response = llm_model.invoke(prompt)
    raw_answer = response.content
    
    # Structure the response
    structured_answer = structure_llm_output(raw_answer, return_format="json")
    
    return {
        "answer": structured_answer,
        "matched_questions": context_questions
    }
