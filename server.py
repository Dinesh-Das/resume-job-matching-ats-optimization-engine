"""
FastAPI Backend — Resume-Job Matching & ATS Optimization Engine
Wraps existing Python analysis modules and serves the React frontend.
"""

import os
import sys
import json
import tempfile
import logging
import multiprocessing
import pandas as pd
from pathlib import Path
from typing import Optional, List

# Silence joblib physical core warning on CPUs with P/E cores (like i7-14700HX)
os.environ["LOKY_MAX_CPU_COUNT"] = str(multiprocessing.cpu_count())

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    OUTPUT_DIR, JOBS_JSON_PATH, ORACLE_DEFAULTS, JOB_ROLES
)
from data_ingestion import ingest_jobs
from resume_parser import parse_resume, parse_resume_text
from text_processor import process, process_series
from skill_extractor import (
    extract_skills_from_text, extract_skills_from_jobs,
    extract_statistical_skills,
)
from vectorizer import fit_tfidf, transform_text
from matching_engine import compute_scores, score_summary
from skill_intelligence import (
    skill_frequency_table, skill_cooccurrence_matrix,
    cluster_roles, cluster_summary, compute_importance_weights,
)
from gap_analyzer import analyze_gaps, get_gap_summary
from recommendation_engine import generate_recommendations, generate_general_tips
from report_generator import generate_full_report, export_csv, export_json
from oracle_connector import fetch_and_save, get_jobs_json_metadata, save_jobs_paginated
from model_manager import save_model, load_model, is_model_trained
import task_manager

# ── Logging Setup (must be before any logger usage) ────
from logging_config import setup_logging, log_banner, log_stage
from resource_monitor import check_memory, log_memory, get_memory_usage_gb

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────
RESULTS_JSON = os.path.join(OUTPUT_DIR, "results.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Server application started and logging initialized.")
    yield

app = FastAPI(title="ATS Optimization Engine API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════

# ── Database ──────────────────────────────────

def run_connect_db_task(task_id: str, host: str, port: int, service_name: str, user: str, password: str, table_name: str):
    """Background task to fetch jobs from Oracle and build index without blocking the API."""
    try:
        def progress_cb(pct, msg):
            task_manager.update_task(task_id, progress=pct, message=msg)
            
        task_manager.update_task(task_id, status="running", message="Connecting to Oracle database...")
        
        count, path = fetch_and_save(
            host=host, port=port, service_name=service_name,
            user=user, password=password,
            output_path=JOBS_JSON_PATH, table_name=table_name,
            progress_callback=progress_cb
        )
        task_manager.update_task(task_id, progress=0.95, message="Building index files for fast searching...")
        
        # Build lightweight index files for fast Jobs Explorer serving
        import json as _json
        with open(JOBS_JSON_PATH, "r", encoding="utf-8") as _f:
            _d = _json.load(_f)
        _records = _d["jobs"] if isinstance(_d, dict) and "jobs" in _d else _d
        save_jobs_paginated(_records, os.path.dirname(JOBS_JSON_PATH))
        
        # Invalidate Explorer cache
        global GLOBAL_JOBS_CACHE, GLOBAL_JOBS_CACHE_MTIME
        GLOBAL_JOBS_CACHE = None
        GLOBAL_JOBS_CACHE_MTIME = 0
        
        task_manager.update_task(task_id, status="completed", progress=1.0, 
                                 message="Import complete!", result={"count": count, "path": path})
    except Exception as e:
        logger.error(f"DB Import Task {task_id} failed: {e}")
        task_manager.update_task(task_id, status="failed", error=str(e), message=f"Failed: {str(e)}")

@app.post("/api/connect-db")
async def connect_db(
    background_tasks: BackgroundTasks,
    host: str = Form(default="localhost"),
    port: int = Form(default=1521),
    service_name: str = Form(default="XE"),
    user: str = Form(default="system"),
    password: str = Form(default="system"),
    table_name: str = Form(default="JOBDETAILS"),
):
    """Start background fetch from Oracle, return task tracking ID instantly."""
    task_id = task_manager.create_task("Fetch from Oracle DB")
    background_tasks.add_task(
        run_connect_db_task, task_id, 
        host, int(port), service_name, user, password, table_name
    )
    return {"status": "accepted", "task_id": task_id}

@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Poll for background task progress and status."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/api/jobs-status")
async def jobs_status():
    """Check if jobs.json exists and return metadata."""
    if os.path.exists(JOBS_JSON_PATH):
        try:
            meta = get_jobs_json_metadata(JOBS_JSON_PATH)
            return {"exists": True, **meta}
        except Exception:
            return {"exists": True, "total_records": "unknown"}
    return {"exists": False}


# Index file path (lightweight display-only copy of jobs)
JOBS_INDEX_PATH = os.path.join(os.path.dirname(JOBS_JSON_PATH), "jobs_index.json")

# Cache for Jobs Explorer — uses the index file when available
GLOBAL_JOBS_CACHE = None
GLOBAL_JOBS_CACHE_MTIME = 0

@app.get("/api/jobs-data")
async def jobs_data(
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
):
    """Return paginated jobs using the lightweight index file (preferred) or full jobs.json."""
    global GLOBAL_JOBS_CACHE, GLOBAL_JOBS_CACHE_MTIME

    # Prefer the lightweight index if it exists (~40MB vs 1.5GB)
    source_path = JOBS_INDEX_PATH if os.path.exists(JOBS_INDEX_PATH) else JOBS_JSON_PATH

    if not os.path.exists(source_path) and not os.path.exists(JOBS_JSON_PATH):
        raise HTTPException(status_code=404, detail="No job data found. Fetch from DB or upload first.")

    if not os.path.exists(source_path):
        source_path = JOBS_JSON_PATH

    try:
        current_mtime = os.path.getmtime(source_path)
        if GLOBAL_JOBS_CACHE is None or current_mtime > GLOBAL_JOBS_CACHE_MTIME:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "jobs" in data:
                all_jobs = data["jobs"]
                metadata = data.get("metadata", {})
            elif isinstance(data, list):
                all_jobs = data
                metadata = {}
            else:
                all_jobs = []
                metadata = {}
            GLOBAL_JOBS_CACHE = {"jobs": all_jobs, "metadata": metadata}
            GLOBAL_JOBS_CACHE_MTIME = current_mtime

        all_jobs = GLOBAL_JOBS_CACHE["jobs"]
        metadata = GLOBAL_JOBS_CACHE["metadata"]

        # Server-side search
        if search:
            q = search.lower()
            all_jobs = [
                j for j in all_jobs
                if q in (j.get("title") or "").lower()
                or q in (j.get("company_name") or j.get("companyname") or "").lower()
                or q in (j.get("keyskills") or "").lower()
                or q in (j.get("location") or "").lower()
            ]

        total = len(all_jobs)
        start = page * page_size
        page_jobs = all_jobs[start:start + page_size]

        return {
            "jobs": page_jobs,
            "metadata": metadata,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sample-jobs-json")
async def sample_jobs_json():
    """Return a downloadable sample JSON showing the expected job data format."""
    sample = {
        "metadata": {
            "fetched_at": "2026-01-01T00:00:00",
            "total_records": 3,
            "source": "Sample — replace with your data"
        },
        "jobs": [
            {
                "title": "Software Engineer",
                "company_name": "Acme Corp",
                "location": "Bangalore, India",
                "experience": "2-5 Yrs",
                "salary": "8-14 LPA",
                "keyskills": "Java, Spring Boot, Microservices, REST API, Docker",
                "role": "Software / IT Engineer",
                "industry_type": "IT Services & Consulting",
                "employment_type": "Full Time, Permanent",
                "education": "B.Tech/B.E.",
                "posted": "2026-01-01",
                "url": "https://example.com/jobs/123",
                "jobdescription": "We are looking for a backend software engineer with experience in Java and Spring Boot to build scalable microservices."
            },
            {
                "title": "Data Scientist",
                "company_name": "DataViz Pvt Ltd",
                "location": "Hyderabad, India",
                "experience": "3-7 Yrs",
                "salary": "12-22 LPA",
                "keyskills": "Python, Machine Learning, TensorFlow, NLP, SQL",
                "role": "Data Science & Analytics",
                "industry_type": "Analytics / KPO / Research",
                "employment_type": "Full Time, Permanent",
                "education": "M.Tech/M.E., M.Sc.",
                "posted": "2026-01-02",
                "url": "https://example.com/jobs/456",
                "jobdescription": "Seeking a data scientist to build ML models and NLP pipelines for our analytics platform."
            },
            {
                "title": "DevOps Engineer",
                "company_name": "CloudSystems Ltd",
                "location": "Pune, India",
                "experience": "4-8 Yrs",
                "salary": "15-25 LPA",
                "keyskills": "AWS, Kubernetes, Docker, Terraform, CI/CD, Linux",
                "role": "DevOps / Infrastructure",
                "industry_type": "IT Services & Consulting",
                "employment_type": "Full Time, Permanent",
                "education": "B.Tech/B.E.",
                "posted": "2026-01-03",
                "url": "https://example.com/jobs/789",
                "jobdescription": "Looking for a DevOps engineer to manage cloud infrastructure, CI/CD pipelines and Kubernetes deployments."
            }
        ]
    }
    return JSONResponse(
        content=sample,
        headers={"Content-Disposition": "attachment; filename=sample_jobs.json"}
    )



# ── File Upload ───────────────────────────────

def run_upload_jobs_task(task_id: str, tmp_path: str):
    """Background task to ingest uploaded jobs files and save to disk."""
    try:
        task_manager.update_task(task_id, status="running", progress=0.2, message="Ingesting file and analyzing schema...")
        df = ingest_jobs(tmp_path)
        
        task_manager.update_task(task_id, progress=0.5, message=f"Parsed {len(df):,} rows. Validating and saving to disk...")
        records = df.to_dict("records")
        from oracle_connector import save_jobs_json
        
        save_jobs_json(records, JOBS_JSON_PATH)
        task_manager.update_task(task_id, progress=0.8, message="Building lightweight index for Jobs Explorer...")
        save_jobs_paginated(records, os.path.dirname(JOBS_JSON_PATH))
        
        # Invalidate Explorer cache
        global GLOBAL_JOBS_CACHE, GLOBAL_JOBS_CACHE_MTIME
        GLOBAL_JOBS_CACHE = None
        GLOBAL_JOBS_CACHE_MTIME = 0
        
        task_manager.update_task(task_id, status="completed", progress=1.0, 
                                 message="Upload processed successfully!", result={"count": len(df)})
    except Exception as e:
        logger.error(f"Upload Task {task_id} failed: {e}")
        task_manager.update_task(task_id, status="failed", error=str(e), message=f"Failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

@app.post("/api/upload-jobs")
async def upload_jobs(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a job dataset (CSV/JSON/Excel), start background ingestion, and return task tracking ID."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "json", "jsonl", "xlsx", "xls"):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    task_id = task_manager.create_task(f"Upload and process {file.filename}")
    background_tasks.add_task(run_upload_jobs_task, task_id, tmp_path)
    
    return {"status": "accepted", "task_id": task_id}


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Parse an uploaded resume/JD file (PDF, DOCX, TXT) into plain text."""
    try:
        content = await file.read()
        text = parse_resume_text(content, filename=file.filename)
        
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file.")

        logger.info(f"Parsed uploaded file: {file.filename} ({len(text)} chars)")
        return {"text": text, "filename": file.filename, "characters": len(text)}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"File parse error: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parse-advanced")
async def parse_advanced(file: UploadFile = File(...)):
    """
    Advanced Parse: Multi-stage fault-tolerant pipeline.
    Extracts text, repairs layout, segments sections, extracts entities,
    and returns a fully structured JSON payload with confidence scores,
    traceability, and anomaly reporting.
    """
    try:
        content = await file.read()

        # 1. Full pipeline extraction (returns ParseResult with bounding boxes, anomalies, etc.)
        parse_result = parse_resume(content, filename=file.filename)

        cleaned_text = parse_result.cleaned_text or parse_result.raw_text
        if not cleaned_text or not cleaned_text.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text. Anomalies: {parse_result.anomalies}"
            )

        # 2. Build fully structured resume schema with validation & reprocessing
        from entity_extractor import build_structured_resume
        structured_data = build_structured_resume(
            resume_text=cleaned_text,
            raw_text=parse_result.raw_text,
            metadata={
                "extraction_method": parse_result.extraction_method,
                "file_type": parse_result.file_type,
                **parse_result.metadata,
            },
        )

        # 3. ATS Parseability
        from ats_simulator import compute_ats_parseability_score
        ats_result = compute_ats_parseability_score(cleaned_text)
        structured_data["ats_parseability"] = ats_result

        # 4. Merge pipeline anomalies into metadata
        structured_data.setdefault("metadata", {})
        structured_data["metadata"]["extraction_anomalies"] = parse_result.anomalies
        structured_data["metadata"]["file_type"] = parse_result.file_type
        structured_data["metadata"]["extraction_method"] = parse_result.extraction_method
        structured_data["metadata"]["page_count"] = len(parse_result.pages)

        return {
            "status": "success",
            "filename": file.filename,
            "data": structured_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Advanced parse error: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))



# ── Pipeline ──────────────────────────────────

def _run_training_logic(role: Optional[str] = None, shared_df: pd.DataFrame = None, preprocessed_corpus: List[str] = None):
    """Core logic to process jobs, vectorize, and save the model for a specific role."""
    import time as _time
    pipeline_start = _time.time()
    
    log_banner(logger, f"TRAINING PIPELINE START {'[' + role.upper() + ']' if role else '[ALL]'}")
    log_memory(logger, "pipeline start")

    # 1. Load jobs
    log_stage(logger, 1, 7, "Data Ingestion")
    t0 = _time.time()
    
    if shared_df is not None:
        logger.info("Using pre-loaded shared dataset from memory")
        job_df = shared_df.copy() # Local copy for role-specific filtering
    else:
        if not os.path.exists(JOBS_JSON_PATH):
            raise HTTPException(status_code=400, detail="No job data found. Fetch from DB or upload first.")
        job_df = ingest_jobs(JOBS_JSON_PATH)
        
    logger.info(f"[OK] Loaded {len(job_df):,} unique jobs")
    
    # 1.1 Filter by role if specified
    if role and role.lower() != "all":
        role_key = role.lower()
        if role_key not in JOB_ROLES:
            # Try to map old UI role names for backward compatibility
            legacy_mapping = {
                "software_developer": "software_engineer",
                "data": "data_scientist"
            }
            if role_key in legacy_mapping:
                role_key = legacy_mapping[role_key]

        if role_key not in JOB_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}. Must be a supported job role.")
        
        logger.info(f"Filtering jobs for role: {role_key}")
        pattern = JOB_ROLES[role_key]["pattern"]

        # Create mask to filter both DataFrame and pre-processed Corpus
        mask = (job_df["combined_text"].str.contains(pattern, case=False, regex=True) |
                job_df["title"].str.contains(pattern, case=False, regex=True))
        
        if preprocessed_corpus is not None:
            # Important: Filter the corpus to align with the filtered dataframe
            preprocessed_corpus = [preprocessed_corpus[i] for i, m in enumerate(mask) if m]
            
        job_df = job_df[mask].copy()
        logger.info(f"Filtered to {len(job_df):,} jobs for {role_key}")
        
        if len(job_df) == 0:
            raise HTTPException(status_code=400, detail=f"No jobs found matching role: {role_key}")

    logger.info(f"[OK] Final training set: {len(job_df):,} jobs in {_time.time()-t0:.1f}s")
    check_memory("after ingestion")

    # 2. Process job texts
    log_stage(logger, 2, 7, "Text Processing")
    t0 = _time.time()
    
    if preprocessed_corpus is not None:
        logger.info("⚡ [Performance] Reusing pre-processed text corpus (Skipping Lemmatization)")
        processed_corpus = preprocessed_corpus
        # Safety check: ensure lengths match
        if len(processed_corpus) != len(job_df):
            logger.warning(f"Corpus size mismatch ({len(processed_corpus)} vs {len(job_df)}). Recalculating...")
            processed_corpus = process_series(job_df["combined_text"])
    else:
        processed_corpus = process_series(job_df["combined_text"])
        
    logger.info(f"[OK] Text processing complete in {_time.time()-t0:.1f}s")
    check_memory("after text processing")

    # 3. Extract all skills
    log_stage(logger, 3, 7, "Skill Extraction")
    t0 = _time.time()
    all_job_skills = extract_skills_from_jobs(job_df["combined_text"].tolist())
    logger.info(f"[OK] Skills extracted in {_time.time()-t0:.1f}s")
    check_memory("after skill extraction")

    # 4. TF-IDF
    log_stage(logger, 4, 7, "TF-IDF Vectorisation")
    t0 = _time.time()
    vectorizer, tfidf_matrix, feature_names = fit_tfidf(processed_corpus)
    logger.info(f"[OK] TF-IDF fitted: {tfidf_matrix.shape[0]:,} docs x {tfidf_matrix.shape[1]:,} features in {_time.time()-t0:.1f}s")
    check_memory("after TF-IDF")

    # 5. Skill intelligence pre-computation
    log_stage(logger, 5, 7, "Skill Intelligence")
    t0 = _time.time()
    skill_freq_df = skill_frequency_table(all_job_skills, len(job_df))
    tfidf_skills = extract_statistical_skills(tfidf_matrix, feature_names, 100)
    importance_df = compute_importance_weights(skill_freq_df, tfidf_skills)
    logger.info(f"[OK] Skill intelligence computed in {_time.time()-t0:.1f}s ({len(skill_freq_df)} unique skills)")

    # 6. Co-occurrence & clustering
    log_stage(logger, 6, 7, "Clustering & Co-occurrence")
    t0 = _time.time()
    cooc = skill_cooccurrence_matrix(all_job_skills, min(20, len(skill_freq_df)))
    cluster_data = None
    cluster_summary_data = None
    if len(job_df) >= 3:
        n_clusters = min(8, len(job_df) // 2)
        clustered = cluster_roles(tfidf_matrix, job_df, n_clusters)
        cluster_data = clustered[["job_id", "title", "cluster"]].head(200).to_dict("records")
        cluster_summary_data = cluster_summary(clustered).to_dict("records")
    logger.info(f"[OK] Clustering complete in {_time.time()-t0:.1f}s")
    check_memory("after clustering")

    # 7. Save model
    log_stage(logger, 7, 7, "Saving Model")
    t0 = _time.time()
    cols = ["job_id", "title"]
    if "url" in job_df.columns:
        cols.append("url")
    if "jobdescription" in job_df.columns:
        cols.append("jobdescription")
    lightweight_job_df = job_df[cols].copy()

    model_data = {
        "job_df": lightweight_job_df,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "importance_df": importance_df,
        "skill_freq_df": skill_freq_df,
        "cooc": cooc,
        "cluster_data": cluster_data,
        "cluster_summary_data": cluster_summary_data,
        "industry_top_skills": importance_df["skill"].tolist() if not importance_df.empty else []
    }

    success = save_model(model_data, role=role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save model to disk.")
    logger.info(f"[OK] Model ({role or 'all'}) saved in {_time.time()-t0:.1f}s")

    total_time = _time.time() - pipeline_start
    return len(job_df), total_time, processed_corpus

@app.post("/api/train-model")
async def train_model(role: Optional[str] = Form(None)):
    """Process jobs (optionally filtered by role), vectorize, and save the model to disk."""
    try:
        count, total_time, _ = _run_training_logic(role)
        return {"status": "ok", "message": f"Successfully trained model on {count} jobs in {total_time:.1f}s."}
    except HTTPException:
        raise
    except MemoryError as e:
        logger.critical(f"[CRIT] MEMORY LIMIT EXCEEDED: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Training error")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/train-all")
async def train_all_models():
    """Sequentially train models for all defined roles plus the general model."""
    import time
    if not os.path.exists(JOBS_JSON_PATH):
        raise HTTPException(status_code=400, detail="No job data found. Fetch from DB or upload first.")

    roles_to_train = ["all"] + list(JOB_ROLES.keys())
    results = []
    start_all = time.time()

    try:
        # Optimization: User has 32GB RAM. Load the massive 1.5GB dataset once in the parent.
        # This saves nearly 1 minute of disk I/O and parsing per role.
        from data_ingestion import ingest_jobs
        logger.info(f"🚀 [Performance] Pre-loading master dataset for {len(roles_to_train)} roles...")
        master_df = ingest_jobs(JOBS_JSON_PATH)
        
        master_corpus = None # Cache for lemmatized text

        for r in roles_to_train:
            t0 = time.time()
            
            # Pass the master_corpus if we've already lemmatized the "all" set.
            # This skips 16 minutes of CPU work per role.
            count, duration, role_corpus = _run_training_logic(
                role=r, 
                shared_df=master_df, 
                preprocessed_corpus=master_corpus if r != "all" else None
            )
            
            # Cache the "all" results for all subsequent role models
            if r == "all":
                master_corpus = role_corpus
                logger.info(f"✅ [Performance] Master corpus cached for {len(master_corpus):,} items.")
            
            results.append({
                "role": r,
                "count": count,
                "duration": duration,
                "status": "ok"
            })
        
        total_duration = time.time() - start_all
        return {
            "status": "ok",
            "message": f"Successfully trained {len(roles_to_train)} models in {total_duration:.1f}s (Optimized shared-memory mode).",
            "details": results
        }
    except Exception as e:
        logger.exception("Bulk training error")
        raise HTTPException(status_code=500, detail=str(e))

        

@app.get("/api/job-roles")
async def get_job_roles():
    """Return the list of available job roles for training/scoring from configuration."""
    roles_list = [{"id": "all", "label": "All Roles (General)"}]
    for role_id, data in JOB_ROLES.items():
        roles_list.append({"id": role_id, "label": data["label"]})
    return {"roles": roles_list}


@app.get("/api/model-status")
async def model_status():
    """Check if the NLP model is trained for various roles."""
    roles = ["all"] + list(JOB_ROLES.keys())
    status = {r: is_model_trained(r) for r in roles}
    
    # Also include the legacy names in case older UI tries to check them
    status["software_developer"] = is_model_trained("software_engineer")
    status["data"] = is_model_trained("data_scientist")
    status["devops"] = is_model_trained("devops_engineer")

    # Phase 1 — semantic model status
    from model_manager import ModelManager
    sem_model = ModelManager.get_semantic_model()

    return {
        "trained": any(status.values()),
        "roles": status,
        "semantic_model_loaded": sem_model is not None,
        "semantic_model_name":   "all-MiniLM-L6-v2",
    }


# ── Quick Match (1:1 JD vs Resume) ───────────
@app.post("/api/quick-match")
async def quick_match(
    resume_text: str = Form(...),
    jd_text: str = Form(...),
    jd_title: str = Form(default=""),
):
    """
    Direct 1:1 comparison of a resume against a single job description.
    Does NOT require pre-training — works standalone.
    Returns the full structured output schema per specification.
    """
    import time as _time
    from text_processor import process
    from skill_extractor import extract_skills_from_text
    from composite_scorer import compute_composite_score
    from ats_simulator import compute_ats_parseability_score, detect_formatting_issues
    from recommendation_engine import generate_general_tips

    try:
        t_start = _time.time()
        log_banner(logger, "QUICK MATCH ANALYSIS")
        log_memory(logger, "quick-match start")

        # 1. Process texts
        logger.info("📝 Processing resume and JD text...")
        resume_processed = process(resume_text)
        jd_processed = process(jd_text)

        # 2. Extract skills from both
        logger.info("🔍 Extracting skills...")
        resume_skills = extract_skills_from_text(resume_text)
        jd_skills = extract_skills_from_text(jd_text)
        logger.info(f"  Resume skills: {len(resume_skills)} | JD skills: {len(jd_skills)}")

        # 3. ATS parseability
        logger.info("📋 Running ATS simulation...")
        ats_result = compute_ats_parseability_score(resume_text)

        # 4. Composite scoring
        logger.info("🎯 Computing composite score...")
        score_result = compute_composite_score(
            resume_text=resume_processed,
            jd_text=jd_processed,
            resume_skills=resume_skills,
            jd_skills=jd_skills,
            jd_title=jd_title,
            ats_score=ats_result["score"],
        )

        # 5. Matched / Missing keywords
        resume_set = set(s.lower() for s in resume_skills)
        jd_set = set(s.lower() for s in jd_skills)
        matched_keywords = sorted(resume_set & jd_set)
        missing_keywords = sorted(jd_set - resume_set)

        # 6. Inferred skills (from context — skills found in resume but not in dictionary)
        # For now, report skills that are in the resume but not in the JD
        extra_resume_skills = sorted(resume_set - jd_set)

        # 7. Recommendations
        logger.info("💡 Generating recommendations...")
        recommendations = []
        for skill in missing_keywords:
            from recommendation_engine import _get_section, _get_phrasing
            section = _get_section(skill)
            phrasing = _get_phrasing(skill, section)
            priority = "critical" if skill in [s.lower() for s in jd_skills[:5]] else "recommended"
            recommendations.append({
                "skill": skill,
                "priority": priority,
                "section": section,
                "suggestion": phrasing,
                "action": f"Add {skill}" if section == "Skills Section"
                          else f"Demonstrate {skill} with a measurable achievement",
            })

        # Sort: critical first
        recommendations.sort(key=lambda r: 0 if r["priority"] == "critical" else 1)

        general_tips = generate_general_tips(resume_text, resume_skills, jd_skills)

        # 8. Fuzzy matching (Tier 3: edit-distance)
        logger.info("🔎 Running fuzzy matching...")
        from skill_extractor import fuzzy_match_skills, infer_skills_from_context
        fuzzy_results = fuzzy_match_skills(resume_text)

        # 9. Contextual skill inference (Tier 3)
        logger.info("🧠 Inferring skills from context...")
        context_inferred = infer_skills_from_context(resume_text)
        inferred_skill_names = [c["inferred_skill"] for c in context_inferred]

        # 10. Career progression (Tier 2)
        from ats_simulator import analyze_career_progression
        career = analyze_career_progression(resume_text)

        # 11. Build output schema per specification
        result = {
            "overall_match_score": score_result["overall_match_score"],
            "component_scores": score_result["component_scores"],
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "inferred_skills": inferred_skill_names,
            "fuzzy_matches": fuzzy_results,
            "formatting_issues": ats_result["issues"],
            "recommendations": recommendations,
            "general_tips": general_tips,
            "parsing_confidence": ats_result["confidence"],
            "ats_parseability": ats_result,
            "career_progression": career,
            "resume_skills": resume_skills,
            "jd_skills": jd_skills,
        }

        total_time = _time.time() - t_start
        log_banner(logger, "QUICK MATCH COMPLETE")
        logger.info(f"   Overall score: {score_result['overall_match_score']} / 100")
        logger.info(f"   Matched skills: {len(matched_keywords)}")
        logger.info(f"   Missing skills: {len(missing_keywords)}")
        logger.info(f"   Time: {total_time:.2f}s")
        log_memory(logger, "quick-match end")

        return result

    except MemoryError as e:
        logger.critical(f"🔥 MEMORY LIMIT EXCEEDED: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Quick match error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai-review")
async def ai_review(
    resume_text:      str = Form(...),
    jd_text:          str = Form(...),
    jd_title:         str = Form(""),
    missing_keywords: str = Form(""),  # JSON-encoded list
    recommendations:  str = Form(""),  # JSON-encoded list
):
    """
    Phase 2 — AI Resume Reviewer.
    Identifies weak bullets in the resume and returns Gemini-generated rewrites
    aligned to the job description. Requires GEMINI_API_KEY in .env.
    """
    from ai_reviewer import extract_weak_bullets, generate_rewrites

    try:
        missing_list = json.loads(missing_keywords) if missing_keywords else []
    except Exception:
        missing_list = []

    try:
        recs_list = json.loads(recommendations) if recommendations else []
    except Exception:
        recs_list = []

    bullets = extract_weak_bullets(resume_text, missing_list, recs_list)

    if not bullets:
        return {
            "status":    "ok",
            "available": True,
            "rewrites":  [],
            "message":   "No clear bullet candidates found — paste your resume as plain text for best results",
        }

    result = generate_rewrites(
        resume_text=resume_text,
        jd_text=jd_text,
        jd_title=jd_title,
        missing_keywords=missing_list,
        recommendations=recs_list,
        bullets_to_rewrite=bullets,
    )

    return {
        "status":    "ok",
        "available": result["available"],
        "rewrites":  result["rewrites"],
        "error":     result.get("error"),
    }


@app.post("/api/run-pipeline")
async def run_pipeline(resume_text: str = Form(...), role: Optional[str] = Form(None)):
    """Run real-time resume analysis against the pre-trained model."""
    import time as _time
    if not is_model_trained(role):
        role_label = role if role else "General"
        raise HTTPException(status_code=400, detail=f"Model for '{role_label}' is not trained. Fetch data and train the engine first.")

    try:
        t_start = _time.time()
        log_banner(logger, f"RESUME ANALYSIS PIPELINE {'[' + (role or 'ALL').upper() + ']'}")
        log_memory(logger, "analysis start")

        # Load the pre-trained data structures
        logger.info(f"[LOAD] Loading pre-trained model ({role or 'all'})...")
        model = load_model(role)
        if not model:
            raise HTTPException(status_code=500, detail="Error loading model from disk.")

        job_df = model["job_df"]
        vectorizer = model["vectorizer"]
        tfidf_matrix = model["tfidf_matrix"]
        importance_df = model["importance_df"]
        logger.info(f"[OK] Model loaded ({len(job_df):,} jobs, {tfidf_matrix.shape[1]:,} features)")

        # Process the single resume
        logger.info("[PROC] Processing resume text...")
        resume_processed = process(resume_text)
        resume_skills = extract_skills_from_text(resume_text)
        resume_vector = transform_text(resume_processed, vectorizer)
        logger.info(f"[OK] Resume processed: {len(resume_skills)} skills found")

        # Compute instant scores against the cached matrix
        logger.info("[SCORE] Computing match scores...")
        scores = compute_scores(resume_vector, tfidf_matrix)
        summary = score_summary(scores, job_df)
        logger.info(f"[OK] Scoring complete: mean={summary['mean']:.1f}, max={summary['max']:.1f}")

        # Gap analysis and recommendations
        logger.info("[FIND] Running gap analysis...")
        gap_df = analyze_gaps(resume_skills, importance_df)
        gap_summary_data = get_gap_summary(gap_df)
        logger.info(f"[OK] Gaps: {gap_summary_data['total_gaps']} total ({gap_summary_data['critical_gaps']} critical)")

        logger.info("[IDEA] Generating recommendations...")
        recommendations_df = generate_recommendations(gap_df, resume_text)
        general_tips = generate_general_tips(resume_text, resume_skills, model["industry_top_skills"])
        logger.info(f"[OK] {len(recommendations_df)} recommendations generated")

        # Build scores list for output
        all_scores_df = summary.get("all_scores_df")
        all_scores_list = all_scores_df.to_dict("records") if all_scores_df is not None else []

        # ── Tier 2/3: Composite scoring, ATS, and enriched output ──
        from composite_scorer import compute_composite_score
        from ats_simulator import compute_ats_parseability_score, analyze_career_progression
        from skill_extractor import fuzzy_match_skills, infer_skills_from_context

        # ATS parseability on resume
        ats_result = compute_ats_parseability_score(resume_text)

        # Use the top job title as JD title for composite scoring
        top_job_title = ""
        if all_scores_list:
            top_job_title = all_scores_list[0].get("title", "")

        # Industry top skills act as JD skills for corpus mode
        industry_skills = model["industry_top_skills"]

        # Composite score against best-match JD
        composite = compute_composite_score(
            resume_text=resume_processed,
            jd_text=" ".join(importance_df["skill"].tolist()) if not importance_df.empty else "",
            resume_skills=resume_skills,
            jd_skills=industry_skills,
            jd_title=top_job_title,
            ats_score=ats_result["score"],
        )

        # Matched / Missing keywords
        resume_set = set(s.lower() for s in resume_skills)
        industry_set = set(s.lower() for s in industry_skills)
        matched_keywords = sorted(resume_set & industry_set)
        missing_keywords = sorted(industry_set - resume_set)

        # Fuzzy matches and contextual inference
        fuzzy_results = fuzzy_match_skills(resume_text)
        context_inferred = infer_skills_from_context(resume_text)
        career = analyze_career_progression(resume_text)

        result = {
            # Spec-conformant output
            "overall_match_score": composite["overall_match_score"],
            "component_scores": composite["component_scores"],
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "inferred_skills": [c["inferred_skill"] for c in context_inferred],
            "fuzzy_matches": fuzzy_results,
            "formatting_issues": ats_result["issues"],
            "parsing_confidence": ats_result["confidence"],
            "ats_parseability": ats_result,
            "career_progression": career,
            # Legacy corpus-mode data
            "score_summary": {k: v for k, v in summary.items() if k != "all_scores_df"},
            "all_scores": all_scores_list[:200],
            "total_jobs_scored": len(all_scores_list),
            "gap_summary": gap_summary_data,
            "gap_details": gap_df.to_dict("records"),
            "resume_skills": resume_skills,
            "recommendations": recommendations_df.to_dict("records") if recommendations_df is not None else [],
            "general_tips": general_tips,
            "skill_frequency": model["skill_freq_df"].head(50).to_dict("records"),
            "cooccurrence": {
                "labels": model["cooc"].columns.tolist() if model["cooc"] is not None and not model["cooc"].empty else [],
                "matrix": model["cooc"].values.tolist() if model["cooc"] is not None and not model["cooc"].empty else [],
            },
            "clusters": (model["cluster_data"] or [])[:200],
            "cluster_summary": model["cluster_summary_data"],
        }

        # Convert numpy types
        def _serialize(obj):
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        # Save to local file
        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=_serialize)

        total_time = _time.time() - t_start
        log_banner(logger, "ANALYSIS COMPLETE")
        logger.info(f"   Total time: {total_time:.1f}s")
        logger.info(f"   Overall score: {summary['mean']:.1f} / 100")
        logger.info(f"   Skills matched: {gap_summary_data['resume_skills_matched']}")
        logger.info(f"   Gaps found: {gap_summary_data['total_gaps']}")
        log_memory(logger, "analysis end")

        return result

    except MemoryError as e:
        logger.critical(f"[CRIT] MEMORY LIMIT EXCEEDED: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results")
async def get_results():
    """Return cached pipeline results (trimmed for browser performance)."""
    if not os.path.exists(RESULTS_JSON):
        raise HTTPException(status_code=404, detail="No results found. Run the pipeline first.")
    with open(RESULTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Ensure large arrays are capped for browser safety
    if isinstance(data.get("all_scores"), list) and len(data["all_scores"]) > 200:
        data["all_scores"] = data["all_scores"][:200]
    if isinstance(data.get("clusters"), list) and len(data["clusters"]) > 200:
        data["clusters"] = data["clusters"][:200]
    return data


@app.get("/api/export/{format}")
async def export_report(format: str):
    """Export report in given format (excel, csv, json)."""
    if not os.path.exists(RESULTS_JSON):
        raise HTTPException(status_code=404, detail="No results to export. Run the pipeline first.")

    with open(RESULTS_JSON, "r", encoding="utf-8") as f:
        results = json.load(f)

    if format == "json":
        path = export_json(results, "ats_report.json")
        return FileResponse(path, filename="ats_report.json", media_type="application/json")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


# ── Serve React Frontend ──────────────────────
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React SPA — all non-API routes go to index.html."""
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
