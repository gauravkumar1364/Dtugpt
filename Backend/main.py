import os
import re
from contextlib import asynccontextmanager
from typing import Optional
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
from services.analytics import get_most_asked_questions, get_subjects_stats, get_question_count, get_most_asked_topics, get_analyzed_questions
from services.response_formatter import structure_llm_output

# Load environment variables
load_dotenv()

# Initialize LLM with token limits to prevent truncation
llm_model = ChatGroq(
    model="qwen/qwen3-32b",
    max_tokens=1024,  # Limit output to 1024 tokens (~4000 chars)
    temperature=0.7
)


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


# ==================== MODE DETECTION ====================

def detect_query_mode(message: str) -> str:
    """
    Detect if query is analysis mode or detailed mode
    
    Analysis mode: "most asked", "important", "frequency", "topics"
    Detailed mode: everything else (specific questions, explanations)
    """
    msg_lower = message.lower()
    
    analysis_keywords = [
        "most asked", "important", "frequency", "topics", 
        "trending", "repeated", "common", "usually", "often",
        "statistics", "summary", "overview"
    ]
    
    for keyword in analysis_keywords:
        if keyword in msg_lower:
            return "analysis"
    
    return "detailed"


def get_context_for_detailed(query: str) -> str:
    """
    For detailed mode, search for similar questions to use as context
    """
    results = search_similar(query, top_k=5)
    
    if not results:
        return ""
    
    context = "Similar questions from PYQs:\n"
    for q in results:
        context += f"- {q['question']}\n"
    
    return context


# ==================== ROUTES ====================

# Query Interceptor - Route certain queries to MongoDB instead of LLM
def intercept_query(message: str) -> Optional[dict]:
    """
    Intercept queries asking for questions/topics and route to MongoDB
    Returns: dict with MongoDB results or None to pass to LLM
    """
    msg_lower = message.lower().strip()
    
    # More flexible regex patterns to catch various query formats
    patterns = [
        r"(?:questions|pyq|past year|previous|topic)s?\s+(?:for|on|in|about)?\s+([a-z0-9\s]+?)(?:\?|$)",
        r"(?:most asked|frequently asked|common|give me).*?(?:for|on|in)?\s+([a-z0-9\s]+?)(?:\?|$)",
        r"([a-z0-9\s]+?)\s+(?:questions|topics|pyq)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, msg_lower)
        if match:
            subject = match.group(1).strip()
            if not subject or len(subject) < 2:
                continue
            
            print(f"🔍 Interceptor: Testing subject='{subject}'")
            
            # Get ANALYZED questions with clustering and frequency
            analyzed_data = get_analyzed_questions(subject=subject, limit=10)
            questions = analyzed_data.get("topics", [])
            
            if questions:
                print(f"✅ INTERCEPTED: Query='{message}' -> Subject='{subject}' -> Found {len(questions)} topics")
                # Format for LLM analysis
                return {
                    "type": "analyzed_questions",
                    "subject": subject,
                    "data": analyzed_data
                }
            else:
                print(f"⚠️  Matched pattern but no questions: subject='{subject}'")
    
    print(f"ℹ️  No interception: '{message}'")
    return None


def format_mongodb_response(intercept_data: dict) -> dict:
    """
    Format analyzed data into clean structured response
    PYTHON does the analysis, LLM only formats output
    """
    subject = intercept_data.get("subject", "Unknown")
    analyzed = intercept_data.get("data", {})
    
    topics = analyzed.get("topics", [])
    total = analyzed.get("total_questions", 0)
    unique = analyzed.get("unique_topics", 0)
    
    if not topics:
        return {
            "title": "",
            "summary": f"No questions found for subject: {subject}",
            "sections": [],
            "key_points": [],
            "formatted_markdown": ""
        }
    
    # Build clean, grouped data - NO raw questions
    topics_list = []
    for topic in topics[:10]:  # Top 10 topics
        topics_list.append({
            "name": topic["topic"],
            "frequency": topic["frequency"]
        })
    
    # Build the prompt with CLEAN, GROUPED data only
    # NOT raw questions, just topic names and frequencies
    topic_summary = "\n".join([
        f"- {t['name']} (frequency: {t['frequency']})" 
        for t in topics_list
    ])
    
    prompt = f"""Format this exam analysis data for a student:

Subject: {subject}
Total Questions: {total}
Unique Topics: {unique}

Topics by Frequency:
{topic_summary}

Task: Create a SHORT, focused response with:
1. Most Important Topics (top 3-5 by frequency only)
2. Study Priority (high/medium/low)
3. Brief frequency breakdown

Keep it UNDER 5 bullet points. Focus on quick reference.
Do NOT repeat raw questions. Keep response SHORT."""
    
    print(f"\n📊 Sending CLEAN GROUPED DATA to LLM (not raw questions)")
    print(f"Topics: {len(topics_list)}, Total Questions: {total}")
    
    response = llm_model.invoke(prompt)
    raw_response = response.content
    
    # Structure the LLM response
    structured = structure_llm_output(raw_response, return_format="json")
    
    return structured


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Chat endpoint with 2 modes:
    1. Analysis Mode - for "most asked questions" type queries
    2. Detailed Mode - for specific questions and explanations
    """
    
    # Detect query mode
    mode = detect_query_mode(req.message)
    
    # ANALYSIS MODE: Return frequency analysis
    if mode == "analysis":
        intercept_result = intercept_query(req.message)
        if intercept_result:
            structured = format_mongodb_response(intercept_result)
            return {
                "reply": structured,
                "thinking": None
            }
    
    # DETAILED MODE: Answer with exam-style details
    # Get context from similar questions
    context = get_context_for_detailed(req.message)
    
    detailed_prompt = f"""You are DTUGPT, an expert academic assistant for exam preparation.

Your task: Answer the student's question concisely and clearly.

Context (Similar questions from past papers):
{context if context else "No specific context available"}

Student's Question:
{req.message}

Requirements:
1. Keep answer concise (max 5-6 bullet points)
2. Format:
   - Main Concept (1-2 lines)
   - Key Points (3-5 bullets)
   - Important for Exam (1-2 key takeaways)
3. Use bullet points, not paragraphs
4. Include formulas only if essential
5. Focus on exam relevance

Keep it SHORT and ORGANIZED, not lengthy."""
    
    # Call LLM with detailed prompt
    response = llm_model.invoke(detailed_prompt)
    raw_text = response.content

    # Extract and remove thinking if present
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