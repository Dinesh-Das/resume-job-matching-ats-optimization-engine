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
from pathlib import Path
from typing import Optional

# Silence joblib physical core warning on CPUs with P/E cores (like i7-14700HX)
os.environ["LOKY_MAX_CPU_COUNT"] = str(multiprocessing.cpu_count())

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    OUTPUT_DIR, JOBS_JSON_PATH, ORACLE_DEFAULTS,
)
from data_ingestion import ingest_jobs
from resume_parser import parse_resume
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
from oracle_connector import fetch_and_save, get_jobs_json_metadata
from model_manager import save_model, load_model, is_model_trained

# ── Logging Setup (must be before any logger usage) ────
from logging_config import setup_logging, log_banner, log_stage
from resource_monitor import check_memory, log_memory, get_memory_usage_gb

setup_logging()
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────
RESULTS_JSON = os.path.join(OUTPUT_DIR, "results.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

app = FastAPI(title="ATS Optimization Engine API")

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

@app.post("/api/connect-db")
async def connect_db(
    host: str = Form(default="localhost"),
    port: int = Form(default=1521),
    service_name: str = Form(default="XE"),
    user: str = Form(default="system"),
    password: str = Form(default="system"),
    table_name: str = Form(default="JOBDETAILS"),
):
    """Connect to Oracle, fetch jobs, save to data/jobs.json."""
    try:
        count, path = fetch_and_save(
            host=host, port=int(port), service_name=service_name,
            user=user, password=password,
            output_path=JOBS_JSON_PATH, table_name=table_name,
        )
        return {"status": "ok", "count": count, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


# Cache for jobs to speed up Jobs Explorer
GLOBAL_JOBS_CACHE = None
GLOBAL_JOBS_CACHE_MTIME = 0

@app.get("/api/jobs-data")
async def jobs_data(
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
):
    """Return paginated jobs from the cached jobs.json for the jobs listing page."""
    global GLOBAL_JOBS_CACHE, GLOBAL_JOBS_CACHE_MTIME

    if not os.path.exists(JOBS_JSON_PATH):
        raise HTTPException(status_code=404, detail="No job data found. Fetch from DB or upload first.")
        
    try:
        current_mtime = os.path.getmtime(JOBS_JSON_PATH)
        if GLOBAL_JOBS_CACHE is None or current_mtime > GLOBAL_JOBS_CACHE_MTIME:
            # Load into cache
            with open(JOBS_JSON_PATH, "r", encoding="utf-8") as f:
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
            
            GLOBAL_JOBS_CACHE = {
                "jobs": all_jobs,
                "metadata": metadata
            }
            GLOBAL_JOBS_CACHE_MTIME = current_mtime
            
        all_jobs = GLOBAL_JOBS_CACHE["jobs"]
        metadata = GLOBAL_JOBS_CACHE["metadata"]

        # Strip heavy fields to reduce payload size
        LIGHT_FIELDS = ["title", "company_name", "companyname", "location",
                        "experience", "keyskills", "role", "salary",
                        "industry_type", "industrytype", "employment_type",
                        "employmenttype", "education", "posted", "url"]

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
        end = start + page_size
        page_jobs = all_jobs[start:end]

        # Return only lightweight fields per job
        light_jobs = []
        for j in page_jobs:
            light = {k: j.get(k, "") for k in LIGHT_FIELDS if k in j}
            # Include a truncated description (max 500 chars)
            desc = j.get("jobdescription", "")
            if desc:
                light["jobdescription"] = desc[:500]
            light_jobs.append(light)

        return {
            "jobs": light_jobs,
            "metadata": metadata,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── File Upload ───────────────────────────────

@app.post("/api/upload-jobs")
async def upload_jobs(file: UploadFile = File(...)):
    """Upload a job dataset (CSV/JSON/Excel) and save as jobs.json."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "json", "jsonl", "xlsx", "xls"):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = ingest_jobs(tmp_path)
        # Save as standardised jobs.json
        records = df.to_dict("records")
        from oracle_connector import save_jobs_json
        save_jobs_json(records, JOBS_JSON_PATH)
        return {"status": "ok", "count": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Parse an uploaded resume and return extracted text."""
    try:
        content = await file.read()
        from io import BytesIO
        text = parse_resume(BytesIO(content), filename=file.filename)
        return {"status": "ok", "text": text, "length": len(text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Parse an uploaded resume/JD file (PDF, DOCX, TXT) into plain text."""
    from resume_parser import parse_pdf, parse_docx, parse_txt
    import io

    try:
        ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
        content = await file.read()
        buf = io.BytesIO(content)

        if ext == "pdf":
            text = parse_pdf(buf)
        elif ext in ("docx", "doc"):
            text = parse_docx(buf)
        elif ext in ("txt", "text"):
            text = parse_txt(buf)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file.")

        logger.info(f"📄 Parsed uploaded file: {file.filename} ({len(text)} chars)")
        return {"text": text, "filename": file.filename, "characters": len(text)}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"File parse error: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Pipeline ──────────────────────────────────

@app.post("/api/train-model")
def train_model():
    """Process all jobs, vectorize, and save the model to disk."""
    import time as _time
    if not os.path.exists(JOBS_JSON_PATH):
        raise HTTPException(status_code=400, detail="No job data found. Fetch from DB or upload first.")

    try:
        pipeline_start = _time.time()
        log_banner(logger, "TRAINING PIPELINE START")
        log_memory(logger, "pipeline start")

        # 1. Load jobs
        log_stage(logger, 1, 7, "Data Ingestion")
        t0 = _time.time()
        job_df = ingest_jobs(JOBS_JSON_PATH)
        logger.info(f"[OK] Loaded {len(job_df):,} unique jobs in {_time.time()-t0:.1f}s")
        check_memory("after ingestion")

        # 2. Process job texts
        log_stage(logger, 2, 7, "Text Processing")
        t0 = _time.time()
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
        lightweight_job_df = job_df[["job_id", "title"]].copy()

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

        success = save_model(model_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save model to disk.")
        logger.info(f"[OK] Model saved in {_time.time()-t0:.1f}s")

        # Final summary
        total_time = _time.time() - pipeline_start
        log_banner(logger, "TRAINING PIPELINE COMPLETE")
        logger.info(f"   Total time: {total_time:.1f}s")
        logger.info(f"   Jobs processed: {len(job_df):,}")
        logger.info(f"   Unique skills: {len(skill_freq_df):,}")
        logger.info(f"   TF-IDF features: {tfidf_matrix.shape[1]:,}")
        log_memory(logger, "pipeline end")

        return {"status": "ok", "message": f"Successfully trained model on {len(job_df)} jobs in {total_time:.1f}s."}

    except MemoryError as e:
        logger.critical(f"[CRIT] MEMORY LIMIT EXCEEDED: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Training error")
        raise HTTPException(status_code=500, detail=str(e))
        

@app.get("/api/model-status")
async def model_status():
    """Check if the NLP model is trained and ready."""
    return {"trained": is_model_trained()}


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


@app.post("/api/run-pipeline")
async def run_pipeline(resume_text: str = Form(...)):
    """Run real-time resume analysis against the pre-trained model."""
    import time as _time
    if not is_model_trained():
        raise HTTPException(status_code=400, detail="Model is not trained. Fetch data and train the engine first.")

    try:
        t_start = _time.time()
        log_banner(logger, "RESUME ANALYSIS PIPELINE")
        log_memory(logger, "analysis start")

        # Load the pre-trained data structures
        logger.info("[LOAD] Loading pre-trained model...")
        model = load_model()
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
