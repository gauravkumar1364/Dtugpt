from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from .response_formatter import structure_llm_output

load_dotenv()

# Initialize LLM with token limits
llm_model = ChatGroq(
    model="qwen/qwen3-32b",
    max_tokens=1024,  # Limit output to prevent truncation
    temperature=0.7
)


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

Your task: Answer the student's question clearly and concisely.

{f'Subject: {context_questions[0]["subject"]}' if context_questions and "subject" in context_questions[0] else ''}

{context}

Student's Question:
{query}

Instructions:
1. Keep answer SHORT (5-7 bullet points max)
2. Structure as:
   - Definition/Concept (1-2 lines)
   - Key Points (3-4 bullets)
   - Exam Tip (1 key takeaway)
3. Use bullet format, not paragraphs
4. Include formulas only if essential
5. Match scope of previous year questions

Answer (SHORT and FORMATTED):"""  
    
    response = llm_model.invoke(prompt)
    raw_answer = response.content
    
    # Structure the response
    structured_answer = structure_llm_output(raw_answer, return_format="json")
    
    return {
        "answer": structured_answer,
        "matched_questions": context_questions
    }
