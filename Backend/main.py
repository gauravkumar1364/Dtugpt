import os
import re
import json
import numpy as np

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_groq import ChatGroq

import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from sentence_transformers import SentenceTransformer
import faiss

# ------------------ INIT ------------------

app = FastAPI()
load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = ChatGroq(model="qwen/qwen3-32b")

# Embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

dimension = 384
index = faiss.IndexFlatL2(dimension)

# Temporary DB (later MongoDB)
questions_db = []

# ------------------ MODELS ------------------

class chat_request(BaseModel):
    message: str

class ask_request(BaseModel):
    query: str

# ------------------ CHAT ------------------

@app.post("/chat")
async def chat(req: chat_request):
    response = model.invoke(req.message)

    raw_text = response.content

    thinking = re.search(r"<think>([\s\S]*?)</think>", raw_text)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()

    thinking_text = thinking.group(1).strip() if thinking else None

    return {
        "reply": cleaned,
        "thinking": thinking_text
    }

# ------------------ PDF EXTRACTION ------------------

def extract_text_from_pdf(file_bytes):
    text = ""

    # Try pdfplumber
    try:
        with pdfplumber.open(file_bytes) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except:
        pass

    # OCR fallback
    if not text.strip():
        images = convert_from_bytes(file_bytes)

        for img in images:
            text += pytesseract.image_to_string(img)

    return text

# ------------------ CLEAN TEXT ------------------

def clean_text(text):
    """Pre-process text to remove OCR artifacts before LLM processing"""
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove weird OCR characters (keep only alphanumeric, ?, ., and spaces)
    text = re.sub(r'[^a-zA-Z0-9?. ]', '', text)
    
    # Remove long number sequences (likely page numbers or artifacts)
    text = re.sub(r'\d{4,}', '', text)
    
    return text.strip()

# ------------------ LLM-BASED CLEANING & EXTRACTION ------------------

def clean_and_extract_questions_with_llm(text):
    """
    Use LLM to intelligently clean OCR noise and extract questions
    """
    import json
    
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
        response = model.invoke(prompt)
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

def extract_questions_fallback(text):
    """Fallback regex-based extraction"""
    questions = []
    lines = re.split(r'\.\s+|\n', text)
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        if '?' in line or re.match(r'^[a-z0-9]+\s*\(', line, re.IGNORECASE):
            questions.append(line)
    
    return list(set(questions))

# ------------------ STORE EMBEDDINGS ------------------

def store_questions(subject, questions):
    global questions_db, index

    embeddings = embed_model.encode(questions)

    for i, q in enumerate(questions):
        questions_db.append({
            "subject": subject,
            "question": q,
            "embedding": embeddings[i]
        })

    index.add(np.array(embeddings))

# ------------------ SEARCH ------------------

def search_similar(query, top_k=5):
    if len(questions_db) == 0:
        return []

    query_embedding = embed_model.encode([query])

    distances, indices = index.search(np.array(query_embedding), top_k)

    results = []
    for idx in indices[0]:
        if idx < len(questions_db):
            results.append(questions_db[idx])

    return results

# ------------------ UPLOAD ------------------

@app.post("/uploadfile")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()

        # STEP 1: Extract raw text from PDF
        text = extract_text_from_pdf(file_bytes)

        # STEP 2: Use LLM to clean & extract questions (IMPROVED)
        questions = clean_and_extract_questions_with_llm(text)

        # STEP 3: Subject from filename
        subject = file.filename.split('.')[0]

        # STEP 4: Store embeddings
        store_questions(subject, questions)

        return {
            "message": "PDF processed successfully",
            "subject": subject,
            "questions_extracted": len(questions),
            "sample_questions": questions[:5]
        }

    except Exception as e:
        return {"error": str(e)}

# ------------------ ASK (PYQ SEARCH) ------------------

@app.post("/ask")
async def ask(req: ask_request):
    results = search_similar(req.query)

    context = "\n".join([r["question"] for r in results])

    prompt = f"""
You are a DTU exam assistant.

Based on previous year questions:
{context}

Answer the query:
{req.query}

Give concise, exam-oriented answer.
"""

    response = model.invoke(prompt)

    return {
        "answer": response.content,
        "matched_questions": results
    }