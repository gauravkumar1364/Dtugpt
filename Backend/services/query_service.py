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
    
    prompt = f"""You are DTUGPT.

Answer: {query}

{f'Subject: {context_questions[0]["subject"]}' if context_questions and "subject" in context_questions[0] else ''}
{context if context else ''}

Format Output:

## Concept
- Main definition or idea (2-3 lines only)

## Key Points
- Essential point 1
- Essential point 2
- Essential point 3
(Only crucial concepts, no repetition)

## Exam Focus
- Important for exam
- Common question format
- Key formula or formula (if needed)

Rules:
- Direct and concise
- No verbose explanations
- Bullet points only
- Match exam scope
- Under 150 words total"""  
    
    response = llm_model.invoke(prompt)
    raw_answer = response.content
    
    # Structure the response
    structured_answer = structure_llm_output(raw_answer, return_format="json")
    
    return {
        "answer": structured_answer,
        "matched_questions": context_questions
    }
