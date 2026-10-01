import os
import json
import uuid
import re
from typing import Any, Optional
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'text'}


def allowed_file(filename: str) -> bool:
    """Check if uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage, target_folder: str) -> tuple[str, str]:
    """
    Safely save an uploaded file with a unique prefix to avoid collision.
    Returns: (saved_file_path, original_filename)
    """
    os.makedirs(target_folder, exist_ok=True)
    original_name = secure_filename(file_storage.filename) or "uploaded_document"
    unique_prefix = uuid.uuid4().hex[:8]
    saved_filename = f"{unique_prefix}_{original_name}"
    file_path = os.path.join(target_folder, saved_filename)
    file_storage.save(file_path)
    return file_path, original_name


def safe_json_loads(data: Any, default: Any = None) -> Any:
    """Safely parse JSON string into Python object."""
    if data is None:
        return default if default is not None else {}
    if isinstance(data, (dict, list)):
        return data
    try:
        return json.loads(data)
    except Exception:
        return default if default is not None else {}


def safe_json_dumps(data: Any) -> str:
    """Safely convert Python object to JSON string."""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"


def calculate_match_tier(score: float) -> str:
    """Categorize score into standard recruitment intelligence tiers."""
    if score >= 80:
        return "Strong Shortlist"
    elif score >= 65:
        return "Potential Match"
    elif score >= 50:
        return "Needs Review"
    else:
        return "Low Relevance"


def extract_candidate_name_fallback(filename: str, text: str) -> str:
    """
    Heuristic fallback to extract candidate name from file name or first lines of text
    before Gemini AI processing runs.
    """
    # Try cleaning filename: e.g. "John_Doe_Resume.pdf" -> "John Doe"
    base = os.path.splitext(filename)[0]
    base = re.sub(r'[\-_]', ' ', base)
    base = re.sub(r'(?i)\b(resume|cv|curriculum|vitae|profile|final|updated|202\d|v\d+)\b', '', base).strip()
    if len(base) > 2 and not base.isdigit():
        return base.title()

    # Otherwise inspect first non-empty lines
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if lines:
        first_line = lines[0]
        # If first line looks like a name (2-4 words, no numbers, not too long)
        if 2 <= len(first_line.split()) <= 4 and len(first_line) < 40 and not re.search(r'[\d@:/\\]', first_line):
            return first_line.title()

    return "Candidate " + uuid.uuid4().hex[:4].upper()
