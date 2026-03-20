import fitz
import os
import docx
from .extractor import load_state


def build_pdf(input_path, state_file, output_path):
    """
    Creates a new PDF with translated text overlaid on the original document.
    Redacts all target blocks first, then draws translated text, to avoid
    apply_redactions() destroying previously inserted text.
    """
    if not os.path.exists(input_path):
        print(f"[Builder] Error: Input file '{input_path}' not found.")
        return False

    state = load_state(state_file)
    doc = fitz.open(input_path)

    # Group translated blocks by page
    blocks_by_page = {}
    for bid, data in state.items():
        if data["status"] == "translated":
            # [翻訳済]タグがついた変換前テキストは除外する
            if "[翻訳済]" in data["translated_text"]:
                continue
            p = data["page"]
            blocks_by_page.setdefault(p, [])
            blocks_by_page[p].append(data)

    total = sum(len(v) for v in blocks_by_page.values())
    print(f"[Builder] Found {total} translated blocks to render.")

    for page_num in range(len(doc)):
        if page_num not in blocks_by_page:
            continue

        page = doc[page_num]
        page_blocks = blocks_by_page[page_num]

        # --- Phase 1: Redact all original text areas at once ---
        for data in page_blocks:
            bbox = fitz.Rect(data["bbox"])
            page.add_redact_annot(bbox, fill=(1, 1, 1))
        page.apply_redactions()  # single call removes all originals

        # --- Phase 2: Register CJK font ---
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        local_font_path = os.path.join(project_root, "NotoSansJP-Regular.ttf")
        system_font_path = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
        
        try:
            if os.path.exists(local_font_path):
                page.insert_font(fontname="jpfont", fontfile=local_font_path)
            elif os.path.exists(system_font_path):
                page.insert_font(fontname="jpfont", fontfile=system_font_path)
            else:
                cjk_font = fitz.Font("cjk")
                page.insert_font(fontname="jpfont", fontbuffer=cjk_font.buffer)
        except Exception as e:
            print(f"Warning: Failed to register font: {e}")

        # --- Phase 3: Draw translated text ---
        for data in page_blocks:
            bbox = fitz.Rect(data["bbox"])
            translated_text = data["translated_text"]

            # Inject zero-width spaces so PyMuPDF can line-break CJK text
            spaced = "\u200B".join(translated_text)

            try:
                res = page.insert_textbox(
                    bbox, spaced, fontname="jpfont", align=0, fontsize=9
                )
                if res < 0:
                    # Overflow: retry with a smaller font
                    page.insert_textbox(
                        bbox, spaced, fontname="jpfont", align=0, fontsize=6
                    )
            except Exception as e:
                print(f"Warning: Failed to render block {data['id']}: {e}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)
    doc.close()
    print(f"[Builder] Successfully built translated PDF at {output_path}")
    return True

def build_docx(input_docx_path, state_file, output_docx_path):
    """
    Creates a new docx with translated text overlaid on the original document.
    """
    if not os.path.exists(input_docx_path):
        print(f"[Builder] Error: Input file '{input_docx_path}' not found.")
        return False

    state = load_state(state_file)
    doc = docx.Document(input_docx_path)

    def process_paragraphs(paragraphs, prefix):
        for i, p in enumerate(paragraphs):
            block_id = f"{prefix}_p{i}"
            if block_id in state and state[block_id]["status"] == "translated":
                # [翻訳済]タグがついた変換前テキストはレイアウト崩れの原因になるため除外（置換をスキップ）する
                if "[翻訳済]" in state[block_id]["translated_text"]:
                    continue
                p.text = state[block_id]["translated_text"]

    process_paragraphs(doc.paragraphs, "body")
    
    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                prefix = f"t{t_idx}_r{r_idx}_c{c_idx}"
                process_paragraphs(cell.paragraphs, prefix)

    os.makedirs(os.path.dirname(output_docx_path) or ".", exist_ok=True)
    doc.save(output_docx_path)
    print(f"[Builder] Successfully built translated Word document at {output_docx_path}")
    return True
