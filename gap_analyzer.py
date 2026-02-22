"""
Gap Analyzer Module
Identifies missing skills between a resume and industry demand,
classifies them by priority, and ranks them for action.
"""

import pandas as pd
import logging
from config import GAP_CRITICAL_THRESHOLD, GAP_RECOMMENDED_THRESHOLD

logger = logging.getLogger(__name__)


def analyze_gaps(resume_skills: list,
                 industry_skill_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare resume skills against industry skill importance table.

    Parameters
    ----------
    resume_skills : list of str
        Skills found in the resume.
    industry_skill_df : DataFrame
        Must have columns: skill, importance_weight

    Returns
    -------
    DataFrame with columns: skill, importance_weight, priority, present_in_resume
    """
    df = industry_skill_df.copy()
    resume_set = set(s.lower() for s in resume_skills)

    df["present_in_resume"] = df["skill"].str.lower().isin(resume_set)

    # Classify priority based on importance percentile using vectorized np.select
    import numpy as np
    if not df.empty and "importance_weight" in df.columns:
        critical_cutoff = df["importance_weight"].quantile(GAP_CRITICAL_THRESHOLD)
        recommended_cutoff = df["importance_weight"].quantile(GAP_RECOMMENDED_THRESHOLD)
        
        conditions = [
            df["present_in_resume"],
            df["importance_weight"] >= critical_cutoff,
            df["importance_weight"] >= recommended_cutoff
        ]
        choices = ["present", "critical", "recommended"]
        df["priority"] = np.select(conditions, choices, default="optional")
    else:
        df["priority"] = np.where(df["present_in_resume"], "present", "recommended")

    df = df.sort_values("importance_weight", ascending=False).reset_index(drop=True)

    missing = df[df["priority"] != "present"]
    logger.info(
        f"Gap analysis: {len(resume_skills)} resume skills, "
        f"{len(missing)} gaps found "
        f"({len(df[df['priority']=='critical'])} critical, "
        f"{len(df[df['priority']=='recommended'])} recommended, "
        f"{len(df[df['priority']=='optional'])} optional)"
    )

    return df


def get_gap_summary(gap_df: pd.DataFrame) -> dict:
    """
    Produce a summary of the gap analysis.
    """
    missing = gap_df[gap_df["priority"] != "present"]
    return {
        "total_industry_skills": len(gap_df),
        "resume_skills_matched": len(gap_df[gap_df["priority"] == "present"]),
        "total_gaps": len(missing),
        "critical_gaps": len(gap_df[gap_df["priority"] == "critical"]),
        "recommended_gaps": len(gap_df[gap_df["priority"] == "recommended"]),
        "optional_gaps": len(gap_df[gap_df["priority"] == "optional"]),
        "coverage_pct": round(
            len(gap_df[gap_df["priority"] == "present"]) / max(len(gap_df), 1) * 100, 1
        ),
        "critical_missing": missing[missing["priority"] == "critical"]["skill"].tolist(),
        "recommended_missing": missing[missing["priority"] == "recommended"]["skill"].tolist(),
    }
