# Resume-Job Matching & ATS Optimization Engine

A production-grade algorithmic and AI-powered platform that evaluates how well a resume matches a job description, simulating Enterprise Applicant Tracking Systems (ATS). It outputs a meticulously structured match score, skill gap analysis, and generates actionable, AI-driven optimization feedback.

---

## 🌟 Core ATS Engine Features

* **Dual-Pipeline Matching Engine:** Perform standard rigid keyword-matching (TF-IDF cosine similarity) paired with advanced Semantic NLP (HuggingFace Sentence Transformers) to understand the *meaning* of a resume.
* **Generative AI Reviewer:** Automated rewriting of weak resume bullets using strict Google Gemini 2.0 prompts to sound like a senior tech recruiter.
* **Strict Schema Validation:** Pydantic models automatically intercept and validate large-scale data imports (JSON/CSV) to prevent dataset corruption, surfacing structured error tracebacks directly in the UI.
* **Asynchronous Background Queues:** FastAPI BackgroundTasks process massive data loads (e.g., 1.5GB / 545,000 row Oracle databases) while the user interface polls for real-time progress, entirely eliminating HTTP timeout crashes.
* **Premium Antigravity UI:** A hardware-accelerated, glassmorphic React interface featuring native Dark Mode, animated particle physics backgrounds, glowing gradients, and zero-stutter transitions.
* **Intelligent Skill Extraction:** Dictionary-backed regex logic designed to detect and categorize over 150+ distinct hard skills dynamically.

---

## 🔄 Two Ways to Match (Workflows)

The engine provides two distinct workflows depending on whether you are analyzing a single job description or thousands at once:

### Workflow 1: Corpus Matching (Market Train & Match)
**Best for:** Discovering how your resume stacks up against the broader market for a specific role.

*Follow these steps in the application:*
1. **Load Data:** Navigate to the **`TRAIN ENGINE`** tab and connect your Oracle Database or upload a job CSV/JSON.
2. **Train Models:** Still on the **`TRAIN ENGINE`** tab, select a role (e.g., Software Engineer) and click "Train Specialized Engine".
3. **Upload Resume:** Navigate to the **`DASHBOARD`** tab and upload your resume.
4. **Check Score:** After the analysis completes, view your performance against the trained market dataset. Detailed metrics and AI reviews can additionally be viewed on the **`RESULTS`** tab.

### Workflow 2: 1:1 JD-Resume Matching (Direct Match)
**Best for:** Individuals tailoring their resume to a specific job application.

*Follow these steps in the application:*
1. **Upload Resume:** Navigate to the **`QUICK MATCH`** tab and upload or paste your resume.
2. **Paste JD:** Paste the exact Job Description target into the secondary window.
3. **Analyze:** Click "Analyze Match". The NLP engine creates an on-the-fly vectorizer without needing pre-training.
4. **Results:** Instantly receive your exact target scores on the same page. 

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  ┌──────────┬──────────┬───────────┬───────────┬──────────┐ │
│  │  Home    │  Quick   │   Data    │ Dashboard │  Export   │ │
│  │          │  Match   │  Source   │ Analysis  │          │ │
│  └──────────┴──────────┴───────────┴───────────┴──────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / REST
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend (server.py)                 │
│                                                              │
│  ┌──────────┬───────────┬──────────┬──────────┬──────────┐  │
│  │ Document │   Text    │  Skill   │  ATS     │ Semantic │  │
│  │ Parser   │ Processor │Extractor │Simulator │ Scorer   │  │
│  └──────────┴───────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────┬───────────┬──────────┬──────────┬──────────┐  │
│  │  Gap     │  Pydantic │ GenAI AI │ Fast API │ Oracle   │  │
│  │ Analyzer │ Validator │ Reviewer │ Bg Tasks │ Connect  │  │
│  └──────────┴───────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧮 Composite Scoring Algorithm

The ATS simulator scores a resume out of 100 based on five rigorously weighted, normalized variables:

| Component | Weight | Method |
|---|---|---|
| **Keyword Similarity** | 0.30 | TF-IDF cosine similarity and Semantic Transformer mapping |
| **Skill Coverage** | 0.25 | Mathematical fraction of required JD skills found in resume |
| **Title Alignment** | 0.15 | TF-IDF cosine sim of JD title vs resume header excerpt |
| **Experience Relevance** | 0.15 | Parsed years of experience vs required JD bounds |
| **ATS Parseability** | 0.15 | 100 minus formatting penalties (e.g., detected multi-column locks) |

*Note: If any of the top 5 most critical JD skills are missing, a heavy penalty of up to 10% is actively applied to simulate strict recruiters.*

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- NVIDIA GPU with CUDA (optional, dramatically speeds up training on large sets)
- **Tesseract-OCR / Poppler**: Required for fallback image-based resume extraction.

### Installation & Run

```bash
# 1. Start the FastAPI Engine
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python server.py
# → Runs on http://localhost:8000

# 2. Start the Antigravity UI
cd frontend
npm install
npm run dev
# → Runs on http://localhost:5173
```
