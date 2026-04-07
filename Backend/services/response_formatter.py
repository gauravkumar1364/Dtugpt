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
    Optimized for structured format: ## Concept, ## Key Points, ## Exam Focus
    
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
                    "level": 2,  # Normalize all sections to level 2
                    "content": [],
                    "bullets": []
                }
            i += 1
            continue
        
        # Detect bullet points (-, *, •, or numbers like 1., 2.)
        bullet_match = re.match(r'^([-*•]|\d+\.)\s+(.+)$', line)
        if bullet_match:
            bullet_text = clean_markdown(bullet_match.group(2).strip())
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
    """Convert structured response back to clean, revision-friendly markdown format"""
    
    output = []
    
    # Add title with visual separator
    if structured_data.get("title"):
        output.append(f"# {structured_data['title']}")
        output.append("---")
    
    # Add summary with visual prominence
    if structured_data.get("summary"):
        output.append(f"\n{structured_data['summary']}\n")
    
    # Add sections with improved formatting
    sections = structured_data.get("sections", [])
    
    for idx, section in enumerate(sections):
        # Add section header with number for better organization
        header_text = section.get("header", "")
        
        # Use consistent ## for main sections (remove level complexity)
        output.append(f"\n## {header_text}")
        output.append("-" * (len(header_text) + 3))  # Visual underline
        
        # Add section content if present
        if section.get("content"):
            content = section["content"].strip()
            if content:
                output.append(f"\n{content}\n")
        
        # Add bullets with better spacing
        bullets = section.get("bullets", [])
        if bullets:
            for bullet in bullets:
                output.append(f"• {bullet}")
                
        # Add spacing between major sections (except last)
        if idx < len(sections) - 1:
            output.append("")
    
    # Add key points as a summary section if present
    key_points = structured_data.get("key_points", [])
    if key_points and not sections:
        output.append("\n## Key Points")
        output.append("-" * 13)
        for point in key_points:
            output.append(f"• {point}")
    elif key_points and sections:
        # Add as recap section if sections exist
        output.append("\n## Quick Recap")
        output.append("-" * 14)
        for point in key_points:
            output.append(f"• {point}")
    
    # Add revision reminder at bottom
    output.append("\n---")
    output.append("✓ Ready for revision")
    
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
