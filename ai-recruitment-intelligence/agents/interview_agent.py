from typing import Dict, Any, List
from agents import call_gemini_json


class InterviewAgent:
    """
    Interview Intelligence Agent.
    Generates 5 personalized, categorized interview questions for a candidate based on:
    - Job Description requirements
    - Candidate skills & proficiency
    - Stated projects & tech stacks
    - Employment history & experience bullets
    - Missing or uncertain requirements

    Categories:
    1. Technical
    2. Project-based
    3. Experience-based
    4. Problem-solving
    5. Role-specific
    """

    @staticmethod
    def generate_interview_questions(
        candidate_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        skill_analysis: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        noise_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate 5 personalized, high-yield interview questions with rationales and evaluation criteria.
        """
        name = candidate_data.get("name", "Candidate")
        role_title = jd_data.get("title", "Target Role")
        work_exp = candidate_data.get("work_experience", [])
        projects = candidate_data.get("projects", [])
        cand_skills = skill_analysis.get("normalized_candidate_skills", candidate_data.get("skills", []))
        matched_must = skill_analysis.get("matched_must_haves", [])
        missing_must = skill_analysis.get("missing_critical_skills", [])
        uncertain_items = [e for e in evidence_items if e.get("status") in ["PARTIAL", "UNCLEAR"]]

        prompt = f"""
Act as a Principal Technical Interviewer and Hiring Strategist.
Generate exactly 5 personalized, highly specific interview questions for candidate {name} applying for the {role_title} role.

Context Information:
- Job Description Title: {role_title}
- JD Required Skills: {jd_data.get('required_skills') or jd_data.get('must_have_skills', [])}
- JD Preferred Skills: {jd_data.get('preferred_skills') or jd_data.get('nice_to_have_skills', [])}
- Candidate Matched Skills: {matched_must}
- Missing Skills (Not found): {missing_must}
- Uncertain / Unverified Claims: {[e.get('requirement') for e in uncertain_items]}
- Candidate Work History: {work_exp}
- Candidate Projects: {projects}
- Anti-Noise Flags: {[f.get('skill_or_keyword') for f in noise_data.get('flags', [])]}

Rules:
1. Divide questions into EXACTLY these 5 categories:
   1) Technical
   2) Project-based
   3) Experience-based
   4) Problem-solving
   5) Role-specific
2. Each question MUST cite real details from the candidate's actual projects or work bullets, or probe a missing/uncertain requirement. Do NOT invent fake companies, projects, or metrics.
3. Include a clear 'why_generated' rationale explaining the exact motivation behind the question.
4. Include a 'what_to_listen_for' evaluation rubric.

Return valid JSON with this exact schema:
{{
  "interview_questions": [
    {{
      "category": "Technical",
      "question": "string (in-depth technical probe)",
      "why_generated": "string (concrete reason referencing candidate skills or missing requirements)",
      "what_to_listen_for": "string (evaluation benchmarks)"
    }},
    {{
      "category": "Project-based",
      "question": "string (referencing candidate's specific project from resume)",
      "why_generated": "string (referencing candidate project name or tech stack)",
      "what_to_listen_for": "string (evaluation benchmarks)"
    }},
    {{
      "category": "Experience-based",
      "question": "string (referencing candidate's past work experience or company context)",
      "why_generated": "string (referencing employment duration, scaling, or team responsibilities)",
      "what_to_listen_for": "string (evaluation benchmarks)"
    }},
    {{
      "category": "Problem-solving",
      "question": "string (scenario testing real-world trade-offs in this domain)",
      "why_generated": "string (referencing domain challenges relevant to this candidate)",
      "what_to_listen_for": "string (evaluation benchmarks)"
    }},
    {{
      "category": "Role-specific",
      "question": "string (testing alignment with target role responsibilities)",
      "why_generated": "string (referencing JD expectations and candidate readiness)",
      "what_to_listen_for": "string (evaluation benchmarks)"
    }}
  ]
}}
"""
        system_instruction = (
            "You are an Elite Technical Hiring Architect. Create rigorous, non-generic, "
            "personalized interview questions grounded in factual resume context and job requirements."
        )
        ai_result = call_gemini_json(prompt, system_instruction)

        if ai_result and isinstance(ai_result, dict) and "interview_questions" in ai_result:
            raw_questions = ai_result["interview_questions"]
            if isinstance(raw_questions, list) and len(raw_questions) >= 5:
                formatted = []
                categories = ["Technical", "Project-based", "Experience-based", "Problem-solving", "Role-specific"]
                for i, q in enumerate(raw_questions[:5]):
                    if isinstance(q, dict):
                        cat = q.get("category") or (categories[i] if i < len(categories) else "Technical")
                        formatted.append({
                            "category": cat,
                            "question": q.get("question", "").strip(),
                            "why_generated": q.get("why_generated", q.get("explanation", "Targeted probe based on candidate profile.")).strip(),
                            "what_to_listen_for": q.get("what_to_listen_for", "Key domain competency and problem-solving depth.").strip()
                        })
                if len(formatted) == 5 and all(q["question"] for q in formatted):
                    return formatted

        # Heuristic Generator Fallback
        return InterviewAgent._heuristic_generate_questions(
            name=name,
            role_title=role_title,
            matched_must=matched_must,
            missing_must=missing_must,
            uncertain_items=uncertain_items,
            work_exp=work_exp,
            projects=projects,
            jd_data=jd_data
        )

    @staticmethod
    def _heuristic_generate_questions(
        name: str,
        role_title: str,
        matched_must: List[str],
        missing_must: List[str],
        uncertain_items: List[Dict[str, Any]],
        work_exp: List[Dict[str, Any]],
        projects: List[Dict[str, Any]],
        jd_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rule-based heuristic generator for 5 categorized interview questions."""
        questions = []

        # 1. Technical Question
        if missing_must:
            miss_skill = missing_must[0]
            questions.append({
                "category": "Technical",
                "question": f"Our role heavily relies on {miss_skill}, which wasn't highlighted in your resume. How would you apply your existing skills in {', '.join(matched_must[:2]) if matched_must else 'software engineering'} to get up to speed with {miss_skill} in production?",
                "why_generated": f"Generated because '{miss_skill}' is a core JD requirement that was not found in the candidate's resume.",
                "what_to_listen_for": f"Fast ramp-up strategy, conceptual understanding of {miss_skill}, and ability to translate adjacent experience."
            })
        elif matched_must:
            top_skill = matched_must[0]
            questions.append({
                "category": "Technical",
                "question": f"Given your extensive experience with {top_skill}, what are the most complex concurrency or performance bottlenecks you have had to debug, and what profiling tools did you rely on?",
                "why_generated": f"Generated to probe deep technical mastery in '{top_skill}', which is a verified core requirement.",
                "what_to_listen_for": "Low-level system understanding, memory/CPU profiling techniques, and concrete debugging methodology."
            })
        else:
            questions.append({
                "category": "Technical",
                "question": "Can you walk us through the core architectural patterns you use when designing scalable, resilient backend APIs?",
                "why_generated": "Generated as a baseline technical probe into foundational software architecture.",
                "what_to_listen_for": "Separation of concerns, caching strategies, and database index optimization."
            })

        # 2. Project-based Question
        if projects:
            proj = projects[0]
            proj_title = proj.get("title", "Recent Project")
            stack = ", ".join(proj.get("tech_stack", [])) or "the project stack"
            questions.append({
                "category": "Project-based",
                "question": f"In your project '{proj_title}' using {stack}, what was the most difficult architectural trade-off you had to make between speed of delivery and system scalability?",
                "why_generated": f"Generated specifically based on candidate's project '{proj_title}' listed in their resume.",
                "what_to_listen_for": "Clear ownership, trade-off analysis, data model decisions, and measurable outcomes."
            })
        else:
            questions.append({
                "category": "Project-based",
                "question": "Can you describe an end-to-end technical project you engineered, highlighting the schema design and API contract design you implemented?",
                "why_generated": "Generated to assess full-lifecycle engineering implementation skills.",
                "what_to_listen_for": "Structured project execution, schema migration safety, and clean API design."
            })

        # 3. Experience-based Question
        if work_exp:
            exp = work_exp[0]
            company = exp.get("company", "your previous company")
            role = exp.get("role", "Engineer")
            questions.append({
                "category": "Experience-based",
                "question": f"During your time as {role} at {company}, how did you handle cross-functional requirements and code review standards when shipping mission-critical features?",
                "why_generated": f"Generated based on candidate's employment as {role} at {company}.",
                "what_to_listen_for": "Collaboration skills, mentorship, CI/CD discipline, and code quality enforcement."
            })
        else:
            questions.append({
                "category": "Experience-based",
                "question": "How do you prioritize technical debt against rapid product feature delivery when working in a high-velocity team?",
                "why_generated": "Generated to evaluate practical workplace engineering prioritization.",
                "what_to_listen_for": "Pragmatic balance, refactoring strategies, and communication with stakeholders."
            })

        # 4. Problem-solving Question
        questions.append({
            "category": "Problem-solving",
            "question": "Suppose our production API experiences a sudden 10x traffic spike causing database connection pool exhaustion and elevated 504 gateway timeouts. What is your step-by-step diagnostic and mitigation process?",
            "why_generated": "Generated to assess incident response, triage methodology, and architectural resilience under pressure.",
            "what_to_listen_for": "Calm triage, connection pooling, rate limiting, read replicas/caching, and post-mortem analysis."
        })

        # 5. Role-specific Question
        responsibilities = jd_data.get("job_responsibilities", [])
        resp_snippet = responsibilities[0] if responsibilities else f"delivering core milestones for the {role_title} role"
        questions.append({
            "category": "Role-specific",
            "question": f"A primary responsibility of this position is '{resp_snippet}'. How have your past deliverables prepared you to execute this on day one?",
            "why_generated": f"Generated directly from the core JD responsibility '{resp_snippet}' to test immediate role alignment.",
            "what_to_listen_for": "Direct relevance of past experience to team goals and proactive execution mentality."
        })

        return questions[:5]
