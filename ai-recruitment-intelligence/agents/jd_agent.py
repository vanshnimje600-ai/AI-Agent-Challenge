import re
from typing import Dict, Any, List
from agents import call_gemini_json


class JDAgent:
    """
    Stage 1: Job Description Analysis Agent.
    Deconstructs raw JD text into structured requirements:
    - Required Skills (Must-Haves)
    - Preferred Skills (Nice-to-Haves)
    - Experience Requirements
    - Education Requirements
    - Job Responsibilities
    - Other Important Requirements
    """

    @staticmethod
    def analyze(jd_text: str) -> Dict[str, Any]:
        """Analyze job description text using Gemini AI or structured heuristic fallback."""
        if not jd_text or not jd_text.strip():
            return JDAgent._get_empty_result()

        prompt = f"""
Analyze the following Job Description and extract structured requirements into valid JSON.

Job Description Content:
\"\"\"
{jd_text[:8000]}
\"\"\"

Return a valid JSON object matching this exact schema:
{{
  "title": "string (The target job title)",
  "company": "string (Company name if mentioned, otherwise 'Not specified')",
  "min_experience_years": number (e.g., 3, 0 if not specified),
  "experience_requirements": "string (e.g., '3+ years in backend engineering with microservices')",
  "education_requirements": "string (e.g., 'Bachelor\\'s degree in Computer Science or equivalent' or 'Not specified')",
  "domain": "string (e.g., 'Backend Engineering / Distributed Systems')",
  "required_skills": ["string (essential skills explicitly required)"],
  "preferred_skills": ["string (bonus/nice-to-have skills)"],
  "job_responsibilities": ["string (core duties and expectations)"],
  "other_requirements": ["string (e.g. on-site location, visa, specific tools, domain knowledge)"],
  "summary": "string (2-3 sentence executive summary of the position requirements)"
}}
"""
        system_instruction = (
            "You are an expert Talent Intelligence Analyst. Extract comprehensive, de-duplicated, and precise "
            "job requirements. Do not invent requirements that are not in the text. If a field is not present, "
            "set it to 'Not specified' or empty list."
        )
        ai_result = call_gemini_json(prompt, system_instruction)

        if ai_result and isinstance(ai_result, dict) and ("required_skills" in ai_result or "must_have_skills" in ai_result):
            # Normalize schema aliases
            req_skills = ai_result.get("required_skills") or ai_result.get("must_have_skills", [])
            pref_skills = ai_result.get("preferred_skills") or ai_result.get("nice_to_have_skills", [])
            ai_result["required_skills"] = req_skills
            ai_result["must_have_skills"] = req_skills
            ai_result["preferred_skills"] = pref_skills
            ai_result["nice_to_have_skills"] = pref_skills
            if "job_responsibilities" not in ai_result and "key_responsibilities" in ai_result:
                ai_result["job_responsibilities"] = ai_result["key_responsibilities"]
            return ai_result

        # Heuristic fallback if LLM is unavailable
        return JDAgent._heuristic_analyze(jd_text)

    @staticmethod
    def _heuristic_analyze(jd_text: str) -> Dict[str, Any]:
        """Rule-based extraction when LLM is unavailable."""
        lines = [l.strip() for l in jd_text.split('\n') if l.strip()]
        title = lines[0] if lines else "Software Engineer"
        if len(title) > 60:
            title = "Target Engineering Position"

        # Experience regex
        exp_match = re.search(r'(\d+)\+?\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', jd_text, re.IGNORECASE)
        min_exp = int(exp_match.group(1)) if exp_match else 2
        exp_text = f"Minimum {min_exp}+ years of relevant experience" if min_exp else "Not specified"

        # Education regex
        edu_text = "Not specified"
        edu_match = re.search(r'(?i)(bachelor|master|phd|b\.?s\.?|m\.?s\.?|b\.?tech|computer science|engineering degree)', jd_text)
        if edu_match:
            edu_text = "Bachelor's Degree in Computer Science or related engineering field"

        # Extract tech keywords
        common_tech = [
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "Flask", "Django", "FastAPI",
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "AWS", "Docker", "Kubernetes", "Git", "REST API",
            "GraphQL", "Java", "C++", "C#", ".NET", "Go", "Rust", "Machine Learning", "PyTorch", "TensorFlow",
            "Redis", "Kafka", "Linux", "CI/CD", "HTML", "CSS"
        ]
        found_skills = [skill for skill in common_tech if re.search(rf'\b{re.escape(skill)}\b', jd_text, re.IGNORECASE)]

        req_skills = found_skills[:6] if found_skills else ["Problem Solving", "Software Engineering", "REST API"]
        pref_skills = found_skills[6:10] if len(found_skills) > 6 else ["Agile Methodology", "Docker", "CI/CD"]

        return {
            "title": title,
            "company": "Hiring Organization",
            "min_experience_years": min_exp,
            "experience_requirements": exp_text,
            "education_requirements": edu_text,
            "domain": "Software Engineering",
            "required_skills": req_skills,
            "must_have_skills": req_skills,
            "preferred_skills": pref_skills,
            "nice_to_have_skills": pref_skills,
            "job_responsibilities": [
                "Design, develop, and maintain performant software features and services",
                "Participate in code reviews, architectural discussions, and automated testing",
                "Collaborate with engineering teammates to fulfill product milestones"
            ],
            "other_requirements": [
                f"Demonstrated background meeting the {min_exp}+ years experience requirement."
            ],
            "summary": f"Seeking candidate with strong foundation in {', '.join(req_skills[:3])}."
        }

    @staticmethod
    def _get_empty_result() -> Dict[str, Any]:
        return {
            "title": "Untitled Position",
            "company": "Not specified",
            "min_experience_years": 0,
            "experience_requirements": "Not specified",
            "education_requirements": "Not specified",
            "domain": "General",
            "required_skills": [],
            "must_have_skills": [],
            "preferred_skills": [],
            "nice_to_have_skills": [],
            "job_responsibilities": [],
            "other_requirements": [],
            "summary": "No job description content provided."
        }
