from typing import Dict, Any, List
from agents import call_gemini_json


class ShortlistAgent:
    """
    Stage 7: Shortlist & Explainability Agent.
    Synthesizes outputs from all preceding agents into an explainable recruitment dossier:
    - Match Percentage
    - Recommendation (Strong Shortlist, Potential Match, Needs Review, Low Relevance)
    - Demonstrated Strengths (backed by resume evidence)
    - Missing Requirements (marked 'Not found')
    - Uncertain Requirements (marked 'Unclear' / vague claims)
    - Primary Evidence Citations
    - Clear Executive Explanation
    - Targeted Interview Questions
    """

    @staticmethod
    def generate_verdict(
        candidate_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        skill_analysis: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        noise_analysis: Dict[str, Any],
        match_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Produce explainable hiring intelligence dossier.
        """
        name = candidate_data.get("name", "Candidate")
        match_percentage = match_result.get("match_percentage", match_result.get("final_score", 0.0))
        recommendation = match_result.get("recommendation", match_result.get("match_tier", "Needs Review"))

        # Pre-filter evidence items for prompt context
        verified_ev = [e for e in evidence_items if e.get("status") == "VERIFIED"]
        unclear_ev = [e for e in evidence_items if e.get("status") in ["PARTIAL", "UNCLEAR"]]
        missing_ev = [e for e in evidence_items if e.get("status") == "NOT_FOUND"]

        prompt = f"""
Act as a Principal Talent Assessment Strategist. Synthesize the multi-agent analysis for candidate {name} applying for {jd_data.get('title', 'Target Role')}.

Data Inputs:
- Match Percentage: {match_percentage}% ({recommendation})
- Required Skills Matched: {skill_analysis.get('matched_must_haves', [])}
- Missing Required Skills: {skill_analysis.get('missing_critical_skills', [])}
- Verified Evidence Items: {[{'req': e.get('requirement'), 'quote': e.get('evidence_snippet'), 'source': e.get('source_section')} for e in verified_ev]}
- Uncertain/Partial Items: {[{'req': e.get('requirement'), 'quote': e.get('evidence_snippet')} for e in unclear_ev]}
- Unsubstantiated/Missing: {[e.get('requirement') for e in missing_ev]}
- Anti-Noise Assessment: {noise_analysis.get('noise_risk_level')} risk ({noise_analysis.get('noise_verdict')})

Requirements:
1. Every major strength MUST cite concrete evidence/quotes from the candidate's background.
2. Clearly separate Missing Requirements ('Not found') from Uncertain Requirements ('Unclear').
3. Provide a transparent 3-sentence hiring explanation.
4. Craft 2-3 tailored interview probes targeting the uncertain or missing requirements.

Return valid JSON with this exact schema:
{{
  "match_percentage": number,
  "recommendation": "string",
  "explanation": "string (transparent narrative of candidate fit, backed by evidence)",
  "strengths": ["string (concrete verified strength with resume citation)"],
  "missing_requirements": ["string (essential JD requirement confirmed 'Not found' in resume)"],
  "uncertain_requirements": ["string (claims that are vague, shallow, or marked 'Unclear')"],
  "evidence_highlights": [
    {{
      "requirement": "string",
      "proof_quote": "string",
      "source": "string"
    }}
  ],
  "interview_questions": [
    {{
      "topic": "string",
      "question": "string",
      "what_to_listen_for": "string"
    }}
  ]
}}
"""
        system_instruction = (
            "You are an Explainable Recruitment Intelligence Agent. Base every finding solely on real resume evidence. "
            "Never fabricate facts. If information is missing, mark it as 'Not found' or 'Unclear'."
        )
        ai_result = call_gemini_json(prompt, system_instruction)

        if ai_result and isinstance(ai_result, dict) and "strengths" in ai_result:
            # Enforce consistent fields
            ai_result["match_percentage"] = match_percentage
            ai_result["recommendation"] = recommendation
            ai_result["executive_summary"] = ai_result.get("explanation", "")
            return ai_result

        # Heuristic Synthesis Fallback
        strengths = []
        for e in verified_ev[:3]:
            strengths.append(f"Demonstrated {e.get('requirement')} capability at {e.get('source_section')}: \"{e.get('evidence_snippet')}\"")

        if not strengths:
            if skill_analysis.get("matched_must_haves"):
                strengths.append(f"Relevant background in: {', '.join(skill_analysis['matched_must_haves'][:3])}.")
            else:
                strengths.append("Foundational technical literacy in software development.")

        missing_reqs = []
        for missing in skill_analysis.get("missing_critical_skills", []):
            missing_reqs.append(f"{missing} - Not found in candidate resume")
        for e in missing_ev:
            if not any(e.get("requirement", "") in m for m in missing_reqs):
                missing_reqs.append(f"{e.get('requirement')} - Not found in candidate profile")

        uncertain_reqs = []
        for e in unclear_ev:
            uncertain_reqs.append(f"{e.get('requirement')} - Unclear depth (mentioned without deep project metrics)")
        for flag in noise_analysis.get("flags", []):
            if flag.get("severity") in ["HIGH", "MEDIUM"]:
                uncertain_reqs.append(f"{flag.get('skill_or_keyword')} - {flag.get('explanation')}")

        ev_highlights = [
            {
                "requirement": e.get("requirement", ""),
                "proof_quote": e.get("evidence_snippet", "Not found"),
                "source": e.get("source_section", "Resume")
            }
            for e in verified_ev[:3]
        ]

        # Interview questions to probe uncertain / missing requirements
        questions = []
        for missing in (skill_analysis.get("missing_critical_skills", []) + [e.get("requirement") for e in missing_ev])[:2]:
            questions.append({
                "topic": f"Hands-on experience with {missing}",
                "question": f"The role requires {missing}, which was not found in your resume. Can you describe any practical experience or adjacent tooling you've used?",
                "what_to_listen_for": f"Direct applied knowledge, core concepts, and ability to ramp up on {missing} quickly."
            })

        for unverified in unclear_ev[:2]:
            req = unverified.get("requirement", "Core Skill")
            questions.append({
                "topic": f"Depth of {req} Application",
                "question": f"Can you detail a production project where you implemented {req} and explain the technical challenges you solved?",
                "what_to_listen_for": "Specific architectural decisions, quantitative metrics, and ownership."
            })

        if not questions:
            questions.append({
                "topic": "System Design & Problem Solving",
                "question": "Can you walk us through the most complex software challenge you engineered from scratch?",
                "what_to_listen_for": "Structured thinking, trade-off evaluation, and clean code principles."
            })

        explanation = (
            f"{name} is assigned a {match_percentage}% match ({recommendation}) for the {jd_data.get('title', 'target role')} position. "
            f"The candidate substantiates key requirements in {', '.join(skill_analysis.get('matched_must_haves', ['core stack'])[:2])}, "
            f"while {len(missing_reqs)} requirement(s) are not found and warrant screening."
        )

        return {
            "match_percentage": match_percentage,
            "recommendation": recommendation,
            "explanation": explanation,
            "executive_summary": explanation,
            "strengths": strengths,
            "missing_requirements": missing_reqs if missing_reqs else ["None identified"],
            "uncertain_requirements": uncertain_reqs if uncertain_reqs else ["None flagged"],
            "evidence_highlights": ev_highlights,
            "interview_questions": questions
        }
