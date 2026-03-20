import argparse
import os
import sys

from modules.extractor import extract_markdown_blocks
from modules.translator import translate_blocks
from modules.builder import build_docx_from_markdown

def main():
    parser = argparse.ArgumentParser(description="PDF Translator using pymupdf4llm + python-docx")
    parser.add_argument("pdf", help="Path to input PDF")
    parser.add_argument("--limit", type=int, help="Limit number of pages")
    parser.add_argument("--state", default="temp/state.json", help="Path to state file")

    args = parser.parse_args()

    input_pdf = args.pdf
    state_file = args.state
    limit = args.limit

    if not os.path.exists(input_pdf):
        print(f"Error: {input_pdf} not found.")
        sys.exit(1)

    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    os.makedirs("output", exist_ok=True)

    base_name = os.path.basename(input_pdf)
    name, _ = os.path.splitext(base_name)
    output_docx = os.path.join("output", f"{name}_translated.docx")
    
    print("\n=== Pipeline Run ===")
    
    print(f"\n1. Extracting Markdown from PDF... ({input_pdf})")
    extract_markdown_blocks(input_pdf, state_file, limit=limit)
    
    print("\n2. Translating sections...")
    translate_blocks(state_file)
    
    print("\n3. Building final Word document...")
    success = build_docx_from_markdown(state_file, output_docx)
    if not success:
        print("Failed to build Word document. Exiting...")
        sys.exit(1)
        
    print(f"\nPipeline finished. Check output at {output_docx}")

if __name__ == "__main__":
    main()
