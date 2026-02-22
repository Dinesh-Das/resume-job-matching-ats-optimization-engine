# Resume-Job Matching & ATS Optimization Engine

A production-grade platform that evaluates how well a resume matches a job description and outputs a structured match score with actionable optimization feedback. The system simulates ATS screening behavior, performs semantic comparison, and generates improvement recommendations.

---

## System Architecture

```
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
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Endpoints:                                            │   │
│  │  POST /api/quick-match      → 1:1 JD vs Resume       │   │
│  │  POST /api/train-model      → Corpus training         │   │
│  │  POST /api/run-pipeline     → Corpus-based scoring    │   │
│  │  POST /api/upload-resume    → File parsing            │   │
│  │  POST /api/oracle-connect   → Database integration    │   │
│  │  GET  /api/model-status     → Training readiness      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────┬───────────┬──────────┬──────────┬──────────┐  │
│  │ Document │   Text    │  Skill   │  ATS     │Composite │  │
│  │ Parser   │ Processor │Extractor │Simulator │ Scorer   │  │
│  └──────────┴───────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────┬───────────┬──────────┬──────────┬──────────┐  │
│  │  Gap     │  Recom-   │  Report  │ Skill    │ Resource │  │
│  │ Analyzer │ mendation │Generator │  Intel   │ Monitor  │  │
│  └──────────┴───────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Module Descriptions

| Module | File | Purpose |
|---|---|---|
| Document Parser | `resume_parser.py` | Extracts text from PDF, DOCX, TXT files |
| Text Processor | `text_processor.py` | NLP pipeline: tokenization, lemmatization, synonym mapping, stopword removal |
| Skill Extractor | `skill_extractor.py` | Dictionary-based skill detection with regex pattern matching |
| Vectorizer | `vectorizer.py` | TF-IDF vectorization of job/resume text |
| Matching Engine | `matching_engine.py` | Cosine similarity computation with optional GPU acceleration |
| ATS Simulator | `ats_simulator.py` | Evaluates resume machine readability, detects formatting issues |
| Composite Scorer | `composite_scorer.py` | 5-component weighted match score (keyword, skill, title, experience, ATS) |
| Gap Analyzer | `gap_analyzer.py` | Identifies missing skills classified by priority |
| Recommendation Engine | `recommendation_engine.py` | Generates actionable resume improvement suggestions |
| Report Generator | `report_generator.py` | Exports results to CSV, Excel, JSON |
| Skill Intelligence | `skill_intelligence.py` | Frequency analysis, co-occurrence, role clustering |
| Resource Monitor | `resource_monitor.py` | RAM usage monitoring with 30GB hard cap |
| Logging Config | `logging_config.py` | Rich console logging with progress bars |
| Config | `config.py` | Centralized constants, dictionaries, weights |
| Server | `server.py` | FastAPI application with all REST endpoints |

---

## Data Schema

### Input Schema

```
Resume:  PDF / DOCX / TXT file  →  plain text
JD:      Plain text or file     →  plain text
```

### Output Schema (Quick Match)

```json
{
  "overall_match_score": 73.2,
  "component_scores": {
    "keyword_similarity": 82.1,
    "skill_coverage": 68.0,
    "job_title_alignment": 75.3,
    "experience_relevance": 70.0,
    "ats_parseability": 90.0
  },
  "matched_keywords": ["python", "react", "docker"],
  "missing_keywords": ["kubernetes", "terraform"],
  "inferred_skills": ["data analysis"],
  "formatting_issues": [
    {
      "issue": "Multi-column layout detected",
      "severity": "high",
      "detail": "Most ATS systems read left-to-right..."
    }
  ],
  "recommendations": [
    {
      "skill": "kubernetes",
      "priority": "critical",
      "section": "Experience Section",
      "suggestion": "Add a bullet point under a relevant role...",
      "action": "Demonstrate kubernetes with a measurable achievement"
    }
  ],
  "parsing_confidence": 0.9
}
```

### Training Data Schema (Corpus Mode)

```json
[
  {
    "Job_ID": "JD-001",
    "Title": "Senior Software Engineer",
    "Summary": "...",
    "Responsibilities": "...",
    "Qualifications": "...",
    "Skills": "...",
    "Experience": "..."
  }
]
```

---

## Scoring Algorithm

### Composite Score Formula

```
overall_score = w1 × keyword_similarity
              + w2 × skill_coverage
              + w3 × title_alignment
              + w4 × experience_relevance
              + w5 × ats_parseability
              - penalty(missing_critical_skills)
```

### Default Weights

| Component | Weight | Method |
|---|---|---|
| Keyword Similarity | 0.30 | TF-IDF cosine similarity between resume and JD |
| Skill Coverage | 0.25 | Fraction of JD skills found in resume |
| Title Alignment | 0.15 | TF-IDF cosine sim of JD title vs resume excerpt |
| Experience Relevance | 0.15 | Years of experience vs JD requirement |
| ATS Parseability | 0.15 | 100 minus formatting penalties |

### Normalization

All component scores are normalized to 0–1 before weighting, then scaled to 0–100.

### Critical Skill Penalty

If any of the top 5 JD skills are missing from the resume, a penalty of up to 10% is applied.

---

## Model Training Strategy

### Corpus Mode

1. **Data Ingestion**: Load jobs from JSON (or Oracle DB), combine text fields, deduplicate
2. **Text Processing**: Clean → synonym mapping → spaCy lemmatization → domain stopword removal (18 parallel workers)
3. **Skill Extraction**: Dictionary-based regex matching across all jobs (18 parallel workers)
4. **TF-IDF Vectorization**: Fit on entire corpus (up to 10,000 features, (1,2)-grams)
5. **Skill Intelligence**: Frequency tables, TF-IDF statistical extraction, importance weighting
6. **Clustering**: KMeans on TF-IDF matrix, role cluster summaries
7. **Model Persistence**: Save vectorizer + matrix + metadata via joblib

### Quick Match Mode

No pre-training required. Creates a temporary TF-IDF vectorizer on-the-fly for the resume+JD pair.

---

## Evaluation Framework

| Metric | Method |
|---|---|
| Keyword coverage accuracy | Precision/recall of extracted skills vs manual labels |
| ATS parsing confidence | Rule-based scoring validated against known-good/bad resumes |
| Score correlation | Composite score compared against recruiter judgment (labeled pairs) |
| Recommendation quality | Priority classification accuracy (critical/recommended/optional) |
| Performance | Analysis latency per resume (target: < 5s) |

---

## API Specification

### `POST /api/quick-match`
**Direct 1:1 resume vs JD comparison (no pre-training required)**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `resume_text` | form string | Yes | Resume text content |
| `jd_text` | form string | Yes | Job description text |
| `jd_title` | form string | No | Target job title |

**Response**: Full output schema (see above)

---

### `POST /api/upload-resume`
**Parse a resume/JD file into plain text**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file` | file upload | Yes | PDF, DOCX, or TXT file |

**Response**: `{ "text": "...", "filename": "...", "characters": 1234 }`

---

### `POST /api/train-model`
**Train on a job corpus for corpus-based matching**

No parameters. Requires `data/jobs.json` to exist.

**Response**: `{ "status": "ok", "message": "Successfully trained..." }`

---

### `POST /api/run-pipeline`
**Score a resume against the trained corpus**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `resume_text` | form string | Yes | Resume text content |

**Response**: Score summary, gap analysis, recommendations, skill frequency data

---

### `POST /api/oracle-connect`
**Connect to Oracle DB and fetch job data**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | form string | Yes | Oracle host |
| `port` | form int | Yes | Oracle port |
| `service_name` | form string | Yes | Oracle service |
| `user` | form string | Yes | DB username |
| `password` | form string | Yes | DB password |
| `table_name` | form string | Yes | Table to query |

**Response**: `{ "status": "ok", "text": "...", "length": 45231 }`

---

## Hardware Optimization

| Resource | Configuration |
|---|---|
| CPU (20 cores) | 18 parallel workers via `ProcessPoolExecutor` (centralized in `config.py`) |
| GPU (RTX 4060) | CuPy for cosine similarity; spaCy GPU acceleration |
| RAM (32 GB) | 30 GB hard limit enforced by `resource_monitor.py` with warnings at 80% |
| Batching | 2000-item chunks for text processing, skill extraction, and NLP pipeline |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- NVIDIA GPU with CUDA (optional, for GPU acceleration)

### Installation

```bash
# Backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Frontend
cd frontend
npm install
```

### Running

```bash
# Terminal 1: Backend
python server.py
# → Starts on http://localhost:8000

# Terminal 2: Frontend (dev)
cd frontend
npm run dev
# → Starts on http://localhost:5173 (proxied to backend)
```

### Usage Modes

1. **Quick Match** (`/match`): Paste resume + JD → instant multi-component match score
2. **Corpus Mode** (`/data` → `/dashboard`): Load job data → Train → Upload resume → Full analysis

---

## Example Output

### Quick Match Result

```
Overall Match Score: 73/100

Component Scores:
  Keyword Similarity:     82
  Skill Coverage:         68
  Title Alignment:        75
  Experience Relevance:   70
  ATS Parseability:       90

Matched Keywords: python, react, docker, sql, git
Missing Keywords: kubernetes, terraform, cicd

Recommendations:
  🔴 Critical: Add "kubernetes" to Experience Section
  🟡 Recommended: Add "terraform" to Experience Section
  🟢 Optional: Add "cicd" to Skills Section
```

### Console Logging (Training Pipeline)

```
[2026-02-22 09:30:01] ════════════════════════════════════════════════════════════
[2026-02-22 09:30:01]   TRAINING PIPELINE START
[2026-02-22 09:30:01] ════════════════════════════════════════════════════════════
[2026-02-22 09:30:01] 💾 Memory [pipeline start]: 2.1 GB / 30 GB
[2026-02-22 09:30:01] ── Stage 1/7: Data Ingestion ──
[2026-02-22 09:30:02] ✅ Loaded 45,231 unique jobs in 0.8s
[2026-02-22 09:30:02] ── Stage 2/7: Text Processing ──
[2026-02-22 09:30:02] 🧠 Text Processing — Stage 1/3: Clean + Synonyms (18 workers)
[2026-02-22 09:30:02] ┌── Clean + Synonyms ── starting (45,231 items)
[2026-02-22 09:30:04] │  [██████████████████░░░░░░░░░░░░] 60.0% (27,138/45,231) | 1.8s | 15,076 items/s | RAM: 4.2 GB
[2026-02-22 09:30:05] └── Clean + Synonyms ── done in 3.1s (45,231 items) | RAM: 4.8 GB
[2026-02-22 09:30:15] ── Stage 4/7: TF-IDF Vectorisation ──
[2026-02-22 09:30:16] ✅ TF-IDF fitted: 45,231 docs × 10,000 features in 1.2s
[2026-02-22 09:30:21] ════════════════════════════════════════════════════════════
[2026-02-22 09:30:21]   TRAINING PIPELINE COMPLETE
[2026-02-22 09:30:21] ════════════════════════════════════════════════════════════
[2026-02-22 09:30:21]    Total time: 19.8s
[2026-02-22 09:30:21]    Jobs processed: 45,231
[2026-02-22 09:30:21]    TF-IDF features: 10,000
[2026-02-22 09:30:21] 💾 Memory [pipeline end]: 12.1 GB / 30 GB
```
