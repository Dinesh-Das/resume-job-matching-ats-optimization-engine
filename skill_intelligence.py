"""
Skill Intelligence Module
Computes industry-level skill statistics: frequency, co-occurrence,
and role clustering.
"""

import numpy as np
import pandas as pd
import logging
from collections import Counter
from itertools import combinations
from sklearn.cluster import MiniBatchKMeans
from config import DEFAULT_N_CLUSTERS

logger = logging.getLogger(__name__)


def skill_frequency_table(all_job_skills: list, total_jobs: int = None) -> pd.DataFrame:
    """
    Build a DataFrame of skill frequencies across all jobs.

    Parameters
    ----------
    all_job_skills : list of lists
        Each inner list contains skills found in one job.

    Returns
    -------
    DataFrame with columns: skill, frequency, percentage, rank
    """
    freq = Counter()
    for skills in all_job_skills:
        freq.update(set(skills))

    if total_jobs is None:
        total_jobs = len(all_job_skills)

    rows = []
    for skill, count in freq.most_common():
        rows.append({
            "skill": skill,
            "frequency": count,
            "percentage": round(count / max(total_jobs, 1) * 100, 1),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["rank"] = range(1, len(df) + 1)
    return df


# Attempt to load GPU libraries
try:
    import cupy as cp
    USE_GPU = True
except ImportError:
    USE_GPU = False

def skill_cooccurrence_matrix(all_job_skills: list, top_n: int = 30) -> pd.DataFrame:
    """
    Compute a pairwise co-occurrence matrix for the top-N most frequent skills.
    Uses GPU-accelerated massive matrix operations ($X^T X$) if available, 
    otherwise falls back to fast NumPy.
    """
    # Get top skills
    freq = Counter()
    for skills in all_job_skills:
        freq.update(set(skills))
    top_skills = [s for s, _ in freq.most_common(top_n)]
    
    # Map skill name to numpy index
    skill_to_idx = {s: i for i, s in enumerate(top_skills)}

    # Build document-term matrix
    n_jobs = len(all_job_skills)
    doc_term = np.zeros((n_jobs, top_n), dtype=np.int32)

    for row, skills in enumerate(all_job_skills):
        for s in skills:
            if s in skill_to_idx:
                doc_term[row, skill_to_idx[s]] = 1

    if USE_GPU:
        try:
            doc_term_gpu = cp.asarray(doc_term)
            cooc_matrix_gpu = doc_term_gpu.T.dot(doc_term_gpu)
            cooc_matrix = cp.asnumpy(cooc_matrix_gpu)
            np.fill_diagonal(cooc_matrix, 0)
        except Exception as e:
            logger.warning(f"GPU co-occurrence failed ({e}). Falling back to CPU.")
            cooc_matrix = doc_term.T.dot(doc_term)
            np.fill_diagonal(cooc_matrix, 0)
    else:
        cooc_matrix = doc_term.T.dot(doc_term)
        np.fill_diagonal(cooc_matrix, 0)

    return pd.DataFrame(cooc_matrix, index=top_skills, columns=top_skills)


def cluster_roles(tfidf_matrix, job_df: pd.DataFrame,
                  n_clusters: int = None) -> pd.DataFrame:
    """
    Cluster jobs into groups using MiniBatchKMeans on TF-IDF vectors.

    Adds a 'cluster' column to job_df and returns it.
    """
    if n_clusters is None:
        n_clusters = min(DEFAULT_N_CLUSTERS, tfidf_matrix.shape[0])

    kmeans = MiniBatchKMeans(
        n_clusters=n_clusters,
        random_state=42,
        batch_size=min(1024, tfidf_matrix.shape[0]),
        n_init=3,
    )
    labels = kmeans.fit_predict(tfidf_matrix)
    result = job_df.copy()
    result["cluster"] = labels
    logger.info(f"Clustered {len(result)} jobs into {n_clusters} groups")
    return result


def cluster_summary(clustered_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarise each cluster: count, most common titles.
    """
    summaries = []
    for cid in sorted(clustered_df["cluster"].unique()):
        subset = clustered_df[clustered_df["cluster"] == cid]
        top_titles = subset["title"].value_counts().head(3).index.tolist()
        summaries.append({
            "cluster": cid,
            "job_count": len(subset),
            "representative_titles": " | ".join(top_titles),
        })
    return pd.DataFrame(summaries)


def compute_importance_weights(skill_freq_df: pd.DataFrame,
                               tfidf_skills: list = None) -> pd.DataFrame:
    """
    Combine frequency-based and TF-IDF based importance into a single weight.

    Parameters
    ----------
    skill_freq_df : DataFrame with columns [skill, frequency, percentage]
    tfidf_skills : list of (skill, tfidf_score) tuples (optional)

    Returns
    -------
    DataFrame with additional 'importance_weight' column.
    """
    df = skill_freq_df.copy()

    # Normalise frequency to [0, 1]
    max_freq = df["frequency"].max() if not df.empty else 1
    df["freq_norm"] = df["frequency"] / max(max_freq, 1)

    if tfidf_skills:
        tfidf_map = dict(tfidf_skills)
        max_tfidf = max(tfidf_map.values()) if tfidf_map else 1
        df["tfidf_norm"] = df["skill"].map(
            lambda s: tfidf_map.get(s, 0) / max(max_tfidf, 1e-10)
        )
    else:
        df["tfidf_norm"] = 0.0

    # Combined weight: 60% frequency + 40% TF-IDF
    df["importance_weight"] = round(0.6 * df["freq_norm"] + 0.4 * df["tfidf_norm"], 4)
    df = df.sort_values("importance_weight", ascending=False).reset_index(drop=True)

    return df
