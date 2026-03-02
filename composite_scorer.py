"""
Composite Scorer Module
Computes a multi-component match score between a resume and a job description,
combining keyword similarity, skill coverage, title alignment, experience
relevance, and ATS parseability into a weighted overall score.
"""

import re
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from thefuzz import fuzz

logger = logging.getLogger(__name__)

# ── Default component weights ─────────────────────
DEFAULT_WEIGHTS = {
    "keyword_similarity": 0.15,
    "skill_coverage": 0.35,
    "job_title_alignment": 0.10,
    "experience_relevance": 0.30,
    "ats_parseability": 0.10,
}


def compute_keyword_similarity(resume_text: str, jd_text: str) -> float:
    """
    Compute TF-IDF cosine similarity between resume and JD with a liberal boost
    to account for text length disparities. Returns score 0-1.
    """
    if not resume_text or not jd_text:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words="english",
            dtype=np.float32,
        )
        matrix = vectorizer.fit_transform([resume_text, jd_text])
        sim = cosine_similarity(matrix[0:1], matrix[1:2]).flatten()[0]
        
        # Boost raw TF-IDF similarity since resume and JDs are structurally different
        sim = sim * 1.5
        return float(np.clip(sim, 0, 1))
    except Exception as e:
        logger.warning(f"Keyword similarity computation error: {e}")
        return 0.0


def compute_skill_coverage(resume_skills: list, jd_skills: list) -> float:
    """
    Compute the fraction of JD skills present in the resume.
    Returns score 0-1.
    """
    if not jd_skills:
        return 1.0  # No requirements = full coverage
    if not resume_skills:
        return 0.0

    jd_set = set(s.lower() for s in jd_skills)
    resume_set = set(s.lower() for s in resume_skills)

    matched = jd_set & resume_set
    coverage = len(matched) / len(jd_set)

    logger.debug(f"Skill coverage: {len(matched)}/{len(jd_set)} = {coverage:.2f}")
    return float(np.clip(coverage, 0, 1))


def compute_title_alignment(resume_text: str, jd_title: str) -> float:
    """
    Compute how well the resume aligns with the target job title.
    Uses substring and fuzzy string matching.
    Returns score 0-1.
    """
    if not jd_title or not resume_text:
        return 0.5  # Neutral if no title to compare

    try:
        title_lower = jd_title.lower().strip()
        resume_lower = resume_text.lower()
        
        # Exact match anywhere:
        if title_lower in resume_lower:
            return 1.0
            
        # Isolate top 500 characters of resume (header area)
        excerpt = resume_lower[:500]
        
        # Token set ratio handles words in different order 
        # e.g., "Senior Software Engineer" vs "Software Engineer, Senior"
        best_score = max(
            fuzz.token_set_ratio(title_lower, excerpt),
            fuzz.partial_ratio(title_lower, resume_lower[500:]) * 0.8  # Body match penalized slightly
        )
        
        # normalize 0 to 1
        return float(np.clip(best_score / 100.0, 0, 1))
    except Exception as e:
        logger.warning(f"Title alignment computation error: {e}")
        return 0.5


def compute_experience_relevance(resume_text: str, jd_text: str) -> float:
    """
    Compare experience years, career progression, and seniority against JD requirements.
    Returns score 0-1.
    """
    from ats_simulator import extract_experience_years, analyze_career_progression

    # Extract years from resume
    resume_exp = extract_experience_years(resume_text)
    resume_years = resume_exp["total_years"]

    # Career progression analysis
    progression = analyze_career_progression(resume_text)

    # Extract required years from JD
    jd_year_patterns = [
        r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:minimum|at least|min)\s+(\d+)\s+(?:years?|yrs?)",
        r"(\d+)\s*[-–]\s*(\d+)\s+(?:years?|yrs?)",
    ]

    required_years = 0
    for pattern in jd_year_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2 and groups[1]:
                required_years = (int(groups[0]) + int(groups[1])) / 2
            else:
                required_years = int(groups[0])
            break

    # Base years score
    if required_years == 0:
        years_score = 0.7
    elif resume_years >= required_years:
        years_score = 1.0
    elif resume_years >= required_years * 0.7:
        years_score = 0.7
    elif resume_years >= required_years * 0.5:
        years_score = 0.5
    elif resume_years > 0:
        years_score = 0.3
    else:
        years_score = 0.2

    # Seniority matching bonus/penalty
    jd_seniority = _detect_jd_seniority(jd_text)
    seniority_score = 1.0
    if jd_seniority is not None:
        diff = progression["seniority_level"] - jd_seniority
        if diff >= 0:
            seniority_score = 1.0  # meets or exceeds
        elif diff == -1:
            seniority_score = 0.7  # one level below
        else:
            seniority_score = 0.4  # significantly under-leveled

    # Career trend bonus
    trend_bonus = 0
    if progression["seniority_trend"] == "ascending":
        trend_bonus = 0.05
    elif progression["seniority_trend"] == "descending":
        trend_bonus = -0.05

    # Domain continuity factor
    domain_factor = 0.8 + 0.2 * progression["domain_continuity"]

    # Weighted combination
    score = (years_score * 0.5 + seniority_score * 0.3 + domain_factor * 0.2) + trend_bonus
    return float(np.clip(score, 0, 1))


def _detect_jd_seniority(jd_text: str) -> int:
    """Detect the seniority level expected in a JD. Returns 0-5 or None."""
    text_lower = jd_text.lower()
    from ats_simulator import SENIORITY_KEYWORDS
    found = []
    for keyword, level in SENIORITY_KEYWORDS.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
            found.append(level)
    return max(found) if found else None


def compute_section_weighted_similarity(resume_text: str, jd_text: str) -> float:
    """
    Compute keyword similarity with section weighting.
    Skills section content gets higher weight than education, etc.
    Returns score 0-1.
    """
    from ats_simulator import compute_section_weights

    section_data = compute_section_weights(resume_text)
    if not section_data:
        return compute_keyword_similarity(resume_text, jd_text)

    # Build weighted resume text by repeating high-weight sections
    weighted_parts = []
    for sec_name, data in section_data.items():
        repeat = max(1, int(data["weight"] * 3))  # weight 1.0 → 3 repeats
        weighted_parts.extend([data["text"]] * repeat)

    weighted_resume = " ".join(weighted_parts)
    return compute_keyword_similarity(weighted_resume, jd_text)


def compute_composite_score(
    resume_text: str,
    jd_text: str,
    resume_skills: list,
    jd_skills: list,
    jd_title: str = "",
    ats_score: float = None,
    weights: dict = None,
) -> dict:
    """
    Compute the full multi-component match score.

    Parameters
    ----------
    resume_text : str
        Processed resume text.
    jd_text : str
        Job description text.
    resume_skills : list
        Skills extracted from the resume.
    jd_skills : list
        Skills extracted from the JD.
    jd_title : str
        Job title from the JD.
    ats_score : float, optional
        Pre-computed ATS parseability score (0-100). Will compute if None.
    weights : dict, optional
        Component weights (must sum to 1.0).

    Returns
    -------
    dict with:
        overall_match_score: float (0-100)
        component_scores: dict of component -> score (0-100)
        weights_used: dict
    """
    w = weights or DEFAULT_WEIGHTS

    # Compute each component (all return 0-1)
    logger.info("Computing composite score components...")

    # Use section-weighted similarity (skills section content weighted higher)
    kw_sim = compute_section_weighted_similarity(resume_text, jd_text)
    logger.info(f"  Keyword similarity (section-weighted): {kw_sim:.3f}")

    skill_cov = compute_skill_coverage(resume_skills, jd_skills)
    logger.info(f"  Skill coverage:         {skill_cov:.3f}")

    title_align = compute_title_alignment(resume_text, jd_title)
    logger.info(f"  Title alignment:        {title_align:.3f}")

    exp_rel = compute_experience_relevance(resume_text, jd_text)
    logger.info(f"  Experience relevance:   {exp_rel:.3f}")

    if ats_score is not None:
        ats_norm = ats_score / 100.0
    else:
        from ats_simulator import compute_ats_parseability_score
        ats_result = compute_ats_parseability_score(resume_text)
        ats_norm = ats_result["score"] / 100.0
    logger.info(f"  ATS parseability:       {ats_norm:.3f}")

    # Weighted composite
    overall = (
        w["keyword_similarity"] * kw_sim
        + w["skill_coverage"] * skill_cov
        + w["job_title_alignment"] * title_align
        + w["experience_relevance"] * exp_rel
        + w["ats_parseability"] * ats_norm
    )

    # Penalty for missing critical skills (top JD skills not in resume)
    if jd_skills and resume_skills:
        jd_top5 = set(s.lower() for s in jd_skills[:5])
        resume_set = set(s.lower() for s in resume_skills)
        missing_critical = jd_top5 - resume_set
        if missing_critical:
            penalty = len(missing_critical) / len(jd_top5) * 0.05  # MAX 5% penalty
            overall = max(0, overall - penalty)
            logger.info(f"  Critical skill penalty: -{penalty:.3f} ({len(missing_critical)} missing)")

    component_scores = {
        "keyword_similarity": round(kw_sim * 100, 1),
        "skill_coverage": round(skill_cov * 100, 1),
        "job_title_alignment": round(title_align * 100, 1),
        "experience_relevance": round(exp_rel * 100, 1),
        "ats_parseability": round(ats_norm * 100, 1),
    }

    overall_score = round(float(np.clip(overall * 100, 0, 100)), 1)

    logger.info(f"  ──────────────────────")
    logger.info(f"  Overall match score:    {overall_score}")

    return {
        "overall_match_score": overall_score,
        "component_scores": component_scores,
        "weights_used": w,
    }
