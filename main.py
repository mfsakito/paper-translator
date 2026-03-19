import argparse
import os
import sys

from modules.extractor import extract_pdf_blocks
from modules.translator import translate_blocks
from modules.builder import build_pdf
from modules.evaluator import evaluate_translation


def suppress_mupdf_output():
    """Redirect both stdout and stderr fd to /dev/null to silence MuPDF C-level warnings."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved_stdout = os.dup(1)
    saved_stderr = os.dup(2)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)
    return saved_stdout, saved_stderr


def restore_output(saved):
    """Restore stdout and stderr after MuPDF operations."""
    saved_stdout, saved_stderr = saved
    os.dup2(saved_stdout, 1)
    os.dup2(saved_stderr, 2)
    os.close(saved_stdout)
    os.close(saved_stderr)


def main():
    parser = argparse.ArgumentParser(description="PDF Translator V2 with Auto-Evaluation")
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
    name, ext = os.path.splitext(base_name)
    output_pdf = os.path.join("output", f"{name}_translated{ext}")

    print("\n=== Pipeline Run ===")
    
    # 1. Extract (suppress MuPDF noise)
    saved = suppress_mupdf_output()
    extract_pdf_blocks(input_pdf, state_file, limit)
    restore_output(saved)
    
    # 2. Translate
    translate_blocks(state_file)
    
    # 3. Build (suppress MuPDF noise)
    saved = suppress_mupdf_output()
    success = build_pdf(input_pdf, state_file, output_pdf)
    restore_output(saved)
    if not success:
        print("Failed to build PDF. Exiting...")
        sys.exit(1)
        
    # 4. Evaluate (suppress MuPDF noise)
    saved = suppress_mupdf_output()
    accuracy, failed_blocks = evaluate_translation(output_pdf, state_file)
    restore_output(saved)
    
    if accuracy >= 80.0:
        print(f"\nTarget accuracy achieved ({accuracy:.1f}%). Translation completed!")
    else:
        print(f"\nAccuracy ({accuracy:.1f}%) is below 80%. Pipeline finished.")


if __name__ == "__main__":
    main()
