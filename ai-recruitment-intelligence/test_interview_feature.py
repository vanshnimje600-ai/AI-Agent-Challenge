"""
Unit & Integration Tests for Interview Intelligence Feature
"""
import os
import json
import unittest
from app import app
from database.database import (
    init_db,
    insert_job,
    insert_candidate,
    update_candidate_analysis,
    get_candidate_by_id,
    get_job_by_id
)
from agents.interview_agent import InterviewAgent
from utils.helpers import safe_json_loads, safe_json_dumps


class TestInterviewIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = app.test_client()

    def test_01_interview_agent_heuristic_generation(self):
        """Test heuristic generation of 5 categorized interview questions with rationales."""
        candidate_data = {
            "name": "Sarah Jenkins",
            "skills": ["Python", "Flask", "PostgreSQL", "Docker"],
            "work_experience": [
                {
                    "company": "CloudTech Solutions",
                    "role": "Senior Backend Engineer",
                    "duration": "2021 - Present",
                    "highlights": [
                        "Architected scalable microservices handling 5M daily requests in Python/Flask.",
                        "Optimized PostgreSQL queries reducing p99 latency by 35%."
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Real-time Metrics Dashboard",
                    "tech_stack": ["Python", "Redis", "WebSockets"],
                    "description": "Streamed live system telemetry using Redis PubSub."
                }
            ]
        }

        jd_data = {
            "title": "Lead Backend Platform Engineer",
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Kafka", "Kubernetes"],
            "preferred_skills": ["AWS", "Terraform"],
            "job_responsibilities": ["Lead platform infrastructure scaling to support multi-region deployments"]
        }

        skill_analysis = {
            "matched_must_haves": ["Python", "PostgreSQL"],
            "missing_critical_skills": ["Kafka", "Kubernetes"],
            "matched_nice_to_haves": ["AWS"]
        }

        evidence_items = [
            {
                "requirement": "Python",
                "status": "VERIFIED",
                "evidence_snippet": "Architected scalable microservices in Python/Flask.",
                "source_section": "Experience: CloudTech Solutions"
            },
            {
                "requirement": "Kafka",
                "status": "NOT_FOUND",
                "evidence_snippet": "Not found in resume",
                "source_section": "N/A"
            }
        ]

        noise_data = {
            "noise_risk_level": "LOW",
            "flags": []
        }

        questions = InterviewAgent.generate_interview_questions(
            candidate_data=candidate_data,
            jd_data=jd_data,
            skill_analysis=skill_analysis,
            evidence_items=evidence_items,
            noise_data=noise_data
        )

        self.assertIsInstance(questions, list)
        self.assertEqual(len(questions), 5, f"Expected exactly 5 questions, got {len(questions)}")

        expected_categories = [
            "Technical",
            "Project-based",
            "Experience-based",
            "Problem-solving",
            "Role-specific"
        ]

        categories_found = [q.get("category") for q in questions]
        self.assertEqual(categories_found, expected_categories, f"Categories mismatch: {categories_found}")

        for q in questions:
            self.assertTrue(len(q.get("question", "").strip()) > 10, f"Question text too short: {q}")
            self.assertTrue(len(q.get("why_generated", "").strip()) > 5, f"why_generated missing: {q}")
            self.assertTrue(len(q.get("what_to_listen_for", "").strip()) > 5, f"what_to_listen_for missing: {q}")

        print("\n[OK] InterviewAgent heuristic generator produced 5 distinct categorized questions successfully!")
        for idx, q in enumerate(questions, 1):
            print(f"  {idx}. [{q['category']}] {q['question'][:75]}...")
            print(f"     -> Why: {q['why_generated'][:75]}...")

    def test_02_api_generate_interview_endpoint(self):
        """Test POST /api/candidate/<candidate_id>/generate-interview route and DB persistence."""
        # 1. Setup sample job in DB
        job_id = insert_job(
            title="Senior AI Engineer",
            company="TechCorp",
            file_name="job_desc.txt",
            file_path="",
            raw_text="Looking for a Senior AI Engineer with Python, PyTorch, LangChain, and vector databases."
        )

        # 2. Setup candidate in DB
        cand_id = insert_candidate(
            job_id=job_id,
            name="Alex Rivera",
            file_name="alex_resume.pdf",
            file_path="",
            raw_text="Alex Rivera. Experienced ML Engineer with Python, TensorFlow, Scikit-Learn."
        )

        # Update candidate with structured profile
        parsed_sections = {
            "name": "Alex Rivera",
            "skills": ["Python", "TensorFlow", "FastAPI"],
            "work_experience": [
                {
                    "company": "DeepData AI",
                    "role": "Machine Learning Engineer",
                    "duration": "2022 - Present",
                    "highlights": ["Trained computer vision models on 1M+ images."]
                }
            ],
            "projects": [
                {
                    "title": "Semantic Document Search",
                    "tech_stack": ["Python", "ChromaDB", "FastAPI"],
                    "description": "Built neural semantic search engine."
                }
            ]
        }

        update_candidate_analysis(
            candidate_id=cand_id,
            name="Alex Rivera",
            parsed_sections=safe_json_dumps(parsed_sections),
            extracted_skills=safe_json_dumps({
                "matched_must_haves": ["Python"],
                "missing_critical_skills": ["PyTorch", "LangChain"]
            }),
            evidence_items=safe_json_dumps([]),
            noise_signals=safe_json_dumps({"noise_risk_level": "LOW", "flags": []}),
            match_score=78.5,
            match_tier="Strong Shortlist"
        )

        # 3. Call endpoint
        response = self.client.post(f"/api/candidate/{cand_id}/generate-interview")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        questions = data.get("questions")
        self.assertEqual(len(questions), 5)

        # 4. Verify SQLite database persistence
        cand_row = get_candidate_by_id(cand_id)
        saved_questions = safe_json_loads(cand_row.get("interview_questions"), [])
        self.assertEqual(len(saved_questions), 5)
        self.assertEqual(saved_questions[0]["category"], "Technical")
        self.assertEqual(saved_questions[1]["category"], "Project-based")
        self.assertEqual(saved_questions[2]["category"], "Experience-based")
        self.assertEqual(saved_questions[3]["category"], "Problem-solving")
        self.assertEqual(saved_questions[4]["category"], "Role-specific")

        print("\n[OK] POST /api/candidate/<id>/generate-interview endpoint & SQLite persistence verified!")


if __name__ == "__main__":
    unittest.main()
