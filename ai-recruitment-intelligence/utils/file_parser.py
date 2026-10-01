import os
import re
from typing import Tuple, Dict, Any

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None


def clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    if not text:
        return ""
    # Replace non-breaking spaces and other oddities
    text = text.replace('\xa0', ' ').replace('\r\n', '\n').replace('\r', '\n')
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def parse_pdf(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Safely extract text and metadata from a PDF file using pypdf.
    """
    if not pypdf:
        raise ImportError("pypdf is not installed. Please run pip install pypdf")

    extracted_pages = []
    metadata = {"page_count": 0, "file_type": "PDF"}

    try:
        reader = pypdf.PdfReader(file_path)
        metadata["page_count"] = len(reader.pages)

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(page_text.strip())

        full_text = "\n\n".join(extracted_pages)
        return clean_text(full_text), metadata
    except Exception as e:
        raise RuntimeError(f"Error parsing PDF '{os.path.basename(file_path)}': {str(e)}")


def parse_docx(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Safely extract text from a DOCX document including paragraphs and tables.
    """
    if not docx:
        raise ImportError("python-docx is not installed. Please run pip install python-docx")

    try:
        doc = docx.Document(file_path)
        extracted_elements = []

        # Read paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                extracted_elements.append(para.text.strip())

        # Read tables (often used in resumes for skills/contact info)
        for table in doc.tables:
            for row in table.rows:
                row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_texts:
                    extracted_elements.append(" | ".join(row_texts))

        full_text = "\n".join(extracted_elements)
        metadata = {
            "paragraph_count": len(doc.paragraphs),
            "table_count": len(doc.tables),
            "file_type": "DOCX"
        }
        return clean_text(full_text), metadata
    except Exception as e:
        raise RuntimeError(f"Error parsing DOCX '{os.path.basename(file_path)}': {str(e)}")


def parse_txt(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Read plain text files with automatic encoding fallbacks.
    """
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                text = f.read()
            return clean_text(text), {"file_type": "TXT", "encoding": enc}
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Could not decode text file with standard encodings: {file_path}")


def parse_document(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Dispatch file parser based on extension.
    Supported: .pdf, .docx, .doc (handled or flagged), .txt
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        return parse_pdf(file_path)
    elif ext in ['.docx']:
        return parse_docx(file_path)
    elif ext in ['.txt', '.text', '.md']:
        return parse_txt(file_path)
    elif ext == '.doc':
        raise ValueError("Legacy .doc format is not directly supported. Please convert to .docx or .pdf.")
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Please upload PDF, DOCX, or TXT files.")
