"""
Standalone diagnostic test script for Gemini API Integration.
Usage:
    python test_gemini.py
"""

import os
import sys
from dotenv import load_dotenv

# Ensure the root directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.gemini_service import GeminiService


def main():
    print("==================================================")
    print("  RecruitIntel AI -- Gemini Connection Diagnostic ")
    print("==================================================")

    # 1. Check .env presence
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        print("[!] .env file not found!")
        print("    Create a .env file from .env.example with your GEMINI_API_KEY.")
    else:
        print(f"[OK] .env file detected: {env_path}")

    # 2. Check API key configuration
    is_conf = GeminiService.is_configured()
    key = GeminiService.get_api_key()

    if not is_conf:
        print("[!] GEMINI_API_KEY is not configured or is using placeholder text.")
        print("\nTo configure your Gemini API Key:")
        print("  1. Get a key for free from: https://aistudio.google.com/")
        print("  2. Open .env and add:")
        print("     GEMINI_API_KEY=your_actual_api_key_here\n")
        print("[INFO] Application will operate in Local Heuristic Mode until a key is added.")
        return

    masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
    print(f"[OK] GEMINI_API_KEY loaded: {masked}")

    # 3. Test Text Validation
    valid, err = GeminiService.validate_document_text("Too short")
    assert not valid, "Short text should be flagged as invalid"
    print("[OK] Text length validation check passed.")

    # 4. Perform Live Connection Test
    print("\n[*] Sending test request to Gemini API (testing structured JSON generation)...")
    res = GeminiService.test_connection()

    if res.get("success"):
        print("[SUCCESS] Gemini API Connected Successfully!")
        print(f"[*] Model Response: {res.get('model_response')}")
        print("\n[OK] All agents are now ready to perform LLM-powered recruitment intelligence.")
    else:
        print(f"[ERROR] Connection failed: {res.get('message')}")
        print(f"[*] Hint: {res.get('hint')}")


if __name__ == "__main__":
    main()
