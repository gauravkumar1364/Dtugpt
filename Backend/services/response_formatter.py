"""
Service to structure and format LLM responses into clean, organized output
"""
import json
import re
from typing import Optional


def clean_markdown(text: str) -> str:
    """Remove markdown formatting characters from text"""
    if not text:
        return text
    # Remove bold ** 
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Remove italic *
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Remove underscores for italic/bold
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    return text.strip()


def parse_llm_response(response_text: str) -> dict:
    """
    Parse raw LLM response and structure it into organized sections
    
    Returns a dictionary with:
    - title: Main heading (if present)
    - summary: Brief overview
    - sections: List of organized sections with headers and content
    - bullet_points: Key points as list
    - formatted_text: Clean markdown output
    """
    
    lines = response_text.strip().split('\n')
    sections = []
    current_section = None
    bullet_points = []
    summary_text = ""
    title = ""
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Detect headers (### or ## or #)
        header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if header_match:
            # Save previous section
            if current_section:
                sections.append(current_section)
            
            level = len(header_match.group(1))
            header_text = header_match.group(2).strip('*').strip()
            
            # First header is the title
            if not title and level == 1:
                title = header_text
            else:
                current_section = {
                    "header": header_text,
                    "level": level,
                    "content": [],
                    "bullets": []
                }
            i += 1
            continue
        
        # Detect bullet points
        bullet_match = re.match(r'^[-*•]\s+(.+)$', line)
        if bullet_match:
            bullet_text = clean_markdown(bullet_match.group(1).strip())
            if current_section is not None:
                current_section["bullets"].append(bullet_text)
            else:
                bullet_points.append(bullet_text)
            i += 1
            continue
        
        # Regular text lines
        if current_section is not None:
            current_section["content"].append(clean_markdown(line))
        elif not summary_text and not title:
            summary_text = clean_markdown(line)
        
        i += 1
    
    # Save last section
    if current_section:
        sections.append(current_section)
    
    # Clean up section content
    for section in sections:
        section["content"] = clean_markdown(' '.join(section["content"]).strip())
    
    # Build structured response
    structured = {
        "title": title,
        "summary": clean_markdown(summary_text),
        "sections": sections,
        "key_points": bullet_points,
        "formatted_text": response_text  # Original text for fallback
    }
    
    return structured


def format_structured_response(structured_data: dict) -> str:
    """Convert structured response back to clean markdown format"""
    
    output = []
    
    # Add title
    if structured_data.get("title"):
        output.append(f"# {structured_data['title']}\n")
    
    # Add summary
    if structured_data.get("summary"):
        output.append(f"{structured_data['summary']}\n")
    
    # Add sections
    for section in structured_data.get("sections", []):
        header_level = section.get("level", 2)
        header_text = section.get("header", "")
        output.append(f"{'#' * header_level} {header_text}")
        
        if section.get("content"):
            output.append(section["content"])
        
        if section.get("bullets"):
            for bullet in section["bullets"]:
                output.append(f"- {bullet}")
        
        output.append("")  # Empty line between sections
    
    # Add key points if no sections found
    if not structured_data.get("sections") and structured_data.get("key_points"):
        output.append("## Key Points\n")
        for point in structured_data["key_points"]:
            output.append(f"- {point}")
    
    return "\n".join(output)


def get_json_response(structured_data: dict) -> dict:
    """Return structured response as JSON for API"""
    return {
        "title": structured_data.get("title"),
        "summary": structured_data.get("summary"),
        "sections": structured_data.get("sections", []),
        "key_points": structured_data.get("key_points", []),
        "formatted_markdown": format_structured_response(structured_data)
    }


def structure_llm_output(raw_response: str, return_format: str = "json") -> dict:
    """
    Main function to take raw LLM response and return structured output
    
    Args:
        raw_response: Raw text from LLM
        return_format: "json" or "markdown"
    
    Returns:
        Structured response dictionary
    """
    structured = parse_llm_response(raw_response)
    
    if return_format == "json":
        return get_json_response(structured)
    else:
        return {
            "formatted_text": format_structured_response(structured)
        }
