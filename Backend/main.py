import os
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Import models
from models import ChatRequest, AskRequest

# Import services
from services.pdf_service import extract_text_from_pdf, clean_and_extract_questions_with_llm
from services.embedding import store_questions, search_similar, load_questions_from_db
from services.query_service import answer_query
from services.analytics import get_most_asked_questions, get_subjects_stats, get_question_count

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="DTU PYQ Assistant")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM
llm_model = ChatGroq(model="qwen/qwen3-32b")


# ==================== STARTUP ====================

@app.on_event("startup")
async def startup():
    """Load data on startup"""
    load_questions_from_db()
    print("✅ DTU PYQ Assistant started")


# ==================== ROUTES ====================

@app.post("/chat")
async def chat(req: ChatRequest):
    """Chat endpoint - general conversation"""
    response = llm_model.invoke(req.message)
    raw_text = response.content

    thinking = re.search(r"<think>([\s\S]*?)</think>", raw_text)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()
    thinking_text = thinking.group(1).strip() if thinking else None

    return {
        "reply": cleaned,
        "thinking": thinking_text
    }


@app.post("/uploadfile")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process PDF"""
    try:
        file_bytes = await file.read()

        # Extract text
        text = extract_text_from_pdf(file_bytes)

        # Extract questions using LLM
        questions = clean_and_extract_questions_with_llm(text)

        # Get subject from filename
        subject = file.filename.split('.')[0]

        # Store in DB and FAISS
        store_questions(subject, questions)

        return {
            "message": "PDF processed successfully",
            "subject": subject,
            "questions_extracted": len(questions),
            "sample_questions": questions[:5]
        }

    except Exception as e:
        return {"error": str(e)}


@app.post("/ask")
async def ask(req: AskRequest):
    """Ask question - searches PYQs and generates answer"""
    try:
        # Search similar questions
        results = search_similar(req.query, top_k=5)

        # Generate answer using LLM
        answer_response = await answer_query(req.query, results)

        return answer_response

    except Exception as e:
        return {"error": str(e)}


@app.get("/important-questions")
async def get_important_questions(subject: str = None, limit: int = 10):
    """Get most frequently asked questions"""
    try:
        questions = get_most_asked_questions(subject=subject, limit=limit)
        return {
            "status": "success",
            "questions": questions
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/stats")
async def get_stats():
    """Get analytics and statistics"""
    try:
        return {
            "total_questions": get_question_count(),
            "subjects": get_subjects_stats()
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "total_questions": get_question_count()
    }