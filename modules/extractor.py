import json
import os
import re
import pymupdf4llm


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state, state_file):
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def extract_markdown_blocks(pdf_path, state_file, limit=None):
    """
    Extracts text from the PDF as Markdown using pymupdf4llm,
    then splits it into section-level blocks for translation.
    """
    pages = list(range(limit)) if limit else None
    
    # Extract with formula/figure images saved as PNG
    temp_dir = os.path.dirname(state_file)
    image_dir = os.path.join(temp_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    
    md_text = pymupdf4llm.to_markdown(
        pdf_path,
        pages=pages,
        write_images=True,
        image_path=image_dir,
    )
    
    # Save full markdown for debugging
    md_path = os.path.join(temp_dir, "extracted.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"[Extractor] Saved raw Markdown to {md_path}")
    
    # Split into sections by headings (## or #)
    blocks = split_markdown_into_sections(md_text)
    
    state = load_state(state_file)
    
    # Clear old entries from previous extraction schemes
    old_keys = [k for k in state if not k.startswith("section_")]
    for k in old_keys:
        del state[k]
    
    current_ids = set()
    for i, block in enumerate(blocks):
        text = block.strip()
        if len(text) < 2:
            continue
        
        block_id = f"section_{i}"
        current_ids.add(block_id)
        
        if block_id not in state:
            state[block_id] = {
                "id": block_id,
                "original_text": text,
                "translated_text": "",
                "status": "pending",
                "retry_count": 0
            }
        else:
            # Keep existing translation if text hasn't changed
            if state[block_id]["original_text"] != text:
                state[block_id]["original_text"] = text
                state[block_id]["status"] = "pending"
                state[block_id]["translated_text"] = ""
    
    # Remove blocks that no longer exist
    stale_keys = [k for k in state if k.startswith("section_") and k not in current_ids]
    for k in stale_keys:
        del state[k]
    
    save_state(state, state_file)
    print(f"[Extractor] Extracted {len(current_ids)} sections from {pdf_path}")
    return state


def split_markdown_into_sections(md_text):
    """
    Splits Markdown text into sections by headings.
    Each section includes its heading line and all following text until
    the next heading of equal or higher level.
    """
    lines = md_text.split("\n")
    sections = []
    current_section = []
    
    for line in lines:
        # Detect heading lines (# or ## etc.)
        if re.match(r'^#{1,3}\s', line) and current_section:
            # Flush current section
            section_text = "\n".join(current_section).strip()
            if section_text:
                sections.append(section_text)
            current_section = [line]
        else:
            current_section.append(line)
    
    # Don't forget the last section
    if current_section:
        section_text = "\n".join(current_section).strip()
        if section_text:
            sections.append(section_text)
    
    return sections
