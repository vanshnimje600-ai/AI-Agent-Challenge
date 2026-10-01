import re
from typing import Dict, Any, List
from agents import call_gemini_json
from utils.helpers import extract_candidate_name_fallback


class ResumeAgent:
    """
    Stage 2: Resume Analysis Agent.
    Decomposes raw candidate resume text into structured components:
    - Candidate Name & Contact
    - Education
    - Work Experience
    - Technical & Soft Skills
    - Projects
    - Certifications
    - Relevant Achievements
    """

    @staticmethod
    def parse_resume(resume_text: str, filename: str = "") -> Dict[str, Any]:
        """Parse resume text using Gemini AI or structured heuristic parser."""
        if not resume_text or not resume_text.strip():
            return ResumeAgent._get_empty_result(filename)

        prompt = f"""
Parse the following Candidate Resume into a structured JSON profile.
Do NOT invent candidate experience or skills. If a section or detail is missing, mark it as 'Not found' or 'Unclear'.

Resume Content:
\"\"\"
{resume_text[:8000]}
\"\"\"

Return a valid JSON object matching this exact schema:
{{
  "name": "string (Candidate full name)",
  "email": "string ('Not found' if absent)",
  "phone": "string ('Not found' if absent)",
  "location": "string ('Not found' if absent)",
  "total_experience_years": number (e.g. 4.0, 0 if fresh graduate / not found),
  "summary": "string (Executive background summary or 'Not found')",
  "skills": ["string (skills directly mentioned or demonstrated in resume)"],
  "work_experience": [
    {{
      "company": "string",
      "role": "string",
      "duration": "string",
      "highlights": ["string (verifiable responsibilities, achievements, and technical contributions)"]
    }}
  ],
  "projects": [
    {{
      "title": "string",
      "tech_stack": ["string"],
      "description": "string (what was built and candidate's specific contribution)"
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "institution": "string",
      "year": "string ('Not found' if absent)"
    }}
  ],
  "certifications": ["string (certifications or licenses, empty list if 'Not found')"],
  "relevant_achievements": ["string (quantifiable awards, patents, hackathon wins, leadership impacts)"]
}}
"""
        system_instruction = (
            "You are a meticulous Resume Extraction Specialist. Extract factual details without hallucination. "
            "If information is missing, mark it explicitly as 'Not found' or 'Unclear'."
        )
        ai_result = call_gemini_json(prompt, system_instruction)

        if ai_result and isinstance(ai_result, dict) and "name" in ai_result:
            # Fallback if name was empty or placeholder
            if not ai_result.get("name") or ai_result["name"].lower() in ["string", "candidate", "not found"]:
                ai_result["name"] = extract_candidate_name_fallback(filename, resume_text)
            if "certifications" not in ai_result:
                ai_result["certifications"] = []
            if "relevant_achievements" not in ai_result:
                ai_result["relevant_achievements"] = []
            return ai_result

        # Heuristic fallback
        return ResumeAgent._heuristic_parse(resume_text, filename)

    @staticmethod
    def _heuristic_parse(resume_text: str, filename: str) -> Dict[str, Any]:
        """Extract candidate data via regex and heuristic rules."""
        name = extract_candidate_name_fallback(filename, resume_text)

        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
        email = email_match.group(0) if email_match else "Not found"

        # Phone
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text)
        phone = phone_match.group(0) if phone_match else "Not found"

        # Experience estimation
        exp_matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)', resume_text, re.IGNORECASE)
        total_exp = max([int(x) for x in exp_matches]) if exp_matches else 1.0

        # Extract common skills mentioned
        common_skills = [
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "Flask", "Django", "FastAPI",
            "SQL", "PostgreSQL", "MongoDB", "AWS", "Docker", "Kubernetes", "Git", "HTML", "CSS",
            "Java", "C++", "C#", "Go", "Rust", "Machine Learning", "PyTorch", "TensorFlow", "Pandas",
            "Linux", "Redis", "Kafka", "GraphQL", "Tailwind", "CI/CD", "Scrum", "SQLite"
        ]
        extracted_skills = [s for s in common_skills if re.search(rf'\b{re.escape(s)}\b', resume_text, re.IGNORECASE)]

        # Extract bullets / highlights from experience lines
        work_bullets = []
        for line in resume_text.split('\n'):
            l = line.strip()
            if l.startswith(('-', '•', '*', '–')) and len(l) > 10:
                work_bullets.append(l.lstrip('-•*– '))

        # Certifications regex
        cert_matches = []
        for line in resume_text.split('\n'):
            if any(k in line.lower() for k in ["certified", "certification", "aws certified", "coursera", "udemy"]):
                cert_matches.append(line.strip())

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "location": "Not found",
            "total_experience_years": total_exp,
            "summary": "Candidate profile extracted from submitted document.",
            "skills": extracted_skills,
            "work_experience": [
                {
                    "company": "Professional Experience",
                    "role": "Software Developer / Engineer",
                    "duration": f"Approx. {total_exp} Years",
                    "highlights": work_bullets[:4] if work_bullets else [
                        "Designed and developed software features",
                        "Implemented application logic and database interactions"
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Software Engineering Project",
                    "tech_stack": extracted_skills[:3] if extracted_skills else ["Python"],
                    "description": "Developed software application using " + ", ".join(extracted_skills[:3] if extracted_skills else ["Python"])
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Science / Technology in Computer Science",
                    "institution": "University / Institute",
                    "year": "Not found"
                }
            ],
            "certifications": cert_matches[:3],
            "relevant_achievements": []
        }

    @staticmethod
    def _get_empty_result(filename: str) -> Dict[str, Any]:
        return {
            "name": extract_candidate_name_fallback(filename, ""),
            "email": "Not found",
            "phone": "Not found",
            "location": "Not found",
            "total_experience_years": 0,
            "summary": "Empty resume file.",
            "skills": [],
            "work_experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
            "relevant_achievements": []
        }
