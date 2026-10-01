import unittest
from utils.gemini_service import GeminiService


class TestGeminiService(unittest.TestCase):

    def test_validate_document_text_empty(self):
        valid, err = GeminiService.validate_document_text("", "Job Description")
        self.assertFalse(valid)
        self.assertIn("empty or unreadable", err)

    def test_validate_document_text_too_short(self):
        valid, err = GeminiService.validate_document_text("Only 15 chars", "Resume")
        self.assertFalse(valid)
        self.assertIn("insufficient text", err)

    def test_validate_document_text_valid(self):
        valid, err = GeminiService.validate_document_text(
            "This is a comprehensive software engineer resume with more than forty characters of content.",
            "Resume"
        )
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_clean_json_response_fenced(self):
        raw = "```json\n{\"status\": \"ok\", \"skills\": [\"Python\", \"Flask\"]}\n```"
        cleaned = GeminiService.clean_json_response(raw)
        self.assertEqual(cleaned, '{"status": "ok", "skills": ["Python", "Flask"]}')

    def test_clean_json_response_with_commentary(self):
        raw = "Here is the parsed JSON result:\n\n```json\n{\"name\": \"John Doe\"}\n```\nHope this helps!"
        cleaned = GeminiService.clean_json_response(raw)
        self.assertEqual(cleaned, '{"name": "John Doe"}')

    def test_connection_without_key(self):
        # When key is empty
        res = GeminiService.test_connection()
        # If no key set, returns status missing_api_key
        if not GeminiService.get_api_key():
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], "missing_api_key")


if __name__ == "__main__":
    unittest.main()
