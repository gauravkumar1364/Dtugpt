import os
import re
import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
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
from services.response_formatter import structure_llm_output, clean_markdown
from services.result_service import fetch_result, get_result_by_details
from db import ensure_indexes

# Load environment variables
load_dotenv()

# Lazy-initialize LLM to prevent startup crashes
llm_model = None


def invoke_llm_with_timeout_sync(llm, prompt: str, timeout_seconds: int = 20):
    """Run llm.invoke with a hard timeout to avoid hanging requests."""
    result = {"response": None, "error": None}

    def worker():
        try:
            result["response"] = llm.invoke(prompt)
        except Exception as e:
            result["error"] = e

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        print(f"⚠️  LLM invoke timed out after {timeout_seconds}s")
        return None
    if result["error"] is not None:
        raise result["error"]
    return result["response"]

def get_llm_model():
    """Lazy-initialize LLM (prevents crashes if API key missing)"""
    global llm_model
    if llm_model is None:
        if not os.getenv("GROQ_API_KEY"):
            print("⚠️  GROQ_API_KEY not configured")
            return None
        try:
            llm_model = ChatGroq(
                model="llama-3.1-8b-instant",
                max_tokens=320,
                temperature=0.2,
                timeout=12,
                max_retries=1,
            )
            print("✅ LLM initialized")
        except Exception as e:
            print(f"❌ LLM init failed: {e}")
            return None
    return llm_model


# ==================== LIFESPAN EVENTS ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Non-blocking startup so Render can detect open port quickly."""
    async def warmup() -> None:
        try:
            print("⏳ Warmup: ensuring MongoDB indexes...")
            await asyncio.to_thread(ensure_indexes)
            print("⏳ Warmup: loading questions and FAISS index...")
            await asyncio.to_thread(load_questions_from_db)
            print("✅ Warmup completed")
        except Exception as e:
            print(f"⚠️  Warmup failed: {str(e)[:120]}")

    asyncio.create_task(warmup())
    print("✅ App startup complete (warmup running in background)")

    yield
    
    print("🛑 Shutting down DTU PYQ Assistant")

# Initialize FastAPI with lifespan
app = FastAPI(title="DTU PYQ Assistant", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dtugpt-rose.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "DTU GPT API is running 🚀", "status": "healthy"}

@app.options("/chat")
async def options_chat():
    """CORS preflight for /chat endpoint"""
    return {"message": "OK"}

@app.get("/test")
def test():
    """Test endpoint to verify app is running"""
    return {"status": "API is working", "timestamp": str(__import__('datetime').datetime.now())}

# ==================== DEBUG ENDPOINTS ====================

@app.post("/debug/instant")
def debug_instant():
    """Instant response test - if this works, backend is fine"""
    return {"response": "instant reply", "status": "backend working"}

@app.post("/debug/search")
def debug_search(req: ChatRequest):
    """Test FAISS search only"""
    print("🔵 DEBUG SEARCH START")
    try:
        print("🔵 Calling search_similar()...")
        results = search_similar(req.message, top_k=5)
        print(f"✅ Search completed: {len(results)} results")
        return {
            "status": "search ok",
            "results_count": len(results),
            "results": results[:2]  # Return first 2
        }
    except Exception as e:
        print(f"❌ Search error: {e}")
        return {"status": "search failed", "error": str(e)}

@app.post("/debug/llm")
def debug_llm(req: ChatRequest):
    """Test LLM call only"""
    print("🔵 DEBUG LLM START")
    try:
        print("🔵 Getting LLM model...")
        llm = get_llm_model()
        
        if not llm:
            return {"status": "llm unavailable", "error": "GROQ_API_KEY not set"}
        
        print("🔵 Calling LLM.invoke()...")
        prompt = f"Answer briefly: {req.message}"
        response = invoke_llm_with_timeout_sync(llm, prompt, timeout_seconds=20)
        if response is None:
            return {"status": "llm timeout", "error": "LLM call exceeded timeout"}
        print(f"✅ LLM response received: {len(response.content)} chars")
        
        return {
            "status": "llm ok",
            "response": response.content[:500]  # First 500 chars
        }
    except Exception as e:
        print(f"❌ LLM error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "llm failed", "error": str(e)}

@app.post("/debug/search-then-llm")
def debug_search_then_llm(req: ChatRequest):
    """Test FAISS search + LLM"""
    print("🔵 DEBUG SEARCH + LLM START")
    try:
        print("🔵 Step 1: Search...")
        results = search_similar(req.message, top_k=3)
        print(f"✅ Search done: {len(results)} results")
        
        print("🔵 Step 2: Get LLM...")
        llm = get_llm_model()
        if not llm:
            return {"status": "llm unavailable"}
        
        print("🔵 Step 3: Call LLM...")
        prompt = f"Topic: {req.message}\nContext: {len(results)} found"
        response = invoke_llm_with_timeout_sync(llm, prompt, timeout_seconds=20)
        if response is None:
            return {"status": "llm timeout", "search_results": len(results)}
        print(f"✅ LLM done")
        
        return {
            "status": "ok",
            "search_results": len(results),
            "llm_response": response.content[:300]
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

# ==================== BULK INGESTION FUNCTION ====================

def process_pdf(file_path: str, subject: str, year: str = None) -> dict:
    """
    Process a single PDF file and store questions in database
    
    Args:
        file_path: Path to the PDF file
        subject: Subject/course code (e.g., "CO305", "itc", "dbms")
        year: Year/semester (e.g., "2018", "2020", optional)
    
    Returns:
        dict with processing results
    """
    try:
        # Read PDF file
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        # Extract text from PDF
        text = extract_text_from_pdf(file_bytes)
        
        # Extract questions using LLM
        questions = clean_and_extract_questions_with_llm(text)
        
        if not questions:
            return {
                "status": "success",
                "file": file_path,
                "subject": subject,
                "year": year,
                "questions_extracted": 0,
                "skip_reason": "No questions extracted"
            }
        
        # Store questions in database and FAISS
        store_questions(subject, questions)
        
        return {
            "status": "success",
            "file": file_path,
            "subject": subject,
            "year": year,
            "questions_extracted": len(questions)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "file": file_path,
            "subject": subject,
            "year": year,
            "error": str(e)
        }


# ==================== FILE TRACKING FOR BULK INGESTION ====================

def is_processed(file_path: str) -> bool:
    """Check if a file has already been processed"""
    from db import processed_files
    return processed_files.find_one({"file_path": file_path}) is not None


def mark_processed(file_path: str, subject: str, questions_count: int) -> None:
    """Mark a file as processed with metadata"""
    from db import processed_files
    from datetime import datetime
    
    processed_files.insert_one({
        "file_path": file_path,
        "subject": subject,
        "questions_extracted": questions_count,
        "processed_at": datetime.now()
    })


def get_processed_count(folder_path: str = None) -> int:
    """Get total number of processed files (optionally filtered by folder)"""
    from db import processed_files
    
    if folder_path:
        return processed_files.count_documents({"file_path": {"$regex": folder_path}})
    return processed_files.count_documents({})


# ==================== MODE DETECTION ====================

def detect_query_mode(message: str) -> str:
    """
    Detect query type:
    
    "analysis" mode: "most asked", "important", "frequency", "topics"
    "questions" mode: "questions", "predict", "pyq", "past year", "what questions"
    "explanation" mode: everything else (concepts, explanations, how-to)
    """
    msg_lower = message.lower()
    
    # Analysis mode keywords
    analysis_keywords = [
        "most asked", "important", "frequency", "topics", 
        "trending", "repeated", "common", "usually", "often",
        "statistics", "summary", "overview"
    ]
    
    # Questions mode keywords
    question_keywords = [
        "question", "predict", "pyq", "past year", "previous",
        "expect", "probable", "likely", "coming", "exam question",
        "will ask", "might ask"
    ]
    
    for keyword in analysis_keywords:
        if keyword in msg_lower:
            return "analysis"
    
    for keyword in question_keywords:
        if keyword in msg_lower:
            return "questions"
    
    # Default is explanation mode
    return "explanation"

def detect_subject(message: str) -> Optional[str]:
    """Detect subject from user query and return canonical subject key."""
    msg_lower = message.lower()

    subject_keywords = {
        "fom": ["fom", "fundamentals of management", "fundamental of management", "management"],
        "dbms": ["dbms", "database management system", "database"],
        "itc": ["itc", "internet technologies", "internet technology"],
        "dsa": ["dsa", "data structures", "data structure", "algorithm", "algorithms"],
        "os": ["os", "operating system", "operating systems"],
        "coa": ["coa", "computer organization", "computer architecture"],
        "se": ["se", "software engineering"],
        "oops": ["oops", "oop", "object oriented", "object-oriented"],
        "cn": ["cn", "computer networks", "networking"],
    }

    for subject_key, keywords in subject_keywords.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", msg_lower):
                return subject_key

    return None


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


def extract_roll_number(message: str) -> Optional[dict]:
    """
    Extract roll number and batch from message
    Patterns: "2K19/EC/107" or "23/SE/064" etc.
    """
    # Pattern for roll numbers like 2K19/EC/107 or 23/SE/064
    roll_pattern = r"(\d{1,4}[KA-Z]?\d{2}\/[A-Z]+\/\d{3})"
    match = re.search(roll_pattern, message)
    
    if match:
        roll = match.group(1).strip()
        # Extract batch year (first 2 or 4 digits)
        batch_match = re.match(r"(\d{4}|\d{2})", roll)
        batch = batch_match.group(1) if batch_match else "2027"
        
        print(f"🔍 Found roll number: {roll}, batch: {batch}")
        return {"roll": roll, "batch": batch}
    
    return None


def get_student_details(roll: str, batch: str) -> Optional[dict]:
    """
    Fetch student details from ResultHub
    """
    try:
        result = fetch_result(roll, batch)
        if "error" not in result and "cgpa" in result:
            return result
    except Exception as e:
        print(f"⚠️  Could not fetch student details: {e}")
    
    return None


def format_student_info(student_details: dict) -> str:
    """Format student details for LLM context"""
    if not student_details:
        return ""
    
    info = f"""
Student Information:
- Name: {student_details.get('name', 'N/A')}
- CGPA: {student_details.get('cgpa', 'N/A')}
- SGPA: {student_details.get('sgpa', 'N/A')}
- Batch: {student_details.get('batch', 'N/A')}
- Email: {student_details.get('email', 'N/A')}
"""
    
    if student_details.get('subjects'):
        info += "\nSubjects Taken:\n"
        for subject in student_details['subjects'][:10]:
            info += f"- {subject.get('code', 'N/A')}: {subject.get('name', 'N/A')} ({subject.get('grade', 'N/A')})\n"
    
    return info


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
    Generate EXPECTED EXAM QUESTIONS based on past year patterns
    Exam prediction engine - not notes generator
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
            if sample_q not in all_questions_list:
                all_questions_list.append(sample_q)
    
    # Format questions as numbered list
    formatted_questions = "\n".join([
        f"{i}. {q}" 
        for i, q in enumerate(all_questions_list[:20], 1)  # Top 20 questions
    ])
    

Here are past year questions for {subject}:

Task:
Rules:
- Focus on most repeated patterns
1. Most Expected (High frequency patterns - most likely to appear)
2. Moderate (Medium frequency patterns)
3. Concept-based (Varied patterns testing concepts)

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
- Under 150 words total"""
    
    print(f"\n🔥 EXAM PREDICTION ENGINE for {subject}")
    print(f"Analyzing {len(all_questions_list)} questions to predict exam patterns")
    
    llm = get_llm_model()
    if not llm:
        return {"title": "Service Unavailable", "formatted_markdown": "LLM not available", "sections": []}
    
    response = invoke_llm_with_timeout_sync(llm, prompt, timeout_seconds=20)
    if response is None:
        return {"title": "Timeout", "formatted_markdown": "LLM request timed out", "sections": []}
    raw_response = response.content
    

@app.post("/chat-test")
async def chat_test(req: ChatRequest):
    """Simple /chat alternative - returns fast if issues exist"""
    print(f"🔵 CHAT-TEST: {req.message[:50]}")
    return {
        "reply": {"formatted_markdown": "Test response - real /chat working check"},
        "thinking": None,
        "student_data": None
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Chat endpoint with 3 modes:
    1. Analysis Mode - frequency analysis for "most asked" queries
    2. Questions Mode - predict likely exam questions
    3. Explanation Mode - provide concept explanations and details
    """
    try:
        print(f"🔵 CHAT STARTED: {req.message[:50]}")
        
        # FEATURE 1: Extract roll number and fetch student details
        print("🔵 Extracting roll number...")
        student_roll_info = extract_roll_number(req.message)
        student_details = None
        student_context = ""
        
        if student_roll_info:
            student_details = get_student_details(
                student_roll_info["roll"], 
                student_roll_info["batch"]
            )
            if student_details:
                student_context = format_student_info(student_details)
                print(f"✅ Student data fetched for {student_roll_info['roll']}")
        
        # Detect query mode
        mode = detect_query_mode(req.message)
        print(f"📋 Query Mode: {mode}")
        
        # ========== ANALYSIS MODE: Return frequency analysis ==========
        if mode == "analysis":
            intercept_result = intercept_query(req.message)
            if intercept_result:
                structured = format_mongodb_response(intercept_result)
                return {
                    "reply": structured,
                    "thinking": None,
                    "student_data": student_details if student_context else None
                }
        
        # Get similar questions for context
        print("🔵 Starting search_similar()...")
        search_results = search_similar(req.message, top_k=10)
        print(f"✅ Search completed: {len(search_results)} results")
        
        # ========== QUESTIONS MODE: Generate expected exam questions ==========
        if mode == "questions":
            # Format ACTUAL questions for LLM
            questions_text = ""
            if search_results:
                formatted_questions = []
                for i, q in enumerate(search_results, 1):
                    formatted_questions.append(f"{i}. {q.get('question', '')}")
                questions_text = "\n".join(formatted_questions)
            
            # Build prompt for QUESTION PREDICTION
            questions_prompt = f"""You are an exam assistant and student advisor.

{student_context}

Topic: {req.message}

Subject Focus: {detected_subject or 'general'}

Here are related past year questions:

{questions_text}

Task:
Generate expected exam questions based on repeated patterns.

Rules:
- Focus on most repeated patterns
- Do NOT explain concepts
- ONLY output questions
- Keep questions strictly within subject focus: {detected_subject or 'general'}
- Do not include thinking, reasoning traces, or <think> tags
- Group into:
   1. Most Expected (High frequency)
   2. Moderate (Medium frequency)
   3. Concept-based

Output clean and concise.

Format:

## Most Expected Questions
- Question 1
- Question 2

## Moderate Questions
- Question 1
- Question 2

## Concept-based Questions
- Question 1
- Question 2

Rules:
- ONLY output questions
- NO explanations or key points
- Concise format
- Under 100 words total"""  
            
            llm = get_llm_model()
            if not llm:
                return {"reply": {"formatted_markdown": "LLM unavailable"}, "thinking": None, "student_data": student_details if student_context else None}
            
            print("🔵 Invoking LLM for questions mode...")
            response = invoke_llm_with_timeout_sync(llm, questions_prompt, timeout_seconds=12)
            if response is None:
                return {"reply": {"formatted_markdown": "LLM timeout, please try again."}, "thinking": None, "student_data": student_details if student_context else None}
            print("✅ LLM response received")
            raw_text = response.content
        
        # ========== EXPLANATION MODE: Provide concept explanation ==========
        else:
            # Format reference questions for context
            context_questions = ""
            if search_results:
                formatted_questions = []
                for i, q in enumerate(search_results[:5], 1):
                    formatted_questions.append(f"{i}. {q.get('question', '')}")
                context_questions = "\n".join(formatted_questions)
            
            # Build prompt for EXPLANATION
            explanation_prompt = f"""You are an exam assistant and student advisor.

{student_context}

Topic: {req.message}

Subject Focus: {detected_subject or 'general'}

Related past year questions:
{context_questions}

Task:
Provide a comprehensive but concise explanation of the topic. Include:
1. Definition and key concepts
2. Important points and formulas
3. Common applications or examples
4. Why it's important for exams

Format:
- Use bullet points for clarity
- Bold important terms
- Keep it under 300 words
- Do not include thinking, reasoning traces, or <think> tags
- Keep explanation strictly within subject focus: {detected_subject or 'general'}
- Make it student-friendly"""
            
            llm = get_llm_model()
            if not llm:
                return {"reply": {"formatted_markdown": "LLM unavailable"}, "thinking": None, "student_data": student_details if student_context else None}
            
            print("🔵 Invoking LLM for explanation mode...")
            response = invoke_llm_with_timeout_sync(llm, explanation_prompt, timeout_seconds=12)
            if response is None:
                return {"reply": {"formatted_markdown": "LLM timeout, please try again."}, "thinking": None, "student_data": student_details if student_context else None}
            print("✅ LLM response received")
            raw_text = response.content

        # Extract and remove thinking if present
        thinking = re.search(r"<think>([\s\S]*?)</think>", raw_text)
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()
        thinking_text = None

        # Structure the response
        print("🔵 Structuring response...")
        structured = structure_llm_output(cleaned, return_format="json")

        print("✅ CHAT COMPLETED - Returning response")
        return {
            "reply": structured,
            "thinking": thinking_text,
            "student_data": student_details if student_context else None
        }
    
    except Exception as e:
        print(f"❌ Chat endpoint error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "reply": {"formatted_markdown": f"Error processing your request: {str(e)[:100]}"}, 
            "thinking": None, 
            "student_data": None
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


@app.post("/bulk-ingest")
async def bulk_ingest(folder_path: str):
    """
    🥇 INDUSTRY-LEVEL BULK INGESTION WITH RESUME CAPABILITY
    
    Processes all PDFs in a folder with automatic tracking.
    If processing is interrupted, just call again - skips already processed files!
    
    Args:
        folder_path: Path to folder containing PDFs
                     e.g., "Backend/DTU PYQs COE (2024 Updated)"
    
    Returns:
        Detailed ingestion report with resume capability
    """
    try:
        results = {
            "queued": [],
            "skipped": [],
            "processed": [],
            "errors": []
        }
        
        # Check if folder exists
        if not os.path.isdir(folder_path):
            return {
                "error": f"Folder not found: {folder_path}",
                "status": "failed"
            }
        
        # Find all PDF files recursively
        pdf_files = list(Path(folder_path).glob("**/*.pdf"))
        
        if not pdf_files:
            return {
                "message": "No PDF files found in folder",
                "folder": folder_path,
                "status": "no_files"
            }
        
        print(f"\n📂 BULK INGESTION STARTED")
        print(f"📁 Folder: {folder_path}")
        print(f"📄 Total PDFs found: {len(pdf_files)}")
        print(f"✅ Already processed: {get_processed_count(folder_path)}")
        
        # Process each PDF
        for idx, pdf_path in enumerate(pdf_files, 1):
            file_path_str = str(pdf_path)
            filename = pdf_path.name
            
            # 🔥 CHECK IF ALREADY PROCESSED
            if is_processed(file_path_str):
                print(f"⏩ [{idx}/{len(pdf_files)}] Skipping (already done): {filename}")
                results["skipped"].append({
                    "file": filename,
                    "reason": "already_processed"
                })
                continue
            
            # Extract subject from filename
            filename_clean = pdf_path.stem.lower()
            
            if '_' in filename_clean:
                subject = filename_clean.split('_')[0]
            elif '-' in filename_clean:
                subject = filename_clean.split('-')[0]
            else:
                subject = filename_clean
            
            print(f"🔄 [{idx}/{len(pdf_files)}] Processing: {filename} → Subject: {subject}")
            
            try:
                # Process the PDF
                result = process_pdf(file_path_str, subject=subject)
                
                if result["status"] == "success":
                    questions_count = result.get("questions_extracted", 0)
                    
                    # ✅ MARK AS PROCESSED ONLY IF SUCCESSFUL
                    mark_processed(file_path_str, subject, questions_count)
                    
                    results["processed"].append({
                        "file": filename,
                        "subject": subject,
                        "questions_extracted": questions_count
                    })
                    print(f"   ✅ Success: {questions_count} questions extracted")
                else:
                    # If no questions extracted, still mark as processed to avoid retry
                    if questions_count == 0:
                        mark_processed(file_path_str, subject, 0)
                        results["skipped"].append({
                            "file": filename,
                            "reason": "no_questions_extracted"
                        })
                        print(f"   ⚠️  Skipped: No questions found")
                    else:
                        results["errors"].append({
                            "file": filename,
                            "error": result.get("error", "Unknown error")
                        })
                        print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                results["errors"].append({
                    "file": filename,
                    "error": str(e)
                })
                print(f"   ❌ Exception: {str(e)}")
        
        # Summary
        total_questions = sum(r.get("questions_extracted", 0) for r in results["processed"])
        
        summary = {
            "status": "completed",
            "folder": folder_path,
            "summary": {
                "total_pdfs_found": len(pdf_files),
                "newly_processed": len(results["processed"]),
                "skipped_already_done": len(results["skipped"]),
                "errors": len(results["errors"]),
                "total_questions_ingested": total_questions
            },
            "resume_info": {
                "if_interrupted": "Just call this endpoint again with same folder_path",
                "skipped_files_will_not_reprocess": True,
                "processing_can_resume": True
            },
            "details": results
        }
        
        print(f"\n🎉 BULK INGESTION COMPLETED")
        print(f"✅ Newly processed: {len(results['processed'])}")
        print(f"⏩ Skipped: {len(results['skipped'])}")
        print(f"❌ Errors: {len(results['errors'])}")
        print(f"📊 Total questions: {total_questions}")
        
        return summary
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
            "folder": folder_path
        }


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


@app.get("/status")
async def bulk_ingest_status():
    """Get bulk ingestion system status and statistics"""
    try:
        total_questions = get_question_count()
        processed_count = processed_files.count_documents({})
        subjects = get_subjects_stats()
        
        # Get recent processed files
        recent_files = list(processed_files.find().sort("processed_at", -1).limit(5))
        
        # Format recent files for response
        recent_files_formatted = []
        for f in recent_files:
            recent_files_formatted.append({
                "file_path": f.get("file_path"),
                "subject": f.get("subject"),
                "questions_extracted": f.get("questions_extracted", 0),
                "processed_at": f.get("processed_at").isoformat() if f.get("processed_at") else None
            })
        
        return {
            "status": "operational",
            "bulk_ingestion": {
                "total_processed_files": processed_count,
                "last_5_processed": recent_files_formatted
            },
            "questions_database": {
                "total_questions": total_questions,
                "subjects": subjects
            },
            "endpoints": {
                "/chat": "✓ Active",
                "/uploadfile": "✓ Active",
                "/bulk-ingest": "✓ Active",
                "/result/{roll}/{batch}": "✓ Active",
                "/stats": "✓ Active"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ==================== RESULT SERVICE - DTU RESULTHUB ====================

@app.get("/result/{roll}/{batch}")
async def get_result_endpoint(roll: str, batch: str):
    """
    Fetch student result from DTU ResultHub
    
    Args:
        roll: Student roll number (e.g., "2K19/EC/107")
        batch: Batch year (e.g., "2019")
    
    Returns:
        Student result with CGPA, SGPA, subjects, grades
    """
    try:
        result = fetch_result(roll, batch)
        return result
    except Exception as e:
        return {"error": str(e), "roll": roll, "batch": batch}


@app.get("/result/search")
async def search_result(name: Optional[str] = None, roll: str = None, batch: str = None):
    """
    Search student result by name and/or roll number
    
    Args:
        name: Student name (optional)
        roll: Student roll number
        batch: Batch year
    
    Returns:
        Student result
    """
    try:
        result = get_result_by_details(name=name, roll=roll, batch=batch)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/result/debug/{roll}/{batch}")
async def debug_result(roll: str, batch: str):
    """
    DEBUG ENDPOINT: Get raw HTML and parsed structure
    Use this to inspect what the website actually returns
    
    Args:
        roll: Student roll number
        batch: Batch year
    
    Returns:
        Raw HTML snippet and debug info
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = f"https://www.resulthubdtu.com/DTU/StudentProfile/{batch}/{roll}"
        print(f"\n📍 DEBUG: Fetching {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get HTML statistics
        tables = soup.find_all("table")
        divs = soup.find_all("div", class_=lambda x: x and ("table" in (x or "").lower()))
        paragraphs = soup.find_all("p")
        
        # Extract sample of each section
        debug_info = {
            "url": url,
            "status_code": response.status_code,
            "html_length": len(response.text),
            "tables_found": len(tables),
            "div_containers_found": len(divs),
            "paragraphs_found": len(paragraphs),
            
            # Sample HTML
            "first_table_html": str(tables[0])[:500] if tables else None,
            "first_250_chars": response.text[:250],
            "paragraphs_sample": [p.get_text(strip=True)[:100] for p in paragraphs[:10]],
            
            # Try to find grades pattern
            "text_containing_grade": [line for line in response.text.split('\n') if 'grade' in line.lower()][:5],
            "text_containing_subject": [line for line in response.text.split('\n') if 'subject' in line.lower()][:5],
        }
        
        return debug_info
        
    except Exception as e:
        return {
            "error": str(e),
            "roll": roll,
            "batch": batch,
            "message": "Failed to fetch debug info"
        }