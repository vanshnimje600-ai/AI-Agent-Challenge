import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database.database import (
    init_db,
    insert_job,
    get_job_by_id,
    update_job_requirements,
    insert_candidate,
    get_candidates_by_job,
    get_candidate_by_id,
    update_candidate_analysis,
    get_all_jobs
)
from utils.file_parser import parse_document
from utils.helpers import (
    allowed_file,
    save_uploaded_file,
    safe_json_loads,
    safe_json_dumps,
    calculate_match_tier,
    extract_candidate_name_fallback
)
from agents.jd_agent import JDAgent
from agents.resume_agent import ResumeAgent
from agents.skill_agent import SkillAgent
from agents.evidence_agent import EvidenceAgent
from agents.matching_agent import MatchingAgent
from agents.noise_agent import NoiseAgent
from agents.shortlist_agent import ShortlistAgent
from utils.gemini_service import GeminiService

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "recruitment-intelligence-secret-dev-key")
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max upload payload

# Ensure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SQLite database
init_db()


def is_gemini_configured() -> bool:
    """Check if Gemini API key is configured."""
    return GeminiService.is_configured()


@app.context_processor
def inject_global_vars():
    """Inject global context variables into templates."""
    return {
        "gemini_active": is_gemini_configured()
    }


# ==========================================
# WEB PAGE ROUTES
# ==========================================

@app.route("/")
def index():
    """Homepage: Job upload, Resume upload, and recent shortlists."""
    recent_jobs = get_all_jobs()
    return render_template("index.html", recent_jobs=recent_jobs[:5])


@app.route("/dashboard/<int:job_id>")
def dashboard(job_id: int):
    """Shortlist Intelligence Dashboard for a specific job."""
    job = get_job_by_id(job_id)
    if not job:
        return redirect(url_for("index"))

    raw_candidates = get_candidates_by_job(job_id)
    jd_data = safe_json_loads(job.get("extracted_requirements"), {})

    candidates = []
    noise_flagged_count = 0

    for c in raw_candidates:
        cand_dict = dict(c)
        cand_dict["skills_data"] = safe_json_loads(c.get("extracted_skills"), {})
        cand_dict["noise_data"] = safe_json_loads(c.get("noise_signals"), {})
        cand_dict["evidence_data"] = safe_json_loads(c.get("evidence_items"), [])
        cand_dict["evidence_count"] = len(cand_dict["evidence_data"])
        cand_dict["verified_evidence_count"] = sum(
            1 for e in cand_dict["evidence_data"] if e.get("status") == "VERIFIED"
        )

        if cand_dict["noise_data"] and cand_dict["noise_data"].get("noise_risk_level") in ["MEDIUM", "HIGH"]:
            noise_flagged_count += 1

        candidates.append(cand_dict)

    return render_template(
        "dashboard.html",
        job=job,
        jd_data=jd_data,
        candidates=candidates,
        noise_flagged_count=noise_flagged_count
    )


@app.route("/candidate/<int:candidate_id>")
def candidate_detail(candidate_id: int):
    """Explainable Candidate Dossier deep-dive page."""
    candidate = get_candidate_by_id(candidate_id)
    if not candidate:
        return redirect(url_for("index"))

    job = get_job_by_id(candidate["job_id"])
    
    parsed_sections = safe_json_loads(candidate.get("parsed_sections"), {})
    skills_data = safe_json_loads(candidate.get("extracted_skills"), {})
    evidence_items = safe_json_loads(candidate.get("evidence_items"), [])
    noise_data = safe_json_loads(candidate.get("noise_signals"), {})
    score_breakdown = safe_json_loads(candidate.get("score_breakdown"), {})
    interview_questions = safe_json_loads(candidate.get("interview_questions"), [])

    # Extract structured explainability fields from score_breakdown or verdict
    dossier = {
        "strengths": score_breakdown.get("strengths", score_breakdown.get("top_strengths", [])),
        "missing_requirements": score_breakdown.get("missing_requirements", []),
        "uncertain_requirements": score_breakdown.get("uncertain_requirements", score_breakdown.get("gaps_and_concerns", [])),
        "explanation": score_breakdown.get("explanation", candidate.get("executive_summary", "")),
        "evidence_highlights": score_breakdown.get("evidence_highlights", [])
    }
    
    if not dossier["strengths"] and skills_data.get("matched_must_haves"):
        dossier["strengths"] = [
            f"Demonstrated proficiency in {skill}" for skill in skills_data.get("matched_must_haves", [])[:3]
        ]
    if not dossier["missing_requirements"] and skills_data.get("missing_critical_skills"):
        dossier["missing_requirements"] = [
            f"{skill} — Not found in candidate resume" for skill in skills_data.get("missing_critical_skills", [])
        ]

    return render_template(
        "candidate.html",
        candidate=candidate,
        job=job,
        parsed_sections=parsed_sections,
        skills_data=skills_data,
        evidence_items=evidence_items,
        noise_data=noise_data,
        score_breakdown=score_breakdown,
        interview_questions=interview_questions,
        dossier=dossier
    )


# ==========================================
# API ENDPOINTS (UPLOAD & MULTI-AGENT PIPELINE)
# ==========================================

@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Handle uploading Job Description and multiple Candidate Resumes.
    Parses document texts safely and records them in SQLite.
    """
    try:
        title = request.form.get("title", "").strip()
        job_text = request.form.get("job_text", "").strip()
        jd_file = request.files.get("jd_file")
        resume_files = request.files.getlist("resumes")

        jd_saved_path = None
        jd_file_name = None

        # 1. Parse Job Description
        if jd_file and jd_file.filename:
            if not allowed_file(jd_file.filename):
                return jsonify({"success": False, "error": f"Invalid JD file type: {jd_file.filename}"}), 400
            jd_saved_path, jd_file_name = save_uploaded_file(jd_file, app.config['UPLOAD_FOLDER'])
            parsed_jd_text, _ = parse_document(jd_saved_path)
            
            # Validate document text sufficiency
            is_valid, err_msg = GeminiService.validate_document_text(parsed_jd_text, f"Job Description ({jd_file_name})")
            if not is_valid:
                return jsonify({"success": False, "error": err_msg}), 400
                
            if not job_text:
                job_text = parsed_jd_text
            else:
                job_text = job_text + "\n\n" + parsed_jd_text

        if not job_text:
            return jsonify({"success": False, "error": "Job description content is required."}), 400

        # Validate job text sufficiency if pasted
        is_valid, err_msg = GeminiService.validate_document_text(job_text, "Job Description")
        if not is_valid:
            return jsonify({"success": False, "error": err_msg}), 400

        if not title:
            first_line = job_text.strip().split('\n')[0][:50]
            title = first_line if first_line else "Software Engineering Position"

        # Insert Job Record
        job_id = insert_job(
            title=title,
            company="Hiring Team",
            file_name=jd_file_name,
            file_path=jd_saved_path,
            raw_text=job_text
        )

        # 2. Process and parse Candidate Resumes
        saved_candidates_count = 0
        for r_file in resume_files:
            if r_file and r_file.filename:
                if not allowed_file(r_file.filename):
                    continue
                r_saved_path, r_original_name = save_uploaded_file(r_file, app.config['UPLOAD_FOLDER'])
                try:
                    parsed_resume_text, _ = parse_document(r_saved_path)
                except Exception as e:
                    return jsonify({"success": False, "error": f"Error parsing '{r_original_name}': {str(e)}"}), 400

                # Validate resume text content length
                is_valid, err_msg = GeminiService.validate_document_text(parsed_resume_text, f"Resume '{r_original_name}'")
                if not is_valid:
                    return jsonify({"success": False, "error": err_msg}), 400

                initial_name = extract_candidate_name_fallback(r_original_name, parsed_resume_text)
                insert_candidate(
                    job_id=job_id,
                    name=initial_name,
                    file_name=r_original_name,
                    file_path=r_saved_path,
                    raw_text=parsed_resume_text
                )
                saved_candidates_count += 1

        if saved_candidates_count == 0:
            return jsonify({"success": False, "error": "No valid resume documents were uploaded."}), 400

        return jsonify({
            "success": True,
            "job_id": job_id,
            "candidates_count": saved_candidates_count
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze/<int:job_id>", methods=["POST"])
def api_analyze(job_id: int):
    """
    Orchestrate the multi-agent AI pipeline for the given job and candidate resumes.
    """
    try:
        job = get_job_by_id(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404

        # 1. Run JDAgent to decompose requirements
        jd_data = JDAgent.analyze(job["raw_text"])
        update_job_requirements(
            job_id=job_id,
            extracted_requirements_json=safe_json_dumps(jd_data),
            title=jd_data.get("title", job["title"])
        )

        candidates = get_candidates_by_job(job_id)
        processed_count = 0

        # 2. Process each candidate through specialized agent stages
        for c in candidates:
            cand_id = c["id"]
            raw_resume = c["raw_text"]
            file_name = c["file_name"]

            # Step A: Resume Agent Structuring
            parsed_profile = ResumeAgent.parse_resume(raw_resume, file_name)
            candidate_name = parsed_profile.get("name") or c["name"]
            candidate_email = parsed_profile.get("email") or "N/A"
            candidate_phone = parsed_profile.get("phone") or "N/A"
            work_exp = parsed_profile.get("work_experience", [])
            projects = parsed_profile.get("projects", [])
            cand_skills = parsed_profile.get("skills", [])

            # Step B: Skill Normalization & Gap Analysis Agent
            must_haves = jd_data.get("must_have_skills", [])
            nice_to_haves = jd_data.get("nice_to_have_skills", [])
            skill_analysis = SkillAgent.analyze_skills(cand_skills, must_haves, nice_to_haves)

            # Step C: Verifiable Evidence Extraction Agent
            evidence_items = EvidenceAgent.extract_evidence(
                jd_requirements=must_haves,
                work_experience=work_exp,
                projects=projects,
                resume_raw_text=raw_resume
            )

            # Step D: Keyword Stuffing & Anti-Noise Detection Agent
            noise_analysis = NoiseAgent.detect_noise(
                resume_text=raw_resume,
                candidate_skills=cand_skills,
                work_experience=work_exp,
                projects=projects
            )

            # Step E: Multi-Factor Matching & Scoring Agent
            match_result = MatchingAgent.calculate_match(
                jd_data=jd_data,
                candidate_data=parsed_profile,
                skill_analysis=skill_analysis,
                evidence_items=evidence_items,
                noise_analysis=noise_analysis
            )

            # Step F: Shortlist & Targeted Interview Question Agent
            verdict = ShortlistAgent.generate_verdict(
                candidate_data=parsed_profile,
                jd_data=jd_data,
                skill_analysis=skill_analysis,
                evidence_items=evidence_items,
                noise_analysis=noise_analysis,
                match_result=match_result
            )

            # Save full intelligence dossier to SQLite
            score_breakdown_full = match_result.get("breakdown", {})
            score_breakdown_full["strengths"] = verdict.get("strengths", [])
            score_breakdown_full["missing_requirements"] = verdict.get("missing_requirements", [])
            score_breakdown_full["uncertain_requirements"] = verdict.get("uncertain_requirements", [])
            score_breakdown_full["evidence_highlights"] = verdict.get("evidence_highlights", [])
            score_breakdown_full["explanation"] = verdict.get("explanation", "")
            score_breakdown_full["match_percentage"] = match_result.get("match_percentage", 0.0)
            score_breakdown_full["recommendation"] = match_result.get("recommendation", "Needs Review")

            update_candidate_analysis(
                candidate_id=cand_id,
                name=candidate_name,
                email=candidate_email,
                phone=candidate_phone,
                parsed_sections=safe_json_dumps(parsed_profile),
                extracted_skills=safe_json_dumps(skill_analysis),
                evidence_items=safe_json_dumps(evidence_items),
                noise_signals=safe_json_dumps(noise_analysis),
                match_score=match_result.get("match_percentage", match_result.get("final_score", 0.0)),
                score_breakdown=safe_json_dumps(score_breakdown_full),
                match_tier=match_result.get("recommendation", match_result.get("match_tier", "Completed")),
                executive_summary=verdict.get("explanation", verdict.get("executive_summary", "")),
                interview_questions=safe_json_dumps(verdict.get("interview_questions", [])),
                analysis_status="completed"
            )
            processed_count += 1

        return jsonify({
            "success": True,
            "processed_candidates": processed_count,
            "job_id": job_id
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/job/<int:job_id>/export")
def export_job_shortlist(job_id: int):
    """Export complete shortlist dossier in structured JSON format."""
    job = get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    candidates = get_candidates_by_job(job_id)
    export_payload = {
        "job_id": job["id"],
        "job_title": job["title"],
        "created_at": job["created_at"],
        "requirements": safe_json_loads(job.get("extracted_requirements")),
        "candidates": []
    }

    for c in candidates:
        export_payload["candidates"].append({
            "rank": len(export_payload["candidates"]) + 1,
            "name": c["name"],
            "email": c["email"],
            "phone": c["phone"],
            "match_score": c["match_score"],
            "match_tier": c["match_tier"],
            "executive_summary": c["executive_summary"],
            "skills": safe_json_loads(c.get("extracted_skills")),
            "evidence": safe_json_loads(c.get("evidence_items")),
            "noise_analysis": safe_json_loads(c.get("noise_signals")),
            "score_breakdown": safe_json_loads(c.get("score_breakdown")),
            "interview_questions": safe_json_loads(c.get("interview_questions"))
        })

    return jsonify(export_payload)


@app.route("/api/test-gemini")
def api_test_gemini():
    """Endpoint to run live Gemini API test."""
    result = GeminiService.test_connection()
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@app.route("/api/health")
def api_health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "gemini_api_configured": is_gemini_configured(),
        "database": "connected"
    })


# ==========================================
# MAIN ENTRY POINT
# ==========================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"[*] Starting AI Recruitment Intelligence Agent on http://127.0.0.1:{port}")
    print(f"[*] Gemini AI Connected: {is_gemini_configured()}")
    app.run(host="0.0.0.0", port=port, debug=True)
