import os
import sys
import time
from dotenv import load_dotenv
from google import genai
from .extractor import load_state, save_state

load_dotenv()

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set in .env")
        sys.exit(1)
    return genai.Client(api_key=api_key)

def translate_blocks(state_file):
    """
    Iterates through the state file and translates any blocks marked 'pending' or 'error'.
    """
    state = load_state(state_file)
    client = get_gemini_client()
    
    prompt_template = """あなたは学術論文の専門翻訳アシスタントです。以下の英語テキストを自然な日本語に翻訳してください。
【重要】文中の数式記号、変数名（例：$x$, \\alpha）、および独立した数式ブロックは、一切翻訳や変更をせずに元の記法を完全に保持してください。
翻訳されたテキストのみを出力してください。

対象テキスト:
"""

    blocks_to_translate = [bid for bid, data in state.items() if data["status"] in ["pending", "error"]]
    print(f"[Translator] Found {len(blocks_to_translate)} blocks to translate.")

    for bid in blocks_to_translate:
        block_data = state[bid]
        original = block_data["original_text"]
        
        print(f"Translating block {bid} ({len(original)} chars)...")
        try:
            # Exponential backoff loop
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt_template + original,
                    )
                    translated = response.text.strip()
                    
                    if translated:
                        block_data["translated_text"] = translated
                        block_data["status"] = "translated"
                    else:
                        block_data["status"] = "error"
                        print(f"Warning: Empty translation returned for {bid}")
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit on {bid}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise e  # Re-raise if not 429 or max retries reached

        except Exception as e:
            print(f"Translation error on {bid}: {e}")
            block_data["status"] = "error"
            block_data["retry_count"] += 1

        # Save state incrementally to avoid data loss on crash
        save_state(state, state_file)
        time.sleep(1) # Basic rate limit handling

    print("[Translator] Translation pass complete.")
    return state
