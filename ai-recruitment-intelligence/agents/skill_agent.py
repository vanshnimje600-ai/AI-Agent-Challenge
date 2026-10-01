from typing import Dict, Any, List
from agents import call_gemini_json

# Comprehensive Skill Normalization Taxonomy dictionary
SKILL_TAXONOMY = {
    # JavaScript & Ecosystem
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "react native": "React Native",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node js": "Node.js",
    "expressjs": "Express.js",
    "express.js": "Express.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angularjs": "Angular",
    "angular.js": "Angular",
    
    # Python & Frameworks
    "py": "Python",
    "python3": "Python",
    "python": "Python",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "sqlite3": "SQLite",
    "redis": "Redis",
    
    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    "ms azure": "Microsoft Azure",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker containers": "Docker",
    "docker": "Docker",
    "ci cd": "CI/CD",
    "ci/cd": "CI/CD",
    "git": "Git",
    "github": "Git",
    "gitlab": "Git",
    
    # Backend & Architecture
    "restful api": "REST API",
    "rest apis": "REST API",
    "rest api": "REST API",
    "rest": "REST API",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "microservices": "Microservices Architecture",
    
    # AI / ML
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "llm": "LLMs / Generative AI",
    "llms": "LLMs / Generative AI",
    "genai": "LLMs / Generative AI",
    "generative ai": "LLMs / Generative AI",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow"
}


class SkillAgent:
    """
    Stage 3: Skill Normalization Agent.
    Recognizes synonymous, equivalent, and variant skill terms (e.g., 'JS' -> 'JavaScript',
    'Postgres' -> 'PostgreSQL', 'React.js' -> 'React').
    Maps candidate competencies against required and preferred JD skills.
    """

    @staticmethod
    def normalize_skill_name(skill: str) -> str:
        """Normalize a single skill string to canonical industry taxonomy."""
        clean = skill.strip().lower()
        return SKILL_TAXONOMY.get(clean, skill.strip().title() if len(skill) <= 4 else skill.strip())

    @staticmethod
    def analyze_skills(candidate_skills: List[str], jd_must_haves: List[str], jd_nice_to_haves: List[str]) -> Dict[str, Any]:
        """
        Cross-analyze candidate skills against job requirements.
        Uses Gemini AI for semantic mapping with local taxonomy fallback.
        """
        norm_candidate = list({SkillAgent.normalize_skill_name(s) for s in candidate_skills if s.strip()})
        norm_must = list({SkillAgent.normalize_skill_name(s) for s in jd_must_haves if s.strip()})
        norm_nice = list({SkillAgent.normalize_skill_name(s) for s in jd_nice_to_haves if s.strip()})

        # Record active mappings
        mappings = {}
        for s in candidate_skills:
            canonical = SkillAgent.normalize_skill_name(s)
            if s.strip().lower() != canonical.lower():
                mappings[s] = canonical

        prompt = f"""
Compare candidate skills against the Job Description requirements using intelligent skill normalization.
Candidate Skills: {norm_candidate}
JD Required Must-Have Skills: {norm_must}
JD Preferred Nice-to-Have Skills: {norm_nice}

Rules:
1. Recognize semantic equivalence (e.g. 'FastAPI' satisfies 'Python Backend Framework', 'Postgres' is 'PostgreSQL', 'JS' is 'JavaScript').
2. Identify missing critical skills that the candidate has NOT demonstrated.
3. Calculate percentage of required skills covered.

Return valid JSON with this exact schema:
{{
  "normalized_candidate_skills": ["string (canonical skill names)"],
  "matched_must_haves": ["string (required JD skills candidate has)"],
  "matched_nice_to_haves": ["string (preferred skills candidate has)"],
  "missing_critical_skills": ["string (required JD skills completely absent or 'Not found')"],
  "additional_skills": ["string (other relevant demonstrated skills)"],
  "skill_coverage_percentage": number (0 to 100),
  "normalization_notes": ["string (e.g. 'Mapped Postgres to PostgreSQL', 'Mapped React.js to React')"]
}}
"""
        system_instruction = "You are a Skill Taxonomy and Normalization Engine. Output strict, valid JSON without conversational wrapper."
        ai_result = call_gemini_json(prompt, system_instruction)

        if ai_result and isinstance(ai_result, dict) and "matched_must_haves" in ai_result:
            if "normalized_mappings" not in ai_result:
                ai_result["normalized_mappings"] = mappings
            return ai_result

        # Heuristic Matching Fallback
        cand_lower_map = {s.lower(): s for s in norm_candidate}
        matched_must = [m for m in norm_must if m.lower() in cand_lower_map]
        missing_must = [m for m in norm_must if m.lower() not in cand_lower_map]
        matched_nice = [n for n in norm_nice if n.lower() in cand_lower_map]

        all_jd_lower = {m.lower() for m in norm_must}.union({n.lower() for n in norm_nice})
        additional = [s for s in norm_candidate if s.lower() not in all_jd_lower]

        coverage = 0.0
        if norm_must:
            coverage = round((len(matched_must) / len(norm_must)) * 100, 1)

        norm_notes = [f"Normalized '{raw}' to standard taxonomy '{can}'" for raw, can in mappings.items()]

        return {
            "normalized_candidate_skills": norm_candidate,
            "matched_must_haves": matched_must,
            "matched_nice_to_haves": matched_nice,
            "missing_critical_skills": missing_must,
            "additional_skills": additional[:8],
            "skill_coverage_percentage": coverage,
            "normalization_notes": norm_notes,
            "normalized_mappings": mappings
        }
