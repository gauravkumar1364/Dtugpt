# DTU Result Service - Usage Guide

## Overview

The Result Service fetches student results from DTU ResultHub website using robust scraping techniques.

**Key Features:**

- ✅ Robust label-based scraping (resistant to HTML changes)
- ✅ Extracts CGPA, SGPA, name, email, subjects, grades
- ✅ Requests fallback to Selenium for JS-rendered pages
- ✅ Handles table parsing for subject grades
- ✅ Error handling and validation

---

## API Endpoints

### 1. Get Result by Roll & Batch

**Endpoint:** `GET /result/{roll}/{batch}`

Fetch a student's result using roll number and batch year.

**Parameters:**

- `roll` (string): Student roll number (e.g., "2K19/EC/107")
- `batch` (string): Batch year (e.g., "2019")

**Example:**

```bash
curl "http://localhost:8000/result/2K19/EC/107/2019"
```

**Response:**

```json
{
  "name": "John Doe",
  "cgpa": "9.46",
  "sgpa": "9.5",
  "batch": "2019",
  "email": "john.doe@dtu.ac.in",
  "subjects": [
    {
      "code": "CO305",
      "name": "Data Structures",
      "grade": "A+"
    },
    {
      "code": "CO306",
      "name": "Database Systems",
      "grade": "A"
    }
  ],
  "semester_data": {
    "Sem 1 SGPA": "9.8",
    "Sem 2 SGPA": "9.6"
  }
}
```

---

### 2. Search Result	

**Endpoint:** `GET /result/search?name=&roll=&batch=`

Search for a student's result with optional name verification.

**Parameters:**

- `name` (string, optional): Student name for verification
- `roll` (string): Student roll number
- `batch` (string): Batch year

**Example:**

```bash
curl "http://localhost:8000/result/search?name=John%20Doe&roll=2K19/EC/107&batch=2019"
```

---

## Scraping Technique

### Why Label-Based Scraping?

❌ **Fragile:** Class-based selectors

```python
soup.find("p", class_="text-3xl font-bold text-emerald-400")  # Breaks easily
```

✅ **Robust:** Label-based selectors

```python
label = soup.find("p", string=lambda x: x and "Cumulative CGPA" in x)
cgpa = label.find_next("p").text.strip()
```

### How It Works

1. **Find the label** (text-based, stable)

   ```python
   label = soup.find("p", string=lambda x: x and "Cumulative CGPA" in x)
   ```
2. **Get the next element** (containing actual value)

   ```python
   value = label.find_next("p").text.strip()
   ```
3. **Extract and validate**

   - Check if value exists
   - Strip whitespace
   - Return clean data

---

## Fallback Strategy

### When Requests Works

- ✅ Fast (1-2 seconds)
- ✅ Direct HTML parsing

### When Page is JS-Rendered

- ⚠️ Requests returns incomplete data
- ✅ Automatic fallback to Selenium
- ⚠️ Slower (5-10 seconds) but handles dynamic content

### Implementation

```python
# Try requests first
result = fetch_result_requests(url)

# If incomplete, try Selenium
if not result or "cgpa" not in result:
    result = fetch_result_selenium(url)
```

---

## Data Extraction

### CGPA

```
Label: "Cumulative CGPA"
→ find_next("p")
→ "9.946"
```

### SGPA

```
Label: "Semester SGPA"
→ find_next("p")
→ "9.5"
```

### Subject Grades

```
Find all tables
→ Parse rows
→ Extract: code, name, grade
Example: ["CO305", "Data Structures", "A+"]
```

### Semester Data

```
Look for "Semester" labels
→ Extract SGPA by semester
→ Format: {"Sem 1 SGPA": "9.8", ...}
```

---

## Error Handling

### If Student Not Found

```json
{
  "error": "Could not fetch result",
  "roll": "2K19/EC/107",
  "batch": "2019",
  "url": "https://www.resulthubdtu.com/DTU/StudentProfile/2019/2K19/EC/107"
}
```

### If Name Doesn't Match

```json
{
  "error": "Student name doesn't match",
  "provided": "Jane Doe",
  "found": "John Doe"
}
```

### If URL is Invalid

```json
{
  "error": "Failed to fetch: [reason]",
  "roll": "INVALID",
  "batch": "2019"
}
```

---

## Example Use Cases

### 1. Get Student CGPA

```python
import requests

response = requests.get(
    "http://localhost:8000/result/2K19/EC/107/2019"
)
data = response.json()
print(f"CGPA: {data.get('cgpa')}")
```

### 2. Batch Fetch Results

```python
rolls = ["2K19/EC/107", "2K19/EC/108", "2K19/EC/109"]
batch = "2019"

for roll in rolls:
    response = requests.get(
        f"http://localhost:8000/result/{roll}/{batch}"
    )
    result = response.json()
    print(f"{roll}: {result.get('cgpa')}")
```

### 3. Compare Student Performance

```python
response = requests.get(
    "http://localhost:8000/result/2K19/EC/107/2019"
)
result = response.json()

print(f"Name: {result.get('name')}")
print(f"Overall CGPA: {result.get('cgpa')}")
print(f"Current Semester SGPA: {result.get('sgpa')}")
print(f"Subjects: {len(result.get('subjects', []))}")
```

---

## Requirements

These packages are automatically installed:

- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests
- `selenium` - JS-rendered page handling
- `lxml` - HTML parsing backend

To install:

```bash
pip install -r requirements.txt
```

---

## Notes

1. **URL Format:**

   - Base: `https://www.resulthubdtu.com/DTU/StudentProfile/`
   - Batch is the YEAR (e.g., 2019 for 2K19 batch)
   - Roll is full roll number
2. **Performance:**

   - Requests only: ~1-2 seconds
   - Selenium fallback: ~5-10 seconds
   - Caching recommended for frequent requests
3. **Rate Limiting:**

   - Be respectful to the server
   - Add delays between batch requests
   - Implement caching layer
4. **Maintenance:**

   - If HTML structure changes, label-based scraping still works
   - Selenium handles dynamic content
   - Monitor for page changes

---

## Troubleshooting

| Issue                    | Solution                                        |
| ------------------------ | ----------------------------------------------- |
| "Could not fetch result" | Check roll number and batch year format         |
| Timeout error            | Server might be down, try again later           |
| Name doesn't match       | Verify student name spelling                    |
| Incomplete data          | Selenium fallback should handle it              |
| Slow response            | Selenium is likely running, normal for JS pages |

---

## Future Enhancements

- [ ] Add caching layer (Redis)
- [ ] Batch fetch with rate limiting
- [ ] Export results to PDF
- [ ] Grade analysis and trends
- [ ] Semester-wise comparison
- [ ] Websocket for real-time updates
