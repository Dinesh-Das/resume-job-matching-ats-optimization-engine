"""
Skill Extractor Module
Detects skills from text using dictionary matching and statistical extraction.
"""

import re
import logging
from collections import Counter
from config import SKILL_DICTIONARY, MAX_WORKERS, CHUNK_SIZE

logger = logging.getLogger(__name__)


_SKILL_PATTERN = None

def _get_skill_pattern(skill_dict: list):
    """Compile and cache a single regex pattern for all skills in the dictionary."""
    global _SKILL_PATTERN
    if _SKILL_PATTERN is None:
        if skill_dict is None:
            skill_dict = SKILL_DICTIONARY
        # Sort skills by length (longest first) to match multi-word before single-word
        sorted_skills = sorted(skill_dict, key=len, reverse=True)
        # Create a giant OR pattern: \b(skill1|skill2|...)\b
        escaped = [re.escape(s) for s in sorted_skills]
        pattern_str = r"\b(" + "|".join(escaped) + r")\b"
        _SKILL_PATTERN = re.compile(pattern_str, re.IGNORECASE)
    return _SKILL_PATTERN

def extract_skills_from_text(text: str, skill_dict: list = None) -> list:
    """
    Extract skills from text by matching against the curated skill dictionary.
    Handles multi-word skills and single-word skills separately for accuracy.

    Returns a deduplicated list of matched skills sorted alphabetically.
    """
    if not text:
        return []

    pattern = _get_skill_pattern(skill_dict)
    matches = pattern.findall(text)
    
    # Matches will be whatever case they were found in; lowercase them for the final set
    found = set(m.lower() for m in matches)
    return sorted(list(found))

def extract_single_text_skills(text: str) -> list:
    """Helper worker for multiprocessing."""
    return extract_skills_from_text(text, None)

def extract_skills_from_jobs(job_texts: list, skill_dict: list = None) -> list:
    """
    Extract skills from each job text using ProcessPoolExecutor for true multicore speed.
    Returns a list of lists (one per job).
    """
    from concurrent.futures import ProcessPoolExecutor
    from logging_config import ProgressLogger
    from resource_monitor import check_memory

    total = len(job_texts)
    logger.info(f"🔍 Skill Extraction — {MAX_WORKERS} workers, {total:,} jobs")
    check_memory("skill_extraction start")

    progress = ProgressLogger("Skill Extraction", total, logger, report_every_pct=20)
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = []
        for i, result in enumerate(executor.map(extract_single_text_skills, job_texts, chunksize=CHUNK_SIZE)):
            results.append(result)
            if (i + 1) % CHUNK_SIZE == 0 or i + 1 == total:
                progress.update(CHUNK_SIZE if (i + 1) % CHUNK_SIZE == 0 else (i + 1) % CHUNK_SIZE)
    progress.finish()

    check_memory("skill_extraction end")
    return results


def extract_statistical_skills(tfidf_matrix, feature_names: list, top_k: int = 50) -> list:
    """
    Extract top-k statistical skills from a TF-IDF matrix by mean importance.

    Parameters
    ----------
    tfidf_matrix : sparse matrix
        Job corpus TF-IDF matrix (n_jobs x n_features).
    feature_names : list
        Feature names from the vectoriser.
    top_k : int
        Number of top features to return.

    Returns
    -------
    list of (skill, importance_score) tuples.
    """
    import numpy as np

    # Mean TF-IDF importance across all jobs
    mean_importance = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

    # Get top-k indices
    top_indices = mean_importance.argsort()[::-1][:top_k]

    results = []
    for idx in top_indices:
        results.append((feature_names[idx], float(mean_importance[idx])))

    return results


def compute_skill_frequency(all_job_skills: list) -> Counter:
    """
    Compute the frequency of each skill across all jobs.

    Parameters
    ----------
    all_job_skills : list of lists
        Skills extracted from each job.

    Returns
    -------
    Counter mapping skill → count.
    """
    freq = Counter()
    for skills in all_job_skills:
        # Count each skill once per job (document frequency)
        freq.update(set(skills))
    return freq


def get_ranked_skill_table(all_job_skills: list, total_jobs: int = None) -> list:
    """
    Build a ranked skill table with frequency and percentage.

    Returns list of dicts: [{"skill", "frequency", "percentage"}, ...]
    """
    freq = compute_skill_frequency(all_job_skills)
    if total_jobs is None:
        total_jobs = len(all_job_skills)

    table = []
    for skill, count in freq.most_common():
        table.append({
            "skill": skill,
            "frequency": count,
            "percentage": round(count / max(total_jobs, 1) * 100, 1),
        })

    return table


# ── Fuzzy Matching ────────────────────────────────

def fuzzy_match_skills(text: str, skill_dict: list = None, max_distance: int = 2) -> list:
    """
    Find skills in text using edit-distance fuzzy matching for spelling variations.
    Only triggers on words not found by exact dictionary match.

    Returns a list of dicts: [{"found": str, "matched_to": str, "distance": int}, ...]
    """
    if not text:
        return []

    if skill_dict is None:
        skill_dict = SKILL_DICTIONARY

    # Get exact matches first
    exact = set(s.lower() for s in extract_skills_from_text(text, skill_dict))

    # Tokenize text into words and bigrams
    words = re.findall(r"\b[a-zA-Z][\w\+\#\.\-]*[a-zA-Z\+\#]\b", text.lower())
    # Also check bigrams
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    candidates = set(words + bigrams) - exact

    fuzzy_matches = []
    skill_lower = {s.lower(): s for s in skill_dict}

    for candidate in candidates:
        if len(candidate) < 3:
            continue
        for skill_key, skill_orig in skill_lower.items():
            if skill_key in exact:
                continue
            dist = _levenshtein(candidate, skill_key)
            if 0 < dist <= max_distance and dist <= len(skill_key) * 0.3:
                fuzzy_matches.append({
                    "found": candidate,
                    "matched_to": skill_key,
                    "distance": dist,
                })
                break  # one match per candidate

    logger.info(f"Fuzzy matching: {len(fuzzy_matches)} potential matches found")
    return fuzzy_matches


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


# ── Contextual Skill Inference ────────────────────

CONTEXT_RULES = {
    # "action phrase pattern" → inferred skill
    r"built\s+(?:data\s+)?pipeline": "data engineering",
    r"train(?:ed|ing)\s+(?:ml|machine\s+learning)\s+model": "machine learning",
    r"deploy(?:ed|ing)\s+(?:to\s+)?(?:cloud|aws|azure|gcp)": "cloud deployment",
    r"manage(?:d|ing)\s+(?:a\s+)?team": "leadership",
    r"led\s+(?:a\s+)?(?:team|group|squad)": "leadership",
    r"creat(?:ed|ing)\s+(?:rest|api|restful)": "api design",
    r"perform(?:ed|ing)\s+(?:data\s+)?analy(?:sis|tics)": "data analysis",
    r"(?:built|developed|created)\s+(?:web|mobile)\s+app": "full stack development",
    r"implement(?:ed|ing)\s+(?:ci|cd|cicd|ci/cd)": "cicd",
    r"design(?:ed|ing)\s+(?:system|architecture|database|schema)": "system design",
    r"optimi[sz](?:ed|ing)\s+(?:performance|query|database|sql)": "performance optimization",
    r"automat(?:ed|ing)\s+(?:test|deploy|process|workflow)": "automation",
    r"mentor(?:ed|ing)\s+(?:junior|team|developer)": "mentoring",
    r"migrat(?:ed|ing)\s+(?:to\s+)?(?:cloud|microservice|docker|kubernetes)": "cloud migration",
    r"implement(?:ed|ing)\s+(?:unit|integration|e2e)\s+test": "testing",
    r"scal(?:ed|ing)\s+(?:system|application|service|infrastructure)": "scalability",
}


def infer_skills_from_context(text: str) -> list:
    """
    Infer skills from action phrases in resume text.
    e.g. "built data pipelines" → data engineering

    Returns list of dicts: [{"phrase": str, "inferred_skill": str}, ...]
    """
    if not text:
        return []

    text_lower = text.lower()
    inferred = []

    for pattern, skill in CONTEXT_RULES.items():
        match = re.search(pattern, text_lower)
        if match:
            inferred.append({
                "phrase": match.group(0),
                "inferred_skill": skill,
            })

    logger.info(f"Contextual inference: {len(inferred)} skills inferred")
    return inferred


# ── Binary Skill Vector ──────────────────────────

def build_binary_skill_vector(skills: list, vocabulary: list = None) -> list:
    """
    Build a binary (0/1) skill vector for a set of skills.

    Parameters
    ----------
    skills : list
        Skills found in a resume or JD.
    vocabulary : list
        Full skill vocabulary. Defaults to SKILL_DICTIONARY.

    Returns
    -------
    list of int (0 or 1), same length as vocabulary.
    """
    if vocabulary is None:
        vocabulary = SKILL_DICTIONARY

    vocab_lower = [v.lower() for v in vocabulary]
    skill_set = set(s.lower() for s in skills)

    return [1 if v in skill_set else 0 for v in vocab_lower]
