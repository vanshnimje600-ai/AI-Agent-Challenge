import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recruitment.db")


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with dict-like row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables and indexes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Jobs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            file_name TEXT,
            file_path TEXT,
            raw_text TEXT NOT NULL,
            extracted_requirements TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Candidates Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            file_name TEXT NOT NULL,
            file_path TEXT,
            raw_text TEXT NOT NULL,
            parsed_sections TEXT,
            extracted_skills TEXT,
            evidence_items TEXT,
            noise_signals TEXT,
            match_score REAL DEFAULT 0.0,
            score_breakdown TEXT,
            match_tier TEXT DEFAULT 'Uploaded',
            executive_summary TEXT,
            interview_questions TEXT,
            analysis_status TEXT DEFAULT 'uploaded',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def insert_job(title: str, company: str, file_name: Optional[str], file_path: Optional[str], raw_text: str, extracted_requirements: Optional[str] = None) -> int:
    """Insert a new job description and return its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (title, company, file_name, file_path, raw_text, extracted_requirements)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, company, file_name, file_path, raw_text, extracted_requirements))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a job by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_job_requirements(job_id: int, extracted_requirements_json: str, title: Optional[str] = None):
    """Update extracted JD requirements in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if title:
        cursor.execute("""
            UPDATE jobs SET extracted_requirements = ?, title = ? WHERE id = ?
        """, (extracted_requirements_json, title, job_id))
    else:
        cursor.execute("""
            UPDATE jobs SET extracted_requirements = ? WHERE id = ?
        """, (extracted_requirements_json, job_id))
    conn.commit()
    conn.close()


def insert_candidate(job_id: int, name: str, file_name: str, file_path: str, raw_text: str) -> int:
    """Insert a parsed candidate resume."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO candidates (job_id, name, file_name, file_path, raw_text, analysis_status, match_tier)
        VALUES (?, ?, ?, ?, ?, 'uploaded', 'Uploaded')
    """, (job_id, name, file_name, file_path, raw_text))
    candidate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return candidate_id


def get_candidates_by_job(job_id: int) -> List[Dict[str, Any]]:
    """Retrieve all candidates for a specific job, sorted by match score desc."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM candidates 
        WHERE job_id = ? 
        ORDER BY match_score DESC, id ASC
    """, (job_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_candidate_by_id(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve candidate details by candidate ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_candidate_analysis(
    candidate_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    parsed_sections: Optional[str] = None,
    extracted_skills: Optional[str] = None,
    evidence_items: Optional[str] = None,
    noise_signals: Optional[str] = None,
    match_score: float = 0.0,
    score_breakdown: Optional[str] = None,
    match_tier: str = 'Completed',
    executive_summary: Optional[str] = None,
    interview_questions: Optional[str] = None,
    analysis_status: str = 'completed',
    error_message: Optional[str] = None
):
    """Save full multi-agent analysis results for a candidate."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE candidates SET
            name = COALESCE(?, name),
            email = COALESCE(?, email),
            phone = COALESCE(?, phone),
            parsed_sections = COALESCE(?, parsed_sections),
            extracted_skills = COALESCE(?, extracted_skills),
            evidence_items = COALESCE(?, evidence_items),
            noise_signals = COALESCE(?, noise_signals),
            match_score = ?,
            score_breakdown = COALESCE(?, score_breakdown),
            match_tier = ?,
            executive_summary = COALESCE(?, executive_summary),
            interview_questions = COALESCE(?, interview_questions),
            analysis_status = ?,
            error_message = ?
        WHERE id = ?
    """, (
        name, email, phone, parsed_sections, extracted_skills,
        evidence_items, noise_signals, match_score, score_breakdown,
        match_tier, executive_summary, interview_questions, analysis_status,
        error_message, candidate_id
    ))
    conn.commit()
    conn.close()


def get_all_jobs() -> List[Dict[str, Any]]:
    """Retrieve all jobs with candidate counts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.*, COUNT(c.id) as candidate_count,
               AVG(CASE WHEN c.analysis_status = 'completed' THEN c.match_score ELSE NULL END) as avg_score
        FROM jobs j
        LEFT JOIN candidates c ON j.id = c.job_id
        GROUP BY j.id
        ORDER BY j.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
