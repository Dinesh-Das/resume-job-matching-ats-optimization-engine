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
    # in the 0.02-0.35 range. A linear *100 maps these to 2-35, which
    # looks misleadingly low. A power curve (sim^0.5 * 200) stretches
    # the meaningful range so strong matches land in the 60-100 zone:
    #   0.05 → 44,  0.10 → 63,  0.20 → 89,  0.25 → 100
    boosted = np.power(np.maximum(similarities, 0), 0.5) * 200
    scores = np.clip(boosted, 0, 100)
    return scores


def score_summary(scores: np.ndarray, job_df: pd.DataFrame) -> dict:
    """
    Generate a comprehensive score summary.

    Returns
    -------
    dict with keys: overall_score, mean, median, std, min, max,
    percentile_25, percentile_75, top_matches, bottom_matches, all_scores_df
    """
    job_scores = job_df[["job_id", "title"]].copy()
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
