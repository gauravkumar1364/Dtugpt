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
    Generate EXPECTED EXAM QUESTIONS based on patterns
    Exam prediction engine - generates questions, not explanations
    """
    subject = ""
    if context_questions and "subject" in context_questions[0]:
        subject = context_questions[0]["subject"]
    
    # Format ACTUAL questions - not summaries!
    questions_text = ""
    if context_questions:
        formatted_questions = []
        for i, q in enumerate(context_questions, 1):
            formatted_questions.append(f"{i}. {q['question']}")
        questions_text = "\n".join(formatted_questions)
    
    prompt = f"""You are an exam assistant.

Here are past year questions for {subject}:

{questions_text}

Task:
Generate expected exam questions.

Rules:
- Focus on most repeated patterns
- Do NOT explain concepts
- ONLY output questions
- Group into:
   1. Most Expected
   2. Moderate
   3. Concept-based

Output clean and concise.

Format:

## Most Expected Questions
- Question 1
- Question 2
- Question 3

## Moderate Questions
- Question 1
- Question 2

## Concept-based Questions
- Question 1
- Question 2

Rules:
- ONLY output questions from patterns in given questions
- NO explanations
- NO definitions
- Concise format
- Under 100 words total"""
    
    response = llm_model.invoke(prompt)
    raw_answer = response.content
    
    # Structure the response
    structured_answer = structure_llm_output(raw_answer, return_format="json")
    
    return {
        "answer": structured_answer,
        "matched_questions": context_questions
    }
