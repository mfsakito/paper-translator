import os
import sys
import time
from dotenv import load_dotenv
from .extractor import load_state, save_state

load_dotenv()

PROMPT_TEMPLATE = """あなたは学術論文の専門翻訳アシスタントです。以下の英語テキスト（Markdown形式）を自然な日本語に翻訳してください。

【重要なルール】
- Markdownの書式（見出しの##、**太字**、表の|記法など）はそのまま保持してください。
- 数式記号、変数名（例：$x$, \\alpha）、および独立した数式ブロックは一切翻訳や変更をせずに元の記法を保持してください。
- URLやメールアドレスはそのまま保持してください。
- 翻訳されたテキストのみを出力してください。余計な説明は不要です。

対象テキスト:
"""


def _resolve_provider():
    """Determine which LLM provider to use based on available API keys.

    Priority: Gemini (if key exists) > OpenAI (if key exists).
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        return "gemini", gemini_key
    if openai_key:
        return "openai", openai_key

    print("Error: Neither GEMINI_API_KEY nor OPENAI_API_KEY is set in .env")
    sys.exit(1)


def _build_client(provider, api_key):
    if provider == "gemini":
        from google import genai
        return genai.Client(api_key=api_key)

    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _call_llm(client, provider, text):
    if provider == "gemini":
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=PROMPT_TEMPLATE + text,
        )
        return response.text.strip()

    response = client.chat.completions.create(
        model="gpt-5.4-nano-2026-03-17",
        messages=[
            {"role": "system", "content": PROMPT_TEMPLATE.strip()},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content.strip()


def translate_blocks(state_file):
    """
    Iterates through the state file and translates any blocks marked 'pending' or 'error'.
    """
    state = load_state(state_file)
    provider, api_key = _resolve_provider()
    client = _build_client(provider, api_key)
    print(f"[Translator] Using provider: {provider}")

    blocks_to_translate = [
        bid for bid, data in state.items() if data["status"] in ["pending", "error"]
    ]
    print(f"[Translator] Found {len(blocks_to_translate)} blocks to translate.")

    for bid in blocks_to_translate:
        block_data = state[bid]
        original = block_data["original_text"]

        print(f"Translating block {bid} ({len(original)} chars)...")
        try:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    translated = _call_llm(client, provider, original)

                    if translated:
                        block_data["translated_text"] = translated
                        block_data["status"] = "translated"
                    else:
                        block_data["status"] = "error"
                        print(f"Warning: Empty translation returned for {bid}")
                    break

                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        wait_time = 2**attempt
                        print(f"Rate limit hit on {bid}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise

        except Exception as e:
            print(f"Translation error on {bid}: {e}")
            block_data["status"] = "error"
            block_data["retry_count"] += 1

        save_state(state, state_file)
        time.sleep(1)

    print("[Translator] Translation pass complete.")
    return state
