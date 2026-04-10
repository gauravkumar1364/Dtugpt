#!/usr/bin/env python3
"""
Debug script to inspect DTU ResultHub HTML structure
Run this to understand the website structure and fix subject extraction
"""

import requests
from bs4 import BeautifulSoup
import sys

def debug_html_structure(roll: str, batch: str):
    """
    Analyze the HTML structure of a student profile
    """
    url = f"https://www.resulthubdtu.com/DTU/StudentProfile/{batch}/{roll}"
    
    print(f"\n{'='*80}")
    print(f"🔍 DEBUGGING: {url}")
    print(f"{'='*80}\n")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Check for tables
        print("1️⃣  TABLES ANALYSIS")
        print("-" * 80)
        tables = soup.find_all("table")
        print(f"   Total tables found: {len(tables)}")
        
        for idx, table in enumerate(tables):
            rows = table.find_all("tr")
            cols = table.find_all(["th", "td"])
            print(f"\n   Table {idx}:")
            print(f"   - Rows: {len(rows)}")
            print(f"   - Total cells: {len(cols)}")
            
            # Show first 3 rows
            print(f"   - First 3 rows:")
            for r_idx, row in enumerate(rows[:3]):
                cells = row.find_all(["td", "th"])
                cell_texts = [cell.get_text(strip=True)[:30] for cell in cells]
                print(f"     Row {r_idx}: {cell_texts}")
        
        # 2. Check for divs with class containing 'table'
        print("\n\n2️⃣  DIV-BASED TABLES")
        print("-" * 80)
        div_tables = soup.find_all("div", class_=lambda x: x and "table" in x.lower())
        print(f"   Divs with 'table' in class: {len(div_tables)}")
        
        for idx, div in enumerate(div_tables[:3]):
            print(f"\n   Div {idx}:")
            print(f"   - Classes: {div.get('class')}")
            rows = div.find_all("div", class_=lambda x: x and "row" in x.lower())
            print(f"   - Row divs: {len(rows)}")
            
            # Show first row
            if rows:
                cells = rows[0].find_all("div", class_=lambda x: x and "col" in x.lower())
                print(f"   - Cells in first row: {len(cells)}")
                for c_idx, cell in enumerate(cells[:3]):
                    print(f"     Cell {c_idx}: {cell.get_text(strip=True)[:40]}")
        
        # 3. All divs with any subject-related text
        print("\n\n3️⃣  SUBJECT/GRADE PATTERN SEARCH")
        print("-" * 80)
        all_text = soup.get_text()
        lines = [line.strip() for line in all_text.split('\n') if line.strip() and len(line.strip()) > 5]
        
        # Find lines with grade patterns
        grades = ["A+", "A", "B+", "B", "C+", "C", "D+", "D", "F"]
        grade_lines = [line for line in lines if any(grade in line for grade in grades)]
        
        print(f"   Lines containing grades ({len(grade_lines)} found):")
        for line in grade_lines[:10]:
            print(f"   - {line}")
        
        # Find potential subject codes (typically alphanumeric starting with letter)
        import re
        code_pattern = r'\b[A-Z]{2,4}\d{3,4}\b'
        codes = re.findall(code_pattern, all_text)
        
        print(f"\n   Potential subject codes found ({len(set(codes))} unique):")
        for code in list(set(codes))[:10]:
            print(f"   - {code}")
        
        # 4. Check specific elements
        print("\n\n4️⃣  KEY ELEMENTS")
        print("-" * 80)
        
        # CGPA
        cgpa_label = soup.find("p", string=lambda x: x and "Cumulative CGPA" in x)
        if cgpa_label:
            cgpa_val = cgpa_label.find_next("p")
            print(f"   ✅ CGPA found: {cgpa_val.get_text(strip=True) if cgpa_val else 'N/A'}")
        else:
            print(f"   ❌ CGPA not found with standard label")
        
        # Find all p tags with numbers that might be CGPA
        all_p = soup.find_all("p")
        print(f"\n   All <p> tags ({len(all_p)} total):")
        for idx, p in enumerate(all_p[:15]):
            text = p.get_text(strip=True)
            print(f"   P{idx}: {text[:60]}")
        
        # 5. Raw HTML snippet of main content area
        print("\n\n5️⃣  HTML STRUCTURE SNIPPET")
        print("-" * 80)
        main = soup.find("main") or soup.find("div", class_="container") or soup.find("div", id="app")
        if main:
            html_snippet = str(main)[:1000]
            print(f"   Main content (first 1000 chars):")
            print(html_snippet)
        else:
            print(f"   First 1000 chars of HTML:")
            print(response.text[:1000])
        
        # 6. Save full HTML to file for inspection
        html_file = f"debug_html_{roll}_{batch}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"\n\n6️⃣  FULL HTML SAVED")
        print("-" * 80)
        print(f"   Full HTML saved to: {html_file}")
        print(f"   File size: {len(response.text)} bytes")
        
        print(f"\n{'='*80}")
        print("Debug analysis complete!")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_results.py <roll> <batch>")
        print("Example: python debug_results.py 2K19/EC/107 2019")
        sys.exit(1)
    
    roll = sys.argv[1]
    batch = sys.argv[2]
    
    debug_html_structure(roll, batch)
