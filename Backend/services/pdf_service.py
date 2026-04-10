import re
import json
from io import BytesIO

import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize LLM
llm_model = ChatGroq(model="qwen/qwen3-32b")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF using pdfplumber, fallback to OCR if needed
    """
    text = ""

    # Try pdfplumber first
    try:
        pdf_file = BytesIO(file_bytes)
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"pdfplumber error: {e}")

    # OCR fallback
    if not text.strip():
        try:
            images = convert_from_bytes(file_bytes)
            for img in images:
                text += pytesseract.image_to_string(img)
        except Exception as e:
            print(f"OCR error: {e}")

    return text


def clean_text(text: str) -> str:
    """
    Pre-process text to remove OCR artifacts
    """
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove weird OCR characters (keep only alphanumeric, ?, ., and spaces)
    text = re.sub(r'[^a-zA-Z0-9?. ]', '', text)
    
    # Remove long number sequences (page numbers, artifacts)
    text = re.sub(r'\d{4,}', '', text)
    
    return text.strip()


def clean_and_extract_questions_with_llm(text: str) -> list[str]:
    """
    Use LLM to intelligently clean OCR noise and extract questions
    """
    # Pre-clean the text first
    cleaned_text = clean_text(text)
    
    prompt = f"""
You are an expert at extracting ALL questions from exam papers.

Your task:
1. Extract EVERY question and sub-question (including a, b, c parts)
2. Treat each sub-part as a separate question
3. Fix OCR errors and clean up text
4. Remove noise and incomplete fragments

Raw text from exam paper:
---
{cleaned_text[:8000]}
---

CRITICAL RULES:
- Extract Q.1(a), Q.1(b), Q.2(a), Q.2(b), etc. as SEPARATE questions
- If a question has parts (a), (b), (c), extract each part individually
- Include the question number in the extracted question
- Remove standalone numbers, abbreviations, incomplete words
- Each extracted question must be 8+ words
- Return ALL questions found, not just first few

Example from paper with 3 questions, 2 parts each:
["Q1(a) What are the properties of linear block codes?", "Q1(b) How would you generate a linear code?", "Q2(a) What is Entropy?", "Q2(b) Show that entropy is maximum when all messages are equiprobable"]

Return ONLY a JSON array of strings - no other text.
"""

    try:
        response = llm_model.invoke(prompt)
        response_text = response.content.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            # Filter empty/short strings
            questions = [q.strip() for q in questions if q.strip() and len(q) > 8]
            return questions
    except Exception as e:
        print(f"LLM extraction error: {e}")
    
    # Fallback to basic extraction if LLM fails
    return extract_questions_fallback(cleaned_text)


def extract_questions_fallback(text: str) -> list[str]:
    """
    Fallback regex-based extraction
    """
    questions = []
    lines = re.split(r'\.\s+|\n', text)
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        if '?' in line or re.match(r'^[a-z0-9]+\s*\(', line, re.IGNORECASE):
            questions.append(line)
    
    return list(set(questions))



