"""
Oracle Database Connector Module
Fetches job data from Oracle's JOBDETAILS table and stores as JSON.
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Column mapping: Oracle column → our internal field name
COLUMN_MAP = {
    "URL": "url",
    "TITLE": "title",
    "COMPANYNAME": "company_name",
    "RATING": "rating",
    "REVIEWS": "reviews",
    "EXPERIENCE": "experience",
    "SALARY": "salary",
    "LOCATION": "location",
    "POSTED": "posted",
    "OPENINGS": "openings",
    "APPLICATIONS": "applications",
    "JOBDESCRIPTION": "jobdescription",
    "ROLE": "role",
    "INDUSTRYTYPE": "industry_type",
    "DEPARTMENT": "department",
    "EMPLOYMENTTYPE": "employment_type",
    "ROLECATEGORY": "role_category",
    "LOGDATE": "log_date",
    "EDUCATION": "education",
    "KEYSKILLS": "keyskills",
}


def connect_oracle(host: str = "localhost",
                   port: int = 1521,
                   service_name: str = "XE",
                   user: str = "system",
                   password: str = "system"):
    """
    Create an Oracle DB connection using oracledb (thin mode — no Oracle Client needed).
    """
    import oracledb

    dsn = f"{host}:{port}/{service_name}"
    connection = oracledb.connect(user=user, password=password, dsn=dsn)
    logger.info(f"Connected to Oracle: {user}@{dsn}")
    return connection


def fetch_jobs(connection, table_name: str = "JOBDETAILS",
               limit: int = None, progress_callback=None) -> list:
    """
    Fetch all rows from the JOBDETAILS table.

    Parameters
    ----------
    connection : oracledb connection
    table_name : str
    limit : int, optional — limit number of rows (useful for testing)

    Returns
    -------
    list of dicts, each dict is one job record.
    """
    cursor = connection.cursor()

    # Get total count for progress reporting
    total_records = None
    if progress_callback:
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        if limit:
            count_query = f"SELECT COUNT(*) FROM {table_name} WHERE ROWNUM <= {limit}"
        try:
            cursor.execute(count_query)
            total_records = cursor.fetchone()[0]
        except Exception as e:
            logger.warning(f"Could not fetch total count: {e}")

    query = f"SELECT * FROM {table_name}"
    if limit:
        query = f"SELECT * FROM {table_name} WHERE ROWNUM <= {limit}"

    cursor.execute(query)

    # Get column names from cursor description
    columns = [col[0] for col in cursor.description]

    rows = []
    for row in cursor:
        record = {}
        for col_name, value in zip(columns, row):
            mapped_name = COLUMN_MAP.get(col_name, col_name.lower())

            # Handle CLOB
            if hasattr(value, "read"):
                value = value.read()

            # Handle timestamps
            if isinstance(value, datetime):
                value = value.isoformat()

            # Handle None
            if value is None:
                value = ""

            record[mapped_name] = str(value)

        rows.append(record)
        
        # Report progress every 5000 rows
        if progress_callback and len(rows) % 5000 == 0:
            if total_records:
                pct = min(0.9, len(rows) / total_records)
                progress_callback(pct, f"Fetched {len(rows):,} of {total_records:,} records...")
            else:
                progress_callback(0.5, f"Fetched {len(rows):,} records...")

    cursor.close()
    if progress_callback:
        progress_callback(0.9, f"Fetched {len(rows):,} records. Saving to disk...")
        
    logger.info(f"Fetched {len(rows)} records from {table_name}")
    return rows


def save_jobs_json(records: list, output_path: str) -> str:
    """
    Save job records to a JSON file.
    """
    # Add metadata
    data = {
        "metadata": {
            "fetched_at": datetime.now().isoformat(),
            "total_records": len(records),
            "source": "Oracle JOBDETAILS table",
        },
        "jobs": records,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(records)} jobs to {output_path}")
    return output_path


def load_jobs_json(json_path: str) -> list:
    """
    Load job records from the saved JSON file.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "jobs" in data:
        records = data["jobs"]
        metadata = data.get("metadata", {})
        logger.info(
            f"Loaded {len(records)} jobs from JSON "
            f"(fetched: {metadata.get('fetched_at', 'unknown')})"
        )
        return records
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Unexpected JSON structure")


def get_jobs_json_metadata(json_path: str) -> dict:
    """
    Read only the metadata header from the JSON file without loading all records.
    Prefers the lightweight jobs_meta.json if it exists (instant read).
    Falls back to regex head-read on the full file if meta file is missing.
    """
    import re
    # Fast path: prefer pre-built meta file
    meta_path = os.path.join(os.path.dirname(json_path), "jobs_meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback: regex scan of first 2KB (avoids parsing the full 1.5GB file)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            head = f.read(2048)

        fetched_at = ""
        total_records = "unknown"

        m_fetched = re.search(r'"fetched_at"\s*:\s*"([^"]+)"', head)
        if m_fetched:
            fetched_at = m_fetched.group(1)

        m_total = re.search(r'"total_records"\s*:\s*(\d+)', head)
        if m_total:
            total_records = int(m_total.group(1))

        if not m_fetched and not m_total:
            file_size = os.path.getsize(json_path)
            return {"total_records": "unknown", "fetched_at": None,
                    "file_size_mb": round(file_size / 1024 / 1024, 1)}

        return {"fetched_at": fetched_at or None, "total_records": total_records}
    except Exception:
        return {"total_records": "unknown", "fetched_at": None}


def save_jobs_paginated(records: list, data_dir: str) -> None:
    """
    Write lightweight index files alongside the full jobs.json for fast serving:
      - jobs_meta.json   : tiny file with count + timestamp (~500 bytes)
      - jobs_index.json  : display fields only for Jobs Explorer (~40MB for 545k records)

    The full jobs.json is NOT touched — training still reads it directly.
    """
    INDEX_FIELDS = [
        "url", "title", "company_name", "location", "experience",
        "keyskills", "role", "salary", "industry_type", "employment_type",
        "education", "posted",
    ]
    os.makedirs(data_dir, exist_ok=True)

    # 1. Write meta file (instant status checks)
    meta = {
        "fetched_at": datetime.now().isoformat(),
        "total_records": len(records),
        "source": "Oracle JOBDETAILS table",
    }
    meta_path = os.path.join(data_dir, "jobs_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)
    logger.info(f"Wrote jobs_meta.json ({len(records)} records)")

    # 2. Write lightweight index (display fields only)
    index_records = []
    for rec in records:
        entry = {k: rec.get(k, "") for k in INDEX_FIELDS if k in rec or rec.get(k) is not None}
        # Keep full jobdescription for display
        desc = rec.get("jobdescription", "")
        if desc:
            entry["jobdescription"] = desc
        index_records.append(entry)

    index_path = os.path.join(data_dir, "jobs_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": meta, "jobs": index_records}, f, ensure_ascii=False)
    size_mb = os.path.getsize(index_path) / 1024 / 1024
    logger.info(f"Wrote jobs_index.json ({size_mb:.1f} MB, {len(index_records)} records)")




def fetch_and_save(host: str = "localhost",
                   port: int = 1521,
                   service_name: str = "XE",
                   user: str = "system",
                   password: str = "system",
                   output_path: str = "data/jobs.json",
                   table_name: str = "JOBDETAILS",
                   limit: int = None,
                   progress_callback=None) -> tuple:
    """
    Full pipeline: connect → fetch → save → disconnect.

    Returns (record_count, output_path).
    """
    conn = connect_oracle(host, port, service_name, user, password)
    try:
        if progress_callback:
            progress_callback(0.05, "Connected to Oracle. Fetching records...")
        records = fetch_jobs(conn, table_name, limit, progress_callback)
        save_jobs_json(records, output_path)
        return len(records), output_path
    finally:
        conn.close()
        logger.info("Oracle connection closed")
