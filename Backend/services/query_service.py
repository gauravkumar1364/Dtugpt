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
    # Build context from matched questions with better formatting
    if context_questions:
        questions_list = "\n".join([f"- {q['question']}" for q in context_questions])
        context = f"""
Previous Year Questions on Similar Topics:
{questions_list}

These questions help establish the topic coverage and expected answer depth."""
    else:
        context = ""
    
    # Extract subject from first question if available
    subject_context = ""
    if context_questions and "subject" in context_questions[0]:
        subject_context = f" ({context_questions[0]['subject']})"
    
    prompt = f"""You are a DTU exam assistant helping students prepare for exams.

Your task: Answer the student's question comprehensively and clearly.

{f'Subject: {context_questions[0]["subject"]}' if context_questions and "subject" in context_questions[0] else ''}

{context}

Student's Question:
{query}

Instructions:
1. Answer based on the question topic and similar previous year questions
2. Use the previous questions as reference for scope and depth
3. Structure your answer with clear sections and bullet points
4. Include relevant facts, concepts, and explanations
5. Keep it exam-oriented and concise
6. Match the technical depth shown in previous questions

Answer:"""
    
    response = llm_model.invoke(prompt)
    raw_answer = response.content
    
    # Structure the response
    structured_answer = structure_llm_output(raw_answer, return_format="json")
    
    return {
        "answer": structured_answer,
        "matched_questions": context_questions
    }
