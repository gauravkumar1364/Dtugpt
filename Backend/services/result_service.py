import requests
from bs4 import BeautifulSoup
import json
from typing import Optional, Dict, List
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()


def fetch_result_requests(url: str) -> Dict:
    """
    Fetch student result using requests + BeautifulSoup
    Uses robust label-based scraping instead of class names
    
    Args:
        url: Full DTU ResultHub profile URL
    
    Returns:
        Dict with student data: cgpa, sgpa, name, email, batch, semester_data
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        result = {}
        
        # ==================== EXTRACT NAME ====================
        h2_tags = soup.find_all("h2")
        if h2_tags:
            for h2 in h2_tags:
                text = h2.get_text(strip=True)
                if text and len(text) > 5 and "Student" not in text:
                    result["name"] = text
                    break
        
        # ==================== EXTRACT CGPA (Label-based) ====================
        cgpa_label = soup.find("p", string=lambda x: x and "Cumulative CGPA" in x)
        if cgpa_label:
            value_tag = cgpa_label.find_next("p")
            if value_tag:
                result["cgpa"] = value_tag.get_text(strip=True)
        
        # ==================== EXTRACT SGPA (Label-based) ====================
        sgpa_label = soup.find("p", string=lambda x: x and "Semester SGPA" in x)
        if sgpa_label:
            value_tag = sgpa_label.find_next("p")
            if value_tag:
                result["sgpa"] = value_tag.get_text(strip=True)
        
        # ==================== EXTRACT BATCH/YEAR ====================
        batch_label = soup.find("p", string=lambda x: x and "Batch" in x)
        if batch_label:
            value_tag = batch_label.find_next("p")
            if value_tag:
                result["batch"] = value_tag.get_text(strip=True)
        
        # ==================== EXTRACT EMAIL ====================
        email_label = soup.find("p", string=lambda x: x and "Email" in x)
        if email_label:
            value_tag = email_label.find_next("p")
            if value_tag:
                result["email"] = value_tag.get_text(strip=True)
        
        # ==================== EXTRACT SUBJECT GRADES ====================
        result["subjects"] = extract_subject_grades(soup)
        
        # ==================== EXTRACT SEMESTER DATA ====================
        result["semester_data"] = extract_semester_data(soup)
        
        return result
        
    except requests.RequestException as e:
        print(f"❌ Requests error: {e}")
        return {"error": f"Failed to fetch: {str(e)}"}
    except Exception as e:
        print(f"❌ Parsing error: {e}")
        return {"error": f"Failed to parse: {str(e)}"}


def extract_subject_grades(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract subject names and grades from table
    Uses robust table parsing
    """
    subjects = []
    
    try:
        # Find all tables
        tables = soup.find_all("table")
        
        for table in tables:
            rows = table.find_all("tr")
            
            for row in rows:
                cells = row.find_all(["td", "th"])
                
                if len(cells) >= 2:
                    # Try to extract subject code, name, and grade
                    if len(cells) >= 3:
                        code = cells[0].get_text(strip=True)
                        name = cells[1].get_text(strip=True)
                        grade = cells[-1].get_text(strip=True)  # Last cell usually grade
                        
                        if grade and len(code) > 0 and len(name) > 2:
                            subjects.append({
                                "code": code,
                                "name": name,
                                "grade": grade
                            })
    
    except Exception as e:
        print(f"⚠️  Error extracting subjects: {e}")
    
    return subjects


def extract_semester_data(soup: BeautifulSoup) -> Dict:
    """
    Extract semester-wise SGPA and credits
    """
    semester_data = {}
    
    try:
        # Look for semester labels and their data
        paragraphs = soup.find_all("p")
        
        for i, p in enumerate(paragraphs):
            text = p.get_text(strip=True)
            
            # Look for semester patterns: "Sem 1 SGPA", "Semester 1", etc
            if "Semester" in text or "Sem" in text:
                if "SGPA" in text:
                    semester_data[text] = p.find_next("p").get_text(strip=True)
    
    except Exception as e:
        print(f"⚠️  Error extracting semester data: {e}")
    
    return semester_data


def fetch_result_selenium(url: str) -> Dict:
    """
    Fetch student result using Selenium (for JS-rendered pages)
    Use when requests fails or returns incomplete data
    
    Args:
        url: Full DTU ResultHub profile URL
    
    Returns:
        Dict with student data
    """
    driver = None
    try:
        # Setup Chrome options
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "p"))
        )
        
        # Give JS time to render
        time.sleep(2)
        
        # Get rendered HTML
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Parse using same logic as requests version
        result = {}
        
        # Extract using label-based technique
        cgpa_label = soup.find("p", string=lambda x: x and "Cumulative CGPA" in x)
        if cgpa_label:
            value_tag = cgpa_label.find_next("p")
            if value_tag:
                result["cgpa"] = value_tag.get_text(strip=True)
        
        sgpa_label = soup.find("p", string=lambda x: x and "Semester SGPA" in x)
        if sgpa_label:
            value_tag = sgpa_label.find_next("p")
            if value_tag:
                result["sgpa"] = value_tag.get_text(strip=True)
        
        result["subjects"] = extract_subject_grades(soup)
        result["semester_data"] = extract_semester_data(soup)
        
        return result
        
    except Exception as e:
        print(f"❌ Selenium error: {e}")
        return {"error": f"Selenium failed: {str(e)}"}
    
    finally:
        if driver:
            driver.quit()


def fetch_result(roll: str, batch: str) -> Dict:
    """
    Main function to fetch student result
    Tries requests first, falls back to Selenium if needed
    
    Args:
        roll: Student roll number (e.g., "2K19/EC/107")
        batch: Batch year (e.g., "2019")
    
    Returns:
        Dict with complete student result
    """
    # Construct URL
    url = f"https://www.resulthubdtu.com/DTU/StudentProfile/{batch}/{roll}"
    
    print(f"🔍 Fetching result for {roll} (Batch: {batch})")
    print(f"📍 URL: {url}")
    
    # Try requests first (faster)
    result = fetch_result_requests(url)
    
    # If we got data, return it
    if result and "cgpa" in result:
        print(f"✅ Result fetched successfully via requests")
        return result
    
    # If requests failed or incomplete, try Selenium
    print("⚠️  Requests incomplete, trying Selenium...")
    result_selenium = fetch_result_selenium(url)
    
    if result_selenium and "cgpa" in result_selenium:
        print(f"✅ Result fetched successfully via Selenium")
        return result_selenium
    
    # If both failed
    return {
        "error": "Could not fetch result",
        "roll": roll,
        "batch": batch,
        "url": url
    }


def get_result_by_details(name: Optional[str] = None, roll: str = None, batch: str = None) -> Dict:
    """
    Fetch result by student details
    If name provided, search for student first (if needed)
    
    Args:
        name: Student name (optional for search)
        roll: Student roll number
        batch: Batch year
    
    Returns:
        Student result
    """
    if not roll or not batch:
        return {"error": "Roll number and batch year required"}
    
    result = fetch_result(roll, batch)
    
    # If name was provided, verify it matches
    if name and "name" in result:
        if name.lower() not in result["name"].lower():
            return {"error": "Student name doesn't match", "provided": name, "found": result.get("name")}
    
    return result