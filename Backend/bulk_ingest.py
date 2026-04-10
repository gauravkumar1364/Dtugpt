"""
Bulk Ingestion Script for DTU PYQ Assistant
Processes all PDFs from folder structure and stores them in MongoDB
"""

import os
import sys
from pathlib import Path
from main import process_pdf, load_questions_from_db

# Configuration
BASE_FOLDER = "DTU PYQs COE (2024 Updated)"  # folder from gdown
SUPPORTED_FORMATS = {".pdf", ".PDF"}

# Statistics
stats = {
    "total_files": 0,
    "successful": 0,
    "failed": 0,
    "skipped": 0,
    "total_questions": 0
}


def process_all_subjects():
    """
    Iterate through folder structure and process all PDFs
    
    Expected structure:
    download/
        CO305 (subject folder)
            2018.pdf
            2019.pdf
            2020.pdf
        CS701 (subject folder)
            2018.pdf
            2019.pdf
        ...
    """
    
    # Check if download folder exists
    if not os.path.exists(BASE_FOLDER):
        print(f"❌ Error: '{BASE_FOLDER}' folder not found!")
        print(f"📁 Please ensure PDFs are downloaded with gdown to '{BASE_FOLDER}' folder")
        return
    
    print(f"🚀 Starting Bulk Ingestion from '{BASE_FOLDER}/'")
    print("=" * 60)
    
    # Load existing questions into memory (for deduplication)
    print("📚 Loading existing questions...")
    load_questions_from_db()
    print("✅ Questions loaded\n")
    
    # Iterate through subjects (top-level folders)
    subjects = os.listdir(BASE_FOLDER)
    
    for subject in sorted(subjects):
        subject_path = os.path.join(BASE_FOLDER, subject)
        
        # Skip if not a directory
        if not os.path.isdir(subject_path):
            continue
        
        # Subject folder
        print(f"\n📘 SUBJECT: {subject}")
        print("-" * 60)
        
        # List all files in subject folder
        files = os.listdir(subject_path)
        pdf_files = [f for f in files if any(f.lower().endswith(fmt) for fmt in SUPPORTED_FORMATS)]
        
        if not pdf_files:
            print(f"   ⚠️  No PDF files found in this folder")
            stats["skipped"] += 1
            continue
        
        # Process each PDF
        for file in sorted(pdf_files):
            file_path = os.path.join(subject_path, file)
            
            # Extract year from filename (remove .pdf extension)
            year = file.replace(".pdf", "").replace(".PDF", "")
            
            print(f"   📄 Processing: {file}")
            
            # Process the PDF
            result = process_pdf(file_path, subject.lower(), year)
            
            # Update statistics
            stats["total_files"] += 1
            
            if result["status"] == "success":
                stats["successful"] += 1
                questions_count = result.get("questions_extracted", 0)
                stats["total_questions"] += questions_count
                
                if questions_count > 0:
                    print(f"      ✅ Success: {questions_count} questions extracted")
                else:
                    print(f"      ⚠️  Skipped: No questions found")
                    stats["skipped"] += 1
            else:
                stats["failed"] += 1
                error = result.get("error", "Unknown error")
                print(f"      ❌ Error: {error}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total Files Processed:   {stats['total_files']}")
    print(f"✅ Successful:           {stats['successful']}")
    print(f"❌ Failed:               {stats['failed']}")
    print(f"⚠️  Skipped:             {stats['skipped']}")
    print(f"📝 Total Questions:      {stats['total_questions']}")
    print("=" * 60)
    print("✨ Bulk ingestion complete!")


if __name__ == "__main__":
    try:
        process_all_subjects()
    except KeyboardInterrupt:
        print("\n\n⚠️  Bulk ingestion interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
