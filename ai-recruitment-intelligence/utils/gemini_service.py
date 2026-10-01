import os
import json
import re
import logging
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("GeminiService")
logging.basicConfig(level=logging.INFO)


class GeminiService:
    """
    Dedicated, resilient service for Google Gemini API integration.
    Handles authentication, structured JSON generation, text validation,
    and multi-model fallback diagnostics.
    """

    MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
    MIN_DOC_CHARS = 40

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Retrieve and sanitize GEMINI_API_KEY from environment."""
        load_dotenv(override=True)
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key or key in ["your_gemini_api_key_here", "your_actual_gemini_api_key_here", ""]:
            return None
        return key

    @classmethod
    def is_configured(cls) -> bool:
        """Check if a valid API key string is present."""
        return cls.get_api_key() is not None

    @classmethod
    def get_client(cls) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
        """
        Initialize Gemini SDK client.
        Supports both modern `google.genai` and `google.generativeai`.
        Returns: (client_instance, client_type, error_message)
        """
        api_key = cls.get_api_key()
        if not api_key:
            return None, None, "GEMINI_API_KEY is not configured in .env file."

        # 1. Try modern google-genai
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            return client, "genai", None
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed initializing google-genai client: {e}")

        # 2. Try google-generativeai fallback
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel("gemini-1.5-flash")
            return model, "generativeai", None
        except ImportError:
            return None, None, "Neither 'google-genai' nor 'google-generativeai' packages are installed."
        except Exception as e:
            return None, None, f"Error configuring Gemini SDK: {str(e)}"

    @classmethod
    def validate_document_text(cls, text: str, doc_name: str = "document") -> Tuple[bool, Optional[str]]:
        """
        Check whether document text contains sufficient content for meaningful AI extraction.
        Prevents wasting API tokens on empty or scanned image-only PDFs.
        """
        if not text or not text.strip():
            return False, f"Uploaded {doc_name} is empty or unreadable (e.g. scanned image PDF without OCR)."

        cleaned = re.sub(r'\s+', ' ', text.strip())
        if len(cleaned) < cls.MIN_DOC_CHARS:
            return False, f"Uploaded {doc_name} contains insufficient text ({len(cleaned)} characters). Minimum {cls.MIN_DOC_CHARS} characters required."

        return True, None

    @classmethod
    def clean_json_response(cls, raw_text: str) -> str:
        """
        Extract clean JSON string from LLM responses, stripping code fences and extra commentary.
        """
        if not raw_text:
            return ""

        text = raw_text.strip()

        # Remove markdown code blocks if wrapped
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Extract outermost JSON object or array
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if json_match:
            text = json_match.group(0).strip()

        return text

    @classmethod
    def generate_json(
        cls,
        prompt: str,
        system_instruction: str = "You are an expert AI talent intelligence agent. Respond strictly with valid JSON.",
        model_name: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Generate structured JSON output from Gemini with error handling and fallback recovery.
        Returns: (parsed_json_dict, error_message)
        """
        client, client_type, err = cls.get_client()
        if err:
            return None, err

        models_list = [model_name] if model_name else [os.getenv("GEMINI_MODEL", "gemini-2.0-flash")] + cls.MODELS_TO_TRY
        last_err = None

        for model in models_list:
            if not model:
                continue
            try:
                raw_text = ""
                if client_type == "genai":
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config={
                            "response_mime_type": "application/json",
                            "system_instruction": system_instruction,
                        }
                    )
                    raw_text = response.text or ""
                else:
                    full_prompt = f"{system_instruction}\n\nStrictly return valid JSON.\n\n{prompt}"
                    response = client.generate_content(full_prompt)
                    raw_text = response.text or ""

                cleaned_json_str = cls.clean_json_response(raw_text)
                if not cleaned_json_str:
                    continue

                try:
                    parsed = json.loads(cleaned_json_str)
                    return parsed, None
                except json.JSONDecodeError as jde:
                    last_err = f"Failed to parse Gemini output as JSON: {str(jde)}"
                    continue

            except Exception as e:
                error_msg = str(e)
                last_err = error_msg
                if "API_KEY_INVALID" in error_msg or ("400" in error_msg and "API key" in error_msg):
                    return None, "Invalid Gemini API key. Please verify your GEMINI_API_KEY in .env."
                elif "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                    return None, "Gemini API rate limit or quota exceeded. Please wait a moment."
                # Fallback to next model in list
                continue

        return None, f"Gemini request failed: {last_err}"

    @classmethod
    def generate_text(
        cls,
        prompt: str,
        system_instruction: str = "You are a helpful AI assistant."
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate plain text response from Gemini.
        Returns: (response_text, error_message)
        """
        client, client_type, err = cls.get_client()
        if err:
            return None, err

        try:
            if client_type == "genai":
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                return response.text, None
            else:
                response = client.generate_content(f"{system_instruction}\n\n{prompt}")
                return response.text, None
        except Exception as e:
            return None, f"Gemini API text request failed: {str(e)}"

    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """
        Perform a live minimal test of the Gemini API connection.
        Returns detailed status diagnostics for debugging.
        """
        api_key = cls.get_api_key()
        if not api_key:
            return {
                "success": False,
                "status": "missing_api_key",
                "message": "GEMINI_API_KEY is not set in .env file.",
                "hint": "Add 'GEMINI_API_KEY=your_key_here' to the .env file in the project root."
            }

        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"

        test_prompt = "Respond with a JSON object: {\"status\": \"ok\", \"agent\": \"RecruitIntel AI\", \"message\": \"Gemini connection active!\"}"
        data, err = cls.generate_json(
            prompt=test_prompt,
            system_instruction="You are a system health checker. Respond with valid JSON."
        )

        if err:
            return {
                "success": False,
                "status": "connection_failed",
                "masked_key": masked_key,
                "message": err,
                "hint": "Check if your API key is valid at https://aistudio.google.com/ and has remaining quota."
            }

        return {
            "success": True,
            "status": "connected",
            "masked_key": masked_key,
            "model_response": data,
            "message": "Gemini API successfully connected and returned valid structured JSON!"
        }
