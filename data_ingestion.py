"""
Data Ingestion Module
Loads job datasets from CSV/JSON/Excel, validates schema, deduplicates, and
prepares a unified text column for downstream processing.
Supports both direct CSV uploads and Oracle-exported JSON (via oracle_connector).
"""

import json
import pandas as pd
import numpy as np
import hashlib
import logging

logger = logging.getLogger(__name__)


def load_jobs(path: str) -> pd.DataFrame:
    """
    Load job data from CSV, JSON, or Excel file.
    Handles both standard CSV format and Oracle-exported JSON structure.
    """
    ext = path.rsplit(".", 1)[-1].lower()

    if ext == "csv":
        df = pd.read_csv(path, dtype=str)
    elif ext in ("json", "jsonl"):
        df = _load_json_flexible(path)
    elif ext in ("xlsx", "xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

    # Normalise column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Validate required columns
    required = {"title", "keyskills", "jobdescription"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Generate job_id if absent
    if "job_id" not in df.columns:
        df.insert(0, "job_id", range(1, len(df) + 1))

    # Fill NaN text fields
    text_cols = ["title", "keyskills", "jobdescription"]
    for col in text_cols:
        df[col] = df[col].fillna("")

    # Fill optional text columns that might exist
    optional_text_cols = [
        "company_name", "experience", "salary", "location",
        "role", "industry_type", "department", "employment_type",
        "role_category", "education", "url", "rating", "reviews",
        "posted", "openings", "applications",
    ]
    for col in optional_text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("")

    logger.info(f"Loaded {len(df)} job records from {path}")
    return df


def _load_json_flexible(path: str) -> pd.DataFrame:
    """
    Load JSON file, handling both:
    1. Oracle-exported format: {"metadata": {...}, "jobs": [...]}
    2. Standard pandas-compatible JSON (list of objects or records)
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "jobs" in data:
        # Oracle-exported format
        records = data["jobs"]
        df = pd.DataFrame(records)
        logger.info(
            f"Loaded Oracle JSON: {len(records)} records "
            f"(fetched: {data.get('metadata', {}).get('fetched_at', 'unknown')})"
        )
        return df
    elif isinstance(data, list):
        return pd.DataFrame(data)
    else:
        # Try pandas default
        return pd.read_json(path, dtype=str)


def deduplicate_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate jobs based primarily on URL.
    Falls back to title + description if URL is missing or empty.
    Uses vectorized string operations for maximum speed.
    """
    before = len(df)
    
    # 1. Use URL if it exists in the dataframe, otherwise use empty strings
    if "url" in df.columns:
        url_col = df["url"].fillna("").str.strip()
    else:
        url_col = pd.Series([""] * len(df), index=df.index)
        
    # 2. Compute a fallback key (title + description)
    fallback_key = (df["title"].fillna("").str.strip().str.lower() + 
                    df["jobdescription"].fillna("").str.strip().str.lower())
    
    # 3. Create a final deduplication key. 
    # If the URL is missing, we prefix with "FALLBACK_" and attach the fallback string.
    # If the URL exists, we just use the URL.
    dedup_key = np.where(url_col != "", url_col, "FALLBACK_" + fallback_key)
                 
    df = df.assign(_dedup_key=dedup_key).drop_duplicates(subset="_dedup_key").drop(columns="_dedup_key").reset_index(drop=True)
    
    removed = before - len(df)
    if removed:
        logger.info(f"Removed {removed} duplicate job records")
    return df


def combine_job_text(df: pd.DataFrame) -> pd.DataFrame:
    """
    Concatenate title + keyskills + jobdescription into a single 'combined_text' column.
    Also incorporates role and education if available for richer matching.
    """
    parts = [
        df["title"].str.strip(),
        df["keyskills"].str.strip(),
        df["jobdescription"].str.strip(),
    ]

    # Include extra fields if they exist (from Oracle data)
    for col in ["role", "education"]:
        if col in df.columns:
            parts.append(df[col].str.strip())

    df["combined_text"] = parts[0]
    for part in parts[1:]:
        df["combined_text"] = df["combined_text"] + " " + part

    return df


def ingest_jobs(path: str) -> pd.DataFrame:
    """
    Full ingestion pipeline: load → deduplicate → combine text.
    """
    df = load_jobs(path)
    df = deduplicate_jobs(df)
    df = combine_job_text(df)
    logger.info(f"Ingestion complete: {len(df)} unique jobs ready")
    return df
