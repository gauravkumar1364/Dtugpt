import os
import re
from contextlib import asynccontextmanager
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
from services.analytics import get_most_asked_questions, get_subjects_stats, get_question_count, get_most_asked_topics
from services.response_formatter import structure_llm_output

# Load environment variables
load_dotenv()

# Initialize LLM
llm_model = ChatGroq(model="qwen/qwen3-32b")


# ==================== LIFESPAN EVENTS ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events using lifespan context manager"""
    # Startup
    load_questions_from_db()
    print("✅ DTU PYQ Assistant started")
    
    yield
    
    # Shutdown (if needed)
    print("🛑 DTU PYQ Assistant shutting down")


# Initialize FastAPI with lifespan
app = FastAPI(title="DTU PYQ Assistant", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== ROUTES ====================

@app.post("/chat")
async def chat(req: ChatRequest):
    """Chat endpoint - general conversation with structured output"""
    response = llm_model.invoke(req.message)
    raw_text = response.content

    # Extract thinking if present
    thinking = re.search(r"<think>([\s\S]*?)</think>", raw_text)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()
    thinking_text = thinking.group(1).strip() if thinking else None

    # Structure the response
    structured = structure_llm_output(cleaned, return_format="json")

    return {
        "reply": structured,
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

        # Extract subject from filename (handle multiple formats)
        # Formats: "CO305_ITC_2018.pdf", "dbms-normalization.pdf", "signals.pdf"
        filename = file.filename.lower()
        
        # Remove extension
        filename_clean = filename.split('.')[0]
        
        # Try to extract meaningful subject
        # Priority: First word or pattern before underscore/hyphen
        if '_' in filename_clean:
            subject = filename_clean.split('_')[0]  # e.g., "CO305" from "CO305_ITC_2018"
        elif '-' in filename_clean:
            subject = filename_clean.split('-')[0]  # e.g., "dbms" from "dbms-normalization"
        else:
            subject = filename_clean  # Use entire filename if no pattern

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
    """Ask question - searches PYQs and generates answer (with optional subject filter)"""
    try:
        # Search similar questions (optionally filtered by subject)
        results = search_similar(req.query, top_k=5, subject=req.subject)

        if not results:
            return {
                "answer": "No matching questions found",
                "matched_questions": []
            }

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


@app.get("/trending-topics")
async def get_trending_topics(subject: str = None, limit: int = 10):
    """
    Get most repeated topics using clustering
    Groups similar questions together to find trending topics
    """
    try:
        topics = get_most_asked_topics(subject=subject, limit=limit)
        return {
            "status": "success",
            "trending_topics": topics,
            "description": "Topics grouped by similarity (threshold: 0.75)"
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