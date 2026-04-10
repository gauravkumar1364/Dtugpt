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
        
        print(f"\n🔍 Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        result = {}
        
        # ==================== EXTRACT NAME ====================
        print("📝 Extracting name...")
        h2_tags = soup.find_all("h2")
        if h2_tags:
            for h2 in h2_tags:
                text = h2.get_text(strip=True)
                if text and len(text) > 5 and "Student" not in text:
                    result["name"] = text
                    print(f"   ✅ Name: {text}")
                    break
        
        # ==================== EXTRACT CGPA (Label-based) ====================
        print("💯 Extracting CGPA...")
        cgpa_label = soup.find("p", string=lambda x: x and "Cumulative CGPA" in x)
        if cgpa_label:
            value_tag = cgpa_label.find_next("p")
            if value_tag:
                result["cgpa"] = value_tag.get_text(strip=True)
                print(f"   ✅ CGPA: {result['cgpa']}")
        else:
            print("   ⚠️  CGPA label not found")
        
        # ==================== EXTRACT SGPA (Label-based) ====================
        print("📊 Extracting SGPA...")
        sgpa_label = soup.find("p", string=lambda x: x and "Semester SGPA" in x)
        if sgpa_label:
            value_tag = sgpa_label.find_next("p")
            if value_tag:
                result["sgpa"] = value_tag.get_text(strip=True)
                print(f"   ✅ SGPA: {result['sgpa']}")
        else:
            print("   ⚠️  SGPA label not found")
        
        # ==================== EXTRACT BATCH/YEAR ====================
        print("🎓 Extracting batch...")
        batch_label = soup.find("p", string=lambda x: x and "Batch" in x)
        if batch_label:
            value_tag = batch_label.find_next("p")
            if value_tag:
                result["batch"] = value_tag.get_text(strip=True)
                print(f"   ✅ Batch: {result['batch']}")
        else:
            print("   ⚠️  Batch label not found")
        
        # ==================== EXTRACT EMAIL ====================
        print("📧 Extracting email...")
        email_label = soup.find("p", string=lambda x: x and "Email" in x)
        if email_label:
            value_tag = email_label.find_next("p")
            if value_tag:
                result["email"] = value_tag.get_text(strip=True)
                print(f"   ✅ Email: {result['email']}")
        else:
            print("   ⚠️  Email label not found")
        
        # ==================== EXTRACT SUBJECT GRADES ====================
        print("📚 Extracting subject grades...")
        result["subjects"] = extract_subject_grades(soup)
        
        # ==================== EXTRACT SEMESTER DATA ====================
        print("📈 Extracting semester data...")
        result["semester_data"] = extract_semester_data(soup)
        
        print(f"\n✅ Extraction complete")
        return result
        
    except requests.RequestException as e:
        print(f"❌ Requests error: {e}")
        return {"error": f"Failed to fetch: {str(e)}"}
    except Exception as e:
        print(f"❌ Parsing error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to parse: {str(e)}"}


def extract_subject_grades(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract subject names and grades from various table formats
    Supports traditional tables, div-based tables, and multiple formats
    """
    subjects = []
    
    try:
        # ==================== METHOD 1: Traditional HTML Tables ====================
        tables = soup.find_all("table")
        print(f"🔍 Found {len(tables)} tables")
        
        for table_idx, table in enumerate(tables):
            rows = table.find_all("tr")
            print(f"   Table {table_idx}: {len(rows)} rows")
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(["td", "th"])
                
                # Skip header rows and empty rows
                if len(cells) < 2:
                    continue
                
                # Try different extraction patterns
                # Pattern 1: [Code, Name, ..., Grade]
                if len(cells) >= 3:
                    code = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True)
                    grade = cells[-1].get_text(strip=True)
                    
                    # Validate: code should be alphanumeric, grade should be short
                    if (code and name and grade and 
                        len(name) > 3 and len(grade) <= 3 and
                        any(c.isalpha() for c in code)):  # Has letters
                        
                        subjects.append({
                            "code": code,
                            "name": name,
                            "grade": grade
                        })
                        print(f"   ✅ Row {row_idx}: {code} | {name} | {grade}")
        
        # If we found subjects, return them
        if subjects:
            print(f"✅ Extracted {len(subjects)} subjects from tables")
            return subjects
        
        # ==================== METHOD 2: Div-based Tables ====================
        print("📊 Trying div-based table parsing...")
        
        # Look for tables using divs (common in modern websites)
        table_containers = soup.find_all("div", class_=lambda x: x and ("table" in (x or "").lower() or "subject" in (x or "").lower()))
        print(f"🔍 Found {len(table_containers)} div table containers")
        
        for container in table_containers:
            rows = container.find_all("div", class_=lambda x: x and "row" in (x or "").lower())
            
            for row in rows:
                cells = row.find_all("div", class_=lambda x: x and ("col" in (x or "").lower() or "cell" in (x or "").lower()))
                
                if len(cells) >= 3:
                    try:
                        code = cells[0].get_text(strip=True)
                        name = cells[1].get_text(strip=True)
                        grade = cells[-1].get_text(strip=True)
                        
                        if code and name and grade and len(name) > 3:
                            subjects.append({
                                "code": code,
                                "name": name,
                                "grade": grade
                            })
                            print(f"   ✅ Found: {code} | {name} | {grade}")
                    except:
                        pass
        
        if subjects:
            print(f"✅ Extracted {len(subjects)} subjects from divs")
            return subjects
        
        # ==================== METHOD 3: Parse all text for patterns ====================
        print("🔍 Scanning for subject-grade patterns in text...")
        
        # Look for common grade patterns (A+, A, B+, B, etc.)
        all_text = soup.get_text()
        lines = all_text.split('\n')
        
        current_subject = None
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Look for lines that might contain code + name
            if current_subject is None:
                # Pattern: CO305 Database Systems
                if any(c.isdigit() for c in line) and any(c.isalpha() for c in line):
                    if len(line) > 10:
                        parts = line.split()
                        if len(parts) >= 2 and any(c.isdigit() for c in parts[0]):
                            current_subject = {
                                "code": parts[0],
                                "name": " ".join(parts[1:])
                            }
            else:
                # Look for grade in next relevant line
                if line in ["A+", "A", "B+", "B", "C+", "C", "D+", "D", "F", "P", "NP"]:
                    current_subject["grade"] = line
                    subjects.append(current_subject)
                    current_subject = None
                elif len(line) < 5 and line.upper() == line:  # Short uppercase line might be grade
                    current_subject["grade"] = line
                    subjects.append(current_subject)
                    current_subject = None
        
        if subjects:
            print(f"✅ Extracted {len(subjects)} subjects from text patterns")
            return subjects
        
        print("⚠️  No subjects extracted (table format might be unique)")
        return []
        
    except Exception as e:
        print(f"⚠️  Error extracting subjects: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_semester_data(soup: BeautifulSoup) -> Dict:
    """
    Extract semester-wise SGPA and credits
    Uses robust text pattern matching
    """
    semester_data = {}
    
    try:
        print("🔍 Extracting semester data...")
        
        # Method 1: Look for semester labels and their data
        paragraphs = soup.find_all("p")
        
        for i, p in enumerate(paragraphs):
            text = p.get_text(strip=True)
            
            # Look for semester patterns: "Sem 1 SGPA", "Semester 1", etc
            if "Semester" in text or "Sem" in text:
                if "SGPA" in text:
                    next_p = p.find_next("p")
                    if next_p:
                        value = next_p.get_text(strip=True)
                        semester_data[text] = value
                        print(f"   ✅ {text}: {value}")
        
        # Method 2: Scan all text for semester patterns
        if not semester_data:
            all_text = soup.get_text()
            import re
            
            # Look for patterns like "Sem 1 SGPA: 9.5"
            patterns = re.findall(r'(?:Sem|Semester)\s+(\d+)\s+(?:SGPA|GPA)\s*[:=]?\s*([\d.]+)', all_text, re.IGNORECASE)
            for sem_num, sgpa in patterns:
                key = f"Semester {sem_num} SGPA"
                semester_data[key] = sgpa
                print(f"   ✅ {key}: {sgpa}")
        
        print(f"✅ Extracted {len(semester_data)} semester entries")
        return semester_data
        
    except Exception as e:
        print(f"⚠️  Error extracting semester data: {e}")
        import traceback
        traceback.print_exc()
        return {}


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
        
        print("🌐 Starting Selenium (JS rendering)...")
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        print("⏳ Waiting for page initialization...")
        
        # CRITICAL: Wait for actual data to appear, not just generic elements
        # The page shows "Student not found" message or actual student data
        # We look for H1 or actual content that indicates data loaded
        try:
            # Wait for the main heading to be present and visible
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print("✅ Page heading found")
        except:
            print("⚠️  Page heading not found, continuing anyway")
        
        # Wait a bit more for all JavaScript to execute
        print("⏳ Waiting for JavaScript to render (3 seconds)...")
        time.sleep(3)
        
        # Get the rendered HTML
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Check if we got the error message
        error_msg = soup.find("p", string=lambda x: x and "Student not found" in x)
        if error_msg:
            print("❌ Website returned: Student not found")
            return {"error": "Student not found on website"}
        
        print("📄 Parsing rendered HTML...")
        
        # Parse using same logic as requests version
        result = {}
        
        # Extract NAME - from JSON-LD structured data
        json_ld = soup.find("script", {"type": "application/ld+json"})
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if "name" in data:
                    result["name"] = data["name"]
                    print(f"   ✅ Name: {data['name']}")
                if "description" in data:
                    # Extract CGPA from description
                    import re
                    cgpa_match = re.search(r'CGPA:\s*([\d.]+)', data["description"])
                    if cgpa_match:
                        result["cgpa"] = cgpa_match.group(1)
                        print(f"   ✅ CGPA: {cgpa_match.group(1)}")
            except:
                print("⚠️  Could not parse JSON-LD data")
        
        # Extract using label-based technique as fallback
        cgpa_label = soup.find("p", string=lambda x: x and "Cumulative CGPA" in x)
        if cgpa_label and "cgpa" not in result:
            value_tag = cgpa_label.find_next("p")
            if value_tag:
                result["cgpa"] = value_tag.get_text(strip=True)
                print(f"   ✅ CGPA (from label): {result['cgpa']}")
        
        sgpa_label = soup.find("p", string=lambda x: x and "Semester SGPA" in x)
        if sgpa_label:
            value_tag = sgpa_label.find_next("p")
            if value_tag:
                result["sgpa"] = value_tag.get_text(strip=True)
                print(f"   ✅ SGPA: {result['sgpa']}")
        
        result["subjects"] = extract_subject_grades(soup)
        result["semester_data"] = extract_semester_data(soup)
        
        return result
        
    except Exception as e:
        print(f"❌ Selenium error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Selenium failed: {str(e)}"}
    
    finally:
        if driver:
            print("🔌 Closing Selenium driver")
            driver.quit()


def fetch_result(roll: str, batch: str) -> Dict:
    """
    Main function to fetch student result
    Uses Selenium first (for JS rendering), falls back to requests if needed
    
    Args:
        roll: Student roll number (e.g., "2K19/EC/107")
        batch: Batch year (e.g., "2019")
    
    Returns:
        Dict with complete student result
    """
    # Construct URL
    url = f"https://www.resulthubdtu.com/DTU/StudentProfile/{batch}/{roll}"
    
    print(f"\n{'='*80}")
    print(f"🔍 Fetching result for {roll} (Batch: {batch})")
    print(f"📍 URL: {url}")
    print(f"{'='*80}\n")
    
    # Try Selenium FIRST (since site is JS-rendered)
    print("🥇 Attempt 1: Selenium (JS rendering)...")
    result_selenium = fetch_result_selenium(url)
    
    if result_selenium and "cgpa" in result_selenium and "error" not in result_selenium:
        print(f"\n✅ SUCCESS via Selenium")
        return result_selenium
    
    # If Selenium failed, try requests as fallback
    print("\n🥈 Attempt 2: Requests + BeautifulSoup (fallback)...")
    result_requests = fetch_result_requests(url)
    
    if result_requests and "cgpa" in result_requests and "error" not in result_requests:
        print(f"\n✅ SUCCESS via Requests")
        return result_requests
    
    # If both failed, combine what we got with error info
    print(f"\n❌ Both methods failed")
    return {
        "error": "Could not fetch student result - both methods failed",
        "roll": roll,
        "batch": batch,
        "url": url,
        "selenium_result": result_selenium,
        "requests_result": result_requests
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