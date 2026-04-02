import os
import re
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
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9?. ]', '', text)
    return text

# ------------------ QUESTION EXTRACTION ------------------

def extract_questions(text):
    questions = []

    # Split by sentences
    lines = re.split(r'\.|\n', text)

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if '?' in line:
            questions.append(line)

        elif re.match(r'^\d+', line):
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

        # STEP 1: Extract text
        text = extract_text_from_pdf(file_bytes)

        # STEP 2: Clean
        cleaned_text = clean_text(text)

        # STEP 3: Extract questions
        questions = extract_questions(cleaned_text)

        # STEP 4: Subject (basic for now)
        subject = file.filename.split('.')[0]

        # STEP 5: Store embeddings
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