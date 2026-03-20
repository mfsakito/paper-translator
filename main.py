import argparse
import os
import sys

import fitz
from pdf2docx import Converter

from modules.extractor import extract_docx_blocks
from modules.translator import translate_blocks
from modules.builder import build_docx

def main():
    fitz.TOOLS.mupdf_display_errors(False)
    
    parser = argparse.ArgumentParser(description="PDF Translator using Word conversion for Layout")
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
    os.makedirs("temp", exist_ok=True)

    base_name = os.path.basename(input_pdf)
    name, ext = os.path.splitext(base_name)
    
    temp_docx = os.path.join("temp", f"{name}_temp.docx")
    output_docx = os.path.join("output", f"{name}_translated.docx")
    
    print("\n=== Pipeline Run ===")
    
    print(f"1. Converting PDF to Word format... ({input_pdf} -> {temp_docx})")
    cv = Converter(input_pdf)
    cv.convert(temp_docx, start=0, end=limit)
    cv.close()
    
    print("\n2. Extracting Word blocks...")
    extract_docx_blocks(temp_docx, state_file)
    
    print("\n3. Translating blocks...")
    translate_blocks(state_file)
    
    print("\n4. Building final Word document...")
    success = build_docx(temp_docx, state_file, output_docx)
    if not success:
        print("Failed to build Word document. Exiting...")
        sys.exit(1)
        
    print(f"\nPipeline finished. Check output at {output_docx}")

if __name__ == "__main__":
    main()
