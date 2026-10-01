import re
from typing import Dict, Any, List
from agents import call_gemini_json


class NoiseAgent:
    """
    Stage 5: Noise Detection Agent.
    Detects keyword stuffing, buzzword dumping, and false-positive matches.
    Prevents candidates who repeat high-value keywords without applied project experience
    from tricking the matching algorithms.
    """

    @staticmethod
    def detect_noise(
        resume_text: str,
        candidate_skills: List[str],
        work_experience: List[Dict[str, Any]],
        projects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate candidate resume for keyword stuffing, repetition without depth,
        and authentic application of claimed skills.
        """
        exp_text = " ".join([
            " ".join(item.get("highlights", [])) + " " + item.get("role", "") + " " + item.get("company", "")
            for item in work_experience
        ])
        proj_text = " ".join([
            item.get("title", "") + " " + item.get("description", "") + " " + " ".join(item.get("tech_stack", []))
            for item in projects
        ])
        applied_body = (exp_text + " " + proj_text).lower()

        # Count occurrences of claimed skills across raw text vs applied text
        frequency_stats = {}
        for skill in candidate_skills:
            clean = skill.strip().lower()
            if len(clean) >= 2:
                raw_count = len(re.findall(rf'\b{re.escape(clean)}\b', resume_text.lower()))
                applied_count = len(re.findall(rf'\b{re.escape(clean)}\b', applied_body))
                frequency_stats[skill] = {
                    "raw_count": raw_count,
                    "applied_count": applied_count,
                    "contextual": applied_count > 0
                }

        prompt = f"""
Audit this candidate profile for keyword stuffing, buzzword dumps, and false-positive risk.
Claimed Skills: {candidate_skills}
Skill Frequency & Context Breakdown: {frequency_stats}
Applied Experience & Projects Content:
\"\"\"
{applied_body[:4000]}
\"\"\"

Rules:
- If a skill is repeated multiple times in the resume but has ZERO mentions in projects or work bullets, flag it as a False Positive / Keyword Stuffing attempt.
- Assess overall noise risk level: 'LOW', 'MEDIUM', or 'HIGH'.

Return valid JSON with this exact schema:
{{
  "noise_score": number (0 to 100, where 0 is completely authentic and 100 is pure keyword spam),
  "authenticity_score": number (100 - noise_score),
  "noise_risk_level": "LOW" | "MEDIUM" | "HIGH",
  "flags": [
    {{
      "type": "string (e.g., 'Keyword Stuffing without Context', 'Shallow Buzzword Dump', 'Repetition Inflation')",
      "skill_or_keyword": "string",
      "severity": "LOW" | "MEDIUM" | "HIGH",
      "explanation": "string (specific evidence of why this is flagged)"
    }}
  ],
  "noise_verdict": "string (transparent assessment of candidate authentic vs inflated claims)"
}}
"""
        system_instruction = (
            "You are a Forensic Anti-Fraud Recruitment Agent. Detect keyword stuffing, deceptive padding, "
            "and ungrounded buzzwords. Be objective and cite factual inconsistencies."
        )
        ai_result = call_gemini_json(prompt, system_instruction)

        if ai_result and isinstance(ai_result, dict) and "noise_score" in ai_result:
            return ai_result

        # Heuristic Detection Fallback
        flags = []
        unsubstantiated_count = 0

        for skill, stat in frequency_stats.items():
            raw_c = stat["raw_count"]
            app_c = stat["applied_count"]
            if raw_c >= 2 and app_c == 0:
                unsubstantiated_count += 1
                flags.append({
                    "type": "Keyword Mentioned Without Applied Proof",
                    "skill_or_keyword": skill,
                    "severity": "HIGH" if raw_c >= 3 else "MEDIUM",
                    "explanation": f"'{skill}' was mentioned {raw_c} time(s) in the resume but has 0 supporting evidence in work history or project bullets."
                })
            elif raw_c > 0 and app_c == 0:
                unsubstantiated_count += 1
                flags.append({
                    "type": "Unsubstantiated Skill Claim",
                    "skill_or_keyword": skill,
                    "severity": "LOW",
                    "explanation": f"'{skill}' was listed in skill tags without practical elaboration."
                })

        total_skills = max(len(candidate_skills), 1)
        unsub_ratio = unsubstantiated_count / total_skills
        calculated_noise = min(round(unsub_ratio * 70.0, 1), 90.0)
        risk = "HIGH" if calculated_noise > 45 else ("MEDIUM" if calculated_noise > 20 else "LOW")

        return {
            "noise_score": calculated_noise,
            "authenticity_score": round(100.0 - calculated_noise, 1),
            "noise_risk_level": risk,
            "flags": flags[:6],
            "noise_verdict": (
                f"Candidate demonstrates {risk.lower()} keyword noise risk. "
                f"{len(candidate_skills) - unsubstantiated_count} of {len(candidate_skills)} claimed skills are backed by verifiable applied context."
            )
        }
