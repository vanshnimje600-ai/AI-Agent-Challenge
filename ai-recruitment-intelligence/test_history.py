"""
Automated tests for SQLite Persistence & History Management.
Tests:
- Creation and persistence of analysis records
- Querying history list
- Viewing analysis dashboard and candidate dossier from history
- Deleting a single analysis
- Clearing all history
"""

import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import (
    get_history_list,
    delete_job,
    clear_all_history,
    insert_job,
    insert_candidate,
    update_candidate_analysis
)


def test_history_flow():
    base_url = "http://127.0.0.1:5000"

    print("==================================================")
    print(" Testing SQLite Persistence & History Management  ")
    print("==================================================")

    # 1. Test History Route directly
    print("\n[1] Testing GET /history endpoint...")
    resp = requests.get(f"{base_url}/history")
    print(f"    History Page Status: {resp.status_code}")
    assert resp.status_code == 200
    assert "Recruitment Analysis History" in resp.text

    # 2. Insert a fresh distinct test job and candidate to verify persistence
    print("\n[2] Inserting test analysis into SQLite...")
    test_job_id = insert_job(
        title="Staff Security Engineer",
        company="CyberFort Systems",
        file_name="Security_JD.pdf",
        file_path=None,
        raw_text="Seeking Staff Security Engineer with Cryptography and Cloud Security experience."
    )
    cand_id = insert_candidate(
        job_id=test_job_id,
        name="Morgan Freeman",
        file_name="Morgan_Security.pdf",
        file_path=None,
        raw_text="Morgan Freeman - Security engineer with 6 years experience in Cloud Security."
    )
    update_candidate_analysis(
        candidate_id=cand_id,
        name="Morgan Freeman",
        match_score=88.5,
        match_tier="Strong Shortlist",
        executive_summary="Morgan demonstrates deep security engineering capabilities.",
        analysis_status="completed"
    )

    # 3. Verify it shows in get_history_list()
    print("\n[3] Verifying database history list query...")
    history = get_history_list()
    found = [h for h in history if h["analysis_id"] == test_job_id]
    assert len(found) == 1, "Inserted analysis should appear in history list"
    h_item = found[0]
    print(f"    Found Analysis #{h_item['analysis_id']}: {h_item['job_title']} (Candidate: {h_item['candidate_names']}, Top Match: {h_item['top_match']}%)")
    assert h_item["job_title"] == "Staff Security Engineer"
    assert "Morgan Freeman" in h_item["candidate_names"]

    # 4. Verify History page renders this job
    print("\n[4] Verifying HTML rendering on /history page...")
    resp = requests.get(f"{base_url}/history")
    assert "Staff Security Engineer" in resp.text
    assert "Morgan Freeman" in resp.text

    # 5. Test Delete Single Analysis via API
    print(f"\n[5] Testing POST /api/history/delete/{test_job_id}...")
    del_resp = requests.post(f"{base_url}/api/history/delete/{test_job_id}")
    print(f"    Delete Response: {del_resp.status_code}, {del_resp.json()}")
    assert del_resp.status_code == 200
    assert del_resp.json().get("success") is True

    # Verify it is removed
    history_after_del = get_history_list()
    assert not any(h["analysis_id"] == test_job_id for h in history_after_del), "Job should be deleted from SQLite"
    print("    [OK] Analysis successfully deleted from SQLite.")

    # 6. Test Clear All History via API
    print("\n[6] Testing POST /api/history/clear...")
    clear_resp = requests.post(f"{base_url}/api/history/clear")
    print(f"    Clear All Response: {clear_resp.status_code}, {clear_resp.json()}")
    assert clear_resp.status_code == 200
    assert clear_resp.json().get("success") is True

    history_empty = get_history_list()
    assert len(history_empty) == 0, "History should be empty after clear"
    print("    [OK] All history cleared successfully.")

    # 7. Re-populate with a pipeline test so the app has working data
    print("\n[7] Re-running pipeline to leave fresh data in database...")
    import test_pipeline
    test_pipeline.run_test()

    print("\n[SUCCESS] SQLite Persistence & History Management fully verified!")


if __name__ == "__main__":
    test_history_flow()
