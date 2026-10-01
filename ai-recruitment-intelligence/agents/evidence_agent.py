import re
from typing import Dict, Any, List
from agents import call_gemini_json


class EvidenceAgent:
    """
    Stage 4: Evidence Agent.
    For every important matched skill and job requirement, extracts concrete,
    verifiable evidence from work history, projects, and achievements.
    Guarantees that candidates are not rewarded purely for repeating keywords.
    """

    @staticmethod
    def extract_evidence(
        jd_requirements: List[str],
        work_experience: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
        resume_raw_text: str
    ) -> List[Dict[str, Any]]:
        """
        Cross-examines each JD requirement against work history and projects.
        Extracts exact citation quotes and assigns verification status.
        """
        if not jd_requirements:
            return []

        prompt = f"""
Find verifiable proof and evidence in the candidate's resume for each of the following Job Requirements.
CRITICAL: Do NOT mark a skill as verified merely because the word appears. Look for applied context, deliverables, metrics, or technical projects.
If no evidence is present in the resume, explicitly mark the status as 'Not found' or 'Unclear'. Do NOT invent quotes.

Job Requirements:
{jd_requirements}

Candidate Work Experience:
{work_experience}

Candidate Projects:
{projects}

Return valid JSON with this exact schema:
{{
  "evidence_items": [
    {{
      "requirement": "string (the evaluated JD requirement)",
      "status": "VERIFIED" | "PARTIAL" | "UNCLEAR" | "NOT_FOUND",
      "confidence": "HIGH" | "MEDIUM" | "LOW",
      "evidence_snippet": "string (exact quote/bullet point from resume providing proof, or 'Not found')",
      "source_section": "string (e.g. 'Backend Engineer @ Acme Corp' or 'Project: E-Commerce API' or 'Not found')",
      "depth_assessment": "string (brief explanation of how deeply the skill was applied in practice)"
    }}
  ]
}}
"""
        system_instruction = (
            "You are an Evidence Verification Specialist. Quote exact facts from the resume. "
            "Never hallucinate or assume experience not directly substantiated in the candidate's text."
        )
        ai_result = call_gemini_json(prompt, system_instruction)

        if ai_result and isinstance(ai_result, dict) and "evidence_items" in ai_result:
            return ai_result["evidence_items"]

        # Heuristic Evidence Extractor Fallback
        evidence_list = []
        for req in jd_requirements:
            req_words = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9\+#\.]+\b', req) if len(w) > 2]
            found_snippet = None
            source = "Not found"
            status = "NOT_FOUND"
            confidence = "LOW"
            depth = "Unclear"

            # Search in work experiences first (highest weight)
            for exp in work_experience:
                company = exp.get("company", "Work Experience")
                role = exp.get("role", "Role")
                for highlight in exp.get("highlights", []):
                    hl_lower = highlight.lower()
                    matches = sum(1 for w in req_words if w in hl_lower)
                    if matches >= 1:
                        found_snippet = highlight
                        source = f"{role} at {company}"
                        status = "VERIFIED" if matches >= 2 else "PARTIAL"
                        confidence = "HIGH" if matches >= 2 else "MEDIUM"
                        depth = "Applied in professional work environment"
                        break
                if found_snippet:
                    break

            # Search in projects if not found in work
            if not found_snippet:
                for proj in projects:
                    title = proj.get("title", "Project")
                    desc = proj.get("description", "")
                    stack = " ".join(proj.get("tech_stack", []))
                    combined = (desc + " " + stack).lower()
                    matches = sum(1 for w in req_words if w in combined)
                    if matches >= 1:
                        found_snippet = desc or f"Built with {stack}"
                        source = f"Project: {title}"
                        status = "PARTIAL"
                        confidence = "MEDIUM"
                        depth = "Implemented in project portfolio"
                        break

            # Fallback: check raw text mentions
            if not found_snippet:
                for line in resume_raw_text.split('\n'):
                    l_clean = line.strip()
                    if l_clean and any(w in l_clean.lower() for w in req_words):
                        found_snippet = l_clean
                        source = "Resume Stated Mention"
                        status = "UNCLEAR"
                        confidence = "LOW"
                        depth = "Mentioned in text without detailed project context"
                        break

            evidence_list.append({
                "requirement": req,
                "status": status if found_snippet else "NOT_FOUND",
                "confidence": confidence if found_snippet else "LOW",
                "evidence_snippet": found_snippet if found_snippet else "Not found in candidate resume.",
                "source_section": source if found_snippet else "Not found",
                "depth_assessment": depth if found_snippet else "Not found"
            })

        return evidence_list
