"""
Matching Engine Module
Computes cosine similarity between resume and job vectors,
normalises to 0-100 scale, and produces summary statistics.
"""

import numpy as np
import pandas as pd
import logging
from config import SCORE_SCALE, TOP_MATCHES_COUNT, BOTTOM_MATCHES_COUNT

# Attempt to load GPU libraries
try:
    import cupy as cp
    import cupyx.scipy.sparse as cpx_sparse
    USE_GPU = True
except ImportError:
    USE_GPU = False

logger = logging.getLogger(__name__)


def compute_scores(resume_vector, job_matrix) -> np.ndarray:
    """
    Compute cosine similarity between resume vector and all job vectors.
    Accelerated with CUDA if an NVIDIA GPU (e.g., RTX 4060) is available.
    """
    if USE_GPU:
        try:
            # Transfer sparse matrices to GPU
            resume_gpu = cpx_sparse.csr_matrix(resume_vector)
            job_gpu = cpx_sparse.csr_matrix(job_matrix)
            
            # Since TfidfVectorizer uses norm='l2' by default, 
            # cosine similarity is mathematically identical to the dot product.
            # This allows blazingly fast massive matrix multiplication on the GPU.
            similarities_gpu = job_gpu.dot(resume_gpu.T).toarray().flatten()
            similarities = cp.asnumpy(similarities_gpu)
        except Exception as e:
            logger.warning(f"GPU matrix multiplication failed ({e}). Falling back to CPU dot product.")
            from scipy import sparse
            # Same math applies on CPU:
            similarities = (job_matrix.dot(resume_vector.T)).toarray().flatten()
    else:
        from scipy import sparse
        similarities = (job_matrix.dot(resume_vector.T)).toarray().flatten()

    # Non-linear scaling: raw cosine similarity for TF-IDF is typically
    # in the 0.05-0.35 range. A linear *100 maps these to 5-35.
    # We use a hyperbolic tangent (tanh) curve to aggressively boost mid-range 
    # scores while ensuring they asymptotically approach 100 without 
    # flat-lining and hitting a hard ceiling, preserving rank uniqueness.
    #   0.10 → 53,  0.20 → 83,  0.25 → 90.5, 0.30 → 94.6, 0.40 → 98.3
    similarities = np.maximum(similarities, 0)
    scores = np.tanh(similarities * 6.0) * 100
    scores = np.clip(scores, 0, 100)
    return scores


def score_summary(scores: np.ndarray, job_df: pd.DataFrame) -> dict:
    """
    Generate a comprehensive score summary.

    Returns
    -------
    dict with keys: overall_score, mean, median, std, min, max,
    percentile_25, percentile_75, top_matches, bottom_matches, all_scores_df
    """
    cols = ["job_id", "title"]
    if "url" in job_df.columns:
        cols.append("url")
    if "jobdescription" in job_df.columns:
        cols.append("jobdescription")
    job_scores = job_df[cols].copy()
    job_scores["score"] = np.round(scores, 2)
    job_scores = job_scores.sort_values("score", ascending=False).reset_index(drop=True)

    summary = {
        "overall_score": round(float(np.mean(scores)), 2),
        "best_match_score": round(float(np.max(scores)), 2),
        "mean": round(float(np.mean(scores)), 2),
        "median": round(float(np.median(scores)), 2),
        "std": round(float(np.std(scores)), 2),
        "min": round(float(np.min(scores)), 2),
        "max": round(float(np.max(scores)), 2),
        "percentile_25": round(float(np.percentile(scores, 25)), 2),
        "percentile_75": round(float(np.percentile(scores, 75)), 2),
        "top_matches": job_scores.head(TOP_MATCHES_COUNT).to_dict("records"),
        "bottom_matches": job_scores.tail(BOTTOM_MATCHES_COUNT).to_dict("records"),
        "all_scores_df": job_scores,
    }

    logger.info(
        f"Scoring complete: mean={summary['mean']}, "
        f"median={summary['median']}, max={summary['max']}"
    )
    return summary


def get_percentile_rank(score: float, scores: np.ndarray) -> float:
    """Return the percentile rank of a given score within the distribution."""
    return round(float(np.sum(scores <= score) / len(scores) * 100), 1)


def compute_semantic_similarity(resume_text: str, jd_text: str) -> dict:
    """
    Compute semantic similarity between resume and JD using sentence embeddings.

    Returns:
        score       – float 0-100  (None if unavailable)
        confidence  – float 0-1    (reliability based on input length)
        available   – bool         (False when model not loaded)
        raw_cosine  – float        (raw cosine, useful for debugging)

    Always returns a dict and never raises.
    """
    from model_manager import ModelManager

    _unavailable = {"score": None, "confidence": 0.0, "available": False}

    model = ModelManager.get_semantic_model()
    if model is None:
        return _unavailable

    try:
        def _split(text):
            return [s.strip() for s in text.replace("\n", ". ").split(".")
                    if len(s.strip()) > 15]

        r_sents = _split(resume_text)
        j_sents = _split(jd_text)

        if len(r_sents) < 3 or len(j_sents) < 3:
            return _unavailable

        r_vecs = model.encode(r_sents, convert_to_numpy=True, show_progress_bar=False)
        j_vecs = model.encode(j_sents, convert_to_numpy=True, show_progress_bar=False)

        r_mean = r_vecs.mean(axis=0)
        j_mean = j_vecs.mean(axis=0)

        denom = np.linalg.norm(r_mean) * np.linalg.norm(j_mean)
        if denom == 0:
            return _unavailable

        cosine = float(np.dot(r_mean, j_mean) / denom)

        # Map practical cosine range [0.25, 0.90] → [0, 100]
        LOW, HIGH = 0.25, 0.90
        score = round(max(0.0, min(100.0, (cosine - LOW) / (HIGH - LOW) * 100)), 1)

        # Confidence saturates at 20+ sentences per input
        confidence = round(min(1.0, min(len(r_sents), len(j_sents)) / 20.0), 2)

        return {
            "score":      score,
            "confidence": confidence,
            "available":  True,
            "raw_cosine": round(cosine, 4),
        }

    except Exception as e:
        logger.warning(f"Semantic similarity computation failed: {e}")
        return _unavailable
