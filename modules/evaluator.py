import fitz
import re
import difflib
from .extractor import load_state


def normalize_text(text):
    """Normalize string by removing whitespace, zero-width spaces, and null bytes."""
    return re.sub(r'[\s\u200B\x00]+', '', text)


def evaluate_translation(output_pdf_path, state_file):
    """
    Evaluates whether the translated text was successfully rendered into the PDF.
    Returns a tuple of (accuracy_percentage, list_of_failed_block_ids).
    """
    state = load_state(state_file)
    try:
        doc = fitz.open(output_pdf_path)
    except Exception as e:
        print(f"[Evaluator] Could not open output PDF: {e}")
        return 0.0, []

    target_blocks = [d for d in state.values() if d["status"] == "translated"]
    if not target_blocks:
        print("[Evaluator] No translated blocks found to evaluate.")
        return 0.0, []

    blocks_by_page = {}
    for d in target_blocks:
        p = d["page"]
        blocks_by_page.setdefault(p, []).append(d)

    success_count = 0
    total_count = len(target_blocks)
    failed_blocks = []

    print(f"[Evaluator] Starting evaluation of {total_count} blocks...")

    for page_num, blocks in blocks_by_page.items():
        if page_num >= len(doc):
            continue

        page = doc[page_num]
        page_text = page.get_text("text")
        norm_page_text = normalize_text(page_text)

        for block in blocks:
            norm_target = normalize_text(block["translated_text"])

            if not norm_target:
                success_count += 1
                continue

            # Primary check: substring match
            if norm_target in norm_page_text:
                success_count += 1
            else:
                # Fallback: check if the text in the bounding box matches
                rect = fitz.Rect(block["bbox"])
                extracted_text = normalize_text(page.get_text("text", clip=rect))
                
                matcher = difflib.SequenceMatcher(None, norm_target, extracted_text)
                match_ratio = matcher.ratio()

                if match_ratio >= 0.8:
                    success_count += 1
                else:
                    print(
                        f"  [Failed] Block {block['id']} "
                        f"(Match: {match_ratio:.1%}). Text truncated or missing."
                    )
                    failed_blocks.append(block["id"])

    accuracy = (success_count / total_count) * 100 if total_count > 0 else 0
    print(
        f"[Evaluator] Evaluation finished. "
        f"Accuracy: {accuracy:.1f}% ({success_count}/{total_count})"
    )
    return accuracy, failed_blocks
