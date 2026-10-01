"""
Comprehensive test for the 7-stage coordinated recruitment pipeline.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.jd_agent import JDAgent
from agents.resume_agent import ResumeAgent
from agents.skill_agent import SkillAgent
from agents.evidence_agent import EvidenceAgent
from agents.noise_agent import NoiseAgent
from agents.matching_agent import MatchingAgent
from agents.shortlist_agent import ShortlistAgent


def test_coordinated_pipeline():
    print("==================================================")
    print(" Testing 7-Stage Coordinated Multi-Agent Pipeline ")
    print("==================================================")

    sample_jd = """
    Job Title: Senior Full-Stack Python & React Developer
    Company: ScaleForge Innovations
    Experience: 3+ years of professional software engineering
    Education: Bachelor's degree in Computer Science or related STEM field
    Required Skills: Python, Flask, React, PostgreSQL, Docker, REST API
    Preferred Skills: Redis, AWS, Kubernetes, TypeScript
    Responsibilities:
    - Architect and maintain secure backend APIs and modern frontend user interfaces.
    - Optimize relational database queries and containerized workflows.
    - Write unit and integration tests to ensure resilient code delivery.
    Other Requirements: Must be available for hybrid work.
    """

    sample_resume_authentic = """
    Jordan Lee
    Email: jordan.lee@email.com | Phone: (555) 321-7654

    Summary:
    Software Engineer with 4 years of experience building Python web APIs and React frontends.

    Skills:
    Python, Flask, React.js, Postgres, Docker, Git, RESTful API, Redis

    Work Experience:
    Senior Developer | DataFlow Labs (2021 - Present)
    - Developed 12+ scalable REST APIs in Python using Flask and connected to PostgreSQL databases.
    - Built responsive, interactive user dashboards with React.js and styled components.
    - Deployed containerized applications with Docker across staging and production.

    Projects:
    Analytics Engine (Tech: Python, Flask, Postgres, Docker)
    - Engineered high-throughput batch ETL processing pipeline reducing sync delays by 40%.

    Education:
    Bachelor of Science in Computer Science | State University (2020)
    """

    sample_resume_stuffed = """
    Taylor Swift
    Email: taylor@email.com

    Skills:
    Python, Flask, React, PostgreSQL, Docker, Redis, Kubernetes, AWS, Machine Learning, Blockchain, CyberSecurity, Go, Rust, Java

    Work Experience:
    Marketing Assistant | MediaCorp (2023 - 2024)
    - Organized event booth schedules and updated WordPress blog posts.

    Education:
    Bachelor of Arts in Communications (2023)
    """

    # STAGE 1: JD Agent
    print("\n[STAGE 1] JD Analysis Agent...")
    jd_res = JDAgent.analyze(sample_jd)
    print(f"  Title: {jd_res.get('title')}")
    print(f"  Required Skills: {jd_res.get('required_skills')}")
    print(f"  Education: {jd_res.get('education_requirements')}")
    assert len(jd_res.get("required_skills", [])) > 0

    # STAGE 2: Resume Agent
    print("\n[STAGE 2] Resume Analysis Agent...")
    res_profile = ResumeAgent.parse_resume(sample_resume_authentic, "Jordan_Lee.pdf")
    print(f"  Candidate Name: {res_profile.get('name')}")
    print(f"  Total Experience: {res_profile.get('total_experience_years')} yrs")
    print(f"  Extracted Skills: {res_profile.get('skills')}")
    assert res_profile.get("name") == "Jordan Lee"

    # STAGE 3: Skill Normalization Agent
    print("\n[STAGE 3] Skill Normalization Agent...")
    skills_res = SkillAgent.analyze_skills(
        res_profile.get("skills", []),
        jd_res.get("required_skills", []),
        jd_res.get("preferred_skills", [])
    )
    print(f"  Normalized Skills: {skills_res.get('normalized_candidate_skills')}")
    print(f"  Matched Must-Haves: {skills_res.get('matched_must_haves')}")
    print(f"  Missing Critical: {skills_res.get('missing_critical_skills')}")
    print(f"  Skill Coverage: {skills_res.get('skill_coverage_percentage')}%")
    print(f"  Synonym Notes: {skills_res.get('normalization_notes')}")
    # Verify React.js and Postgres were normalized
    assert "React" in skills_res.get("normalized_candidate_skills", [])
    assert "PostgreSQL" in skills_res.get("normalized_candidate_skills", [])

    # STAGE 4: Evidence Agent
    print("\n[STAGE 4] Evidence Verification Agent...")
    evidence_res = EvidenceAgent.extract_evidence(
        jd_requirements=jd_res.get("required_skills", []),
        work_experience=res_profile.get("work_experience", []),
        projects=res_profile.get("projects", []),
        resume_raw_text=sample_resume_authentic
    )
    print(f"  Total Evidence Items Verified: {len(evidence_res)}")
    for ev in evidence_res[:2]:
        print(f"    - {ev.get('requirement')}: [{ev.get('status')}] \"{ev.get('evidence_snippet')[:60]}...\"")

    # STAGE 5: Noise Detection Agent (Authentic candidate vs Stuffed candidate)
    print("\n[STAGE 5] Noise Detection Agent...")
    noise_auth = NoiseAgent.detect_noise(
        sample_resume_authentic,
        res_profile.get("skills", []),
        res_profile.get("work_experience", []),
        res_profile.get("projects", [])
    )
    print(f"  Authentic Resume Noise Risk: {noise_auth.get('noise_risk_level')} (Score: {noise_auth.get('noise_score')})")

    stuffed_profile = ResumeAgent.parse_resume(sample_resume_stuffed, "Taylor_Stuffed.pdf")
    noise_stuffed = NoiseAgent.detect_noise(
        sample_resume_stuffed,
        stuffed_profile.get("skills", []),
        stuffed_profile.get("work_experience", []),
        stuffed_profile.get("projects", [])
    )
    print(f"  Keyword-Stuffed Resume Noise Risk: {noise_stuffed.get('noise_risk_level')} (Score: {noise_stuffed.get('noise_score')})")
    print(f"  Flags Caught: {[f.get('type') for f in noise_stuffed.get('flags', [])]}")
    assert noise_stuffed.get("noise_score", 0) > noise_auth.get("noise_score", 0)

    # STAGE 6: Matching Agent
    print("\n[STAGE 6] Matching Agent (5-Factor Explainable Scoring)...")
    match_auth = MatchingAgent.calculate_match(
        jd_data=jd_res,
        candidate_data=res_profile,
        skill_analysis=skills_res,
        evidence_items=evidence_res,
        noise_analysis=noise_auth
    )
    print(f"  Match Percentage: {match_auth.get('match_percentage')}%")
    print(f"  Recommendation: {match_auth.get('recommendation')}")
    print("  Points Breakdown:")
    for k, v in match_auth.get("breakdown", {}).items():
        print(f"    - {v.get('label')}: {v.get('points')} pts ({v.get('details')})")

    # STAGE 7: Shortlist & Explainability Agent
    print("\n[STAGE 7] Shortlist Agent (Dossier & Targeted Probes)...")
    shortlist_res = ShortlistAgent.generate_verdict(
        candidate_data=res_profile,
        jd_data=jd_res,
        skill_analysis=skills_res,
        evidence_items=evidence_res,
        noise_analysis=noise_auth,
        match_result=match_auth
    )
    print(f"  Explanation: {shortlist_res.get('explanation')}")
    print(f"  Strengths: {shortlist_res.get('strengths')}")
    print(f"  Missing Requirements: {shortlist_res.get('missing_requirements')}")
    print(f"  Uncertain Requirements: {shortlist_res.get('uncertain_requirements')}")
    print(f"  Tailored Interview Probes:")
    for q in shortlist_res.get("interview_questions", []):
        print(f"    ? [{q.get('topic')}]: {q.get('question')}")

    print("\n[SUCCESS] All 7 Stages Executed Cohesively and Passed Tests!")


if __name__ == "__main__":
    test_coordinated_pipeline()
