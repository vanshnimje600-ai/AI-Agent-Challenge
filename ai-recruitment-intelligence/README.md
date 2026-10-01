# ⚡ AI Recruitment Intelligence Agent
> **"From Hundreds of Resumes to an Evidence-Backed Shortlist"**  
> A multi-agent recruitment intelligence platform designed to eliminate keyword stuffing, uncover genuine candidate capabilities, cross-verify resume claims with job requirements, and produce explainable hiring dossiers.

---

## 🌟 Key Highlights & Anti-Bias Architecture

Traditional Applicant Tracking Systems (ATS) rely on naive keyword matching. Candidates exploit this by stuffing buzzwords without actual experience, leading to high false positives.

**RecruitIntel AI** solves this with a specialized multi-agent architecture:
1. **📌 JD Decomposition Agent (`jd_agent.py`)**: Deconstructs job descriptions into must-haves, nice-to-haves, domain context, and experience requirements.
2. **📄 Resume Structuring Agent (`resume_agent.py`)**: Parses PDF, DOCX, and TXT files, extracting verified work history, projects, and accomplishments.
3. **🏷️ Skill Taxonomy & Normalization Agent (`skill_agent.py`)**: Normalizes variants (e.g., `React.js` -> `React`, `k8s` -> `Kubernetes`) and calculates true skill coverage.
4. **🔍 Evidence Cross-Verification Agent (`evidence_agent.py`)**: Quotes verifiable snippets directly from work experience to substantiate each job requirement.
5. **🛡️ Keyword Stuffing & Anti-Noise Agent (`noise_agent.py`)**: Flags skills listed in skill clouds that have zero supporting evidence or project citations.
6. **📊 Multi-Factor Explainable Matching Agent (`matching_agent.py`)**: Generates an evidence-backed score (0–100) with a transparent breakdown (no black boxes).
7. **🎯 Shortlist & Screening Agent (`shortlist_agent.py`)**: Generates executive shortlist summaries and generates tailored technical interview questions to probe unverified claims.

---

## 📂 Project Structure

```
ai-recruitment-intelligence/
│
├── app.py                     # Flask main server and API router
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── .env                       # Local environment variables
├── README.md                  # Documentation and setup guide
│
├── agents/                    # Multi-Agent Intelligence Engine
│   ├── __init__.py            # Gemini client & common LLM helpers
│   ├── jd_agent.py            # JD requirement extractor
│   ├── resume_agent.py        # Resume parser & section extractor
│   ├── skill_agent.py         # Skill normalizer & taxonomy mapper
│   ├── evidence_agent.py      # Verifiable proof & snippet extractor
│   ├── matching_agent.py      # Multi-factor explainable scorer
│   ├── noise_agent.py         # Anti-noise & keyword stuffing detector
│   └── shortlist_agent.py     # Executive synthesis & tailored interview questions
│
├── database/
│   └── database.py            # SQLite schema, queries, and persistence
│
├── utils/
│   ├── file_parser.py         # PDF (pypdf), DOCX (python-docx), and TXT parser
│   └── helpers.py             # File management, sanitization, and fallback helpers
│
├── uploads/                   # Uploaded resume & JD storage folder
│
├── templates/                 # Modern, responsive UI templates
│   ├── index.html             # Upload & job submission page
│   ├── dashboard.html         # Shortlist rankings & analytics dashboard
│   └── candidate.html         # Explainable candidate dossier deep-dive
│
└── static/
    ├── css/
    │   └── style.css          # Glassmorphism dark-mode responsive design system
    └── js/
        └── script.js          # Drag-and-drop uploader & async pipeline state
```

---

## 🚀 Getting Started (Windows Setup)

### 1. Prerequisites
- Python 3.10+ installed
- Pip package manager

### 2. Navigate to Project Directory
```powershell
cd "ai-recruitment-intelligence"
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Open `.env` and add your **Gemini API Key**:
```env
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
PORT=5000
```
> *Note: If you run without an API key, the system seamlessly operates in **Local Heuristic Mode** using rule-based taxonomy and regex extraction.*

### 5. Launch the Application
```powershell
python app.py
```
Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Testing the Pipeline

1. **Job Description**: Drag and drop any `.pdf` / `.docx` JD or paste text (e.g. *Senior Python Backend Engineer*).
2. **Candidate Resumes**: Select multiple candidate `.pdf` or `.docx` resumes.
3. Click **"Run Recruitment Intelligence Agents"**.
4. Watch the real-time agent progression modal.
5. Review the **Shortlist Dashboard** to see:
   - Rank and Score Tier (Strong Shortlist, Potential Match, Needs Review, Low Relevance).
   - Matched vs. Missing core skills.
   - Verified Evidence Snippets.
   - Keyword noise risk flags.
6. Click **"Full Dossier ➔"** on any candidate to inspect the evidence matrix, anti-noise analysis, and tailored interview probes.

---

## 🛠️ Technology Stack
- **Backend**: Python 3, Flask 3.0+
- **Database**: SQLite 3
- **AI / LLM**: Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`)
- **Document Parsers**: `pypdf`, `python-docx`
- **Frontend**: Modern Vanilla HTML5, CSS3 (Glassmorphic Dark UI), JavaScript ES6 (Async Fetch, Drag-and-Drop)
