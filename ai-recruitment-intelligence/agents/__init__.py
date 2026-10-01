"""
Agents package for AI Recruitment Intelligence.
Consists of specialized modular agents:
- JDAgent: Extracts and analyzes job description requirements
- ResumeAgent: Parses candidate resumes into structured profile
- SkillAgent: Normalizes skills and maps synonyms
- NoiseAgent: Detects keyword stuffing and false positives
- EvidenceAgent: Validates requirements against concrete resume proof
- MatchingAgent: Computes multi-dimensional explainable score
- ShortlistAgent: Generates executive shortlist summaries and targeted interview questions
"""

import logging
from typing import Dict, Any, Optional
from utils.gemini_service import GeminiService

logger = logging.getLogger("Agents")


def get_gemini_client():
    """Wrapper to get underlying client from GeminiService."""
    client, client_type, _ = GeminiService.get_client()
    return client, client_type


def call_gemini_json(prompt: str, system_instruction: str = "") -> Optional[Dict[str, Any]]:
    """
    Standardized helper used across all agents to request structured JSON from Gemini.
    Returns parsed JSON dict or None if API key is not present or call fails.
    """
    if not GeminiService.is_configured():
        return None

    data, err = GeminiService.generate_json(prompt=prompt, system_instruction=system_instruction)
    if err:
        logger.warning(f"[Agent Gemini Warning] {err}")
        return None
    return data
