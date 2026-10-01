from typing import Dict, Any, List


class MatchingAgent:
    """
    Stage 6: Matching Agent.
    Compares the candidate profile against the actual JD requirements across 5 dimensions:
    1. Required Skills Alignment (40% Weight)
    2. Experience & Seniority Fit (30% Weight)
    3. Verifiable Project Evidence Quality (20% Weight)
    4. Preferred / Bonus Skills Coverage (10% Weight)
    5. Anti-Noise & Keyword Penalty (Up to -15% Deduction)
    """

    @staticmethod
    def calculate_match(
        jd_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        skill_analysis: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
        noise_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute explainable score breakdown and final candidate fit percentage.
        """
        # 1. Required Skills Match (Max 40 points)
        required_skills = jd_data.get("required_skills") or jd_data.get("must_have_skills", [])
        matched_required = skill_analysis.get("matched_must_haves", [])
        req_ratio = (len(matched_required) / max(len(required_skills), 1)) if required_skills else 1.0
        required_skill_score = round(min(req_ratio * 40.0, 40.0), 1)

        # 2. Preferred Skills Match (Max 10 points)
        preferred_skills = jd_data.get("preferred_skills") or jd_data.get("nice_to_have_skills", [])
        matched_preferred = skill_analysis.get("matched_nice_to_haves", [])
        pref_ratio = (len(matched_preferred) / max(len(preferred_skills), 1)) if preferred_skills else 0.5
        preferred_skill_score = round(min(pref_ratio * 10.0, 10.0), 1)

        # 3. Experience Alignment (Max 30 points)
        required_exp = jd_data.get("min_experience_years", 0)
        cand_exp = candidate_data.get("total_experience_years", 0)

        if required_exp <= 0:
            exp_score = 25.0
            exp_detail = f"{cand_exp} years demonstrated (no hard minimum set in JD)"
        elif cand_exp >= required_exp:
            exp_score = min(25.0 + (cand_exp - required_exp) * 1.5, 30.0)
            exp_detail = f"{cand_exp} yrs exceeds minimum requirement of {required_exp} yrs"
        else:
            exp_score = round((cand_exp / max(required_exp, 1)) * 22.0, 1)
            exp_detail = f"{cand_exp} yrs falls below requested {required_exp} yrs"

        exp_score = round(exp_score, 1)

        # 4. Verifiable Evidence Depth (Max 20 points)
        if evidence_items:
            verified_count = sum(1 for e in evidence_items if e.get("status") == "VERIFIED")
            partial_count = sum(1 for e in evidence_items if e.get("status") in ["PARTIAL", "UNCLEAR"])
            evidence_ratio = (verified_count * 1.0 + partial_count * 0.4) / len(evidence_items)
            evidence_score = round(min(evidence_ratio * 20.0, 20.0), 1)
            evidence_detail = f"{verified_count} of {len(evidence_items)} requirements backed by verified work quotes"
        else:
            evidence_score = 10.0
            evidence_detail = "Standard baseline verification"

        # 5. Keyword Stuffing / False Positive Penalty (Up to -15 points)
        noise_score = noise_analysis.get("noise_score", 0.0)
        noise_penalty = round((noise_score / 100.0) * 15.0, 1)
        noise_detail = f"{noise_score}% noise index (-{noise_penalty} pts deducted)"

        # Final Match Percentage (0 to 100)
        raw_total = required_skill_score + preferred_skill_score + exp_score + evidence_score - noise_penalty
        final_percentage = max(0.0, min(round(raw_total, 1), 100.0))

        # Assign Recommendation Category
        if final_percentage >= 80:
            recommendation = "Strong Shortlist"
            badge_color = "success"
        elif final_percentage >= 65:
            recommendation = "Potential Match"
            badge_color = "primary"
        elif final_percentage >= 50:
            recommendation = "Needs Review"
            badge_color = "warning"
        else:
            recommendation = "Low Relevance"
            badge_color = "danger"

        return {
            "match_percentage": final_percentage,
            "final_score": final_percentage,
            "recommendation": recommendation,
            "match_tier": recommendation,
            "badge_color": badge_color,
            "breakdown": {
                "required_skills": {
                    "points": required_skill_score,
                    "max": 40,
                    "label": "Required Skills Alignment",
                    "details": f"{len(matched_required)}/{len(required_skills)} required skills matched"
                },
                "experience_fit": {
                    "points": exp_score,
                    "max": 30,
                    "label": "Experience Alignment",
                    "details": exp_detail
                },
                "evidence_depth": {
                    "points": evidence_score,
                    "max": 20,
                    "label": "Verifiable Evidence Proof",
                    "details": evidence_detail
                },
                "preferred_skills": {
                    "points": preferred_skill_score,
                    "max": 10,
                    "label": "Preferred Skills Coverage",
                    "details": f"{len(matched_preferred)}/{len(preferred_skills)} preferred skills present"
                },
                "noise_penalty": {
                    "points": -noise_penalty,
                    "max": 0,
                    "label": "Keyword Stuffing Penalty",
                    "details": noise_detail
                }
            }
        }
