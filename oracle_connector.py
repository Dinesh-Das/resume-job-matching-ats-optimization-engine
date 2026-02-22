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
               limit: int = None) -> list:
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

    cursor.close()
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
    Read only the metadata from the JSON file (without loading all records).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "metadata" in data:
        return data["metadata"]
    return {"total_records": "unknown", "fetched_at": "unknown"}


def fetch_and_save(host: str = "localhost",
                   port: int = 1521,
                   service_name: str = "XE",
                   user: str = "system",
                   password: str = "system",
                   output_path: str = "data/jobs.json",
                   table_name: str = "JOBDETAILS",
                   limit: int = None) -> tuple:
    """
    Full pipeline: connect → fetch → save → disconnect.

    Returns (record_count, output_path).
    """
    conn = connect_oracle(host, port, service_name, user, password)
    try:
        records = fetch_jobs(conn, table_name, limit)
        save_jobs_json(records, output_path)
        return len(records), output_path
    finally:
        conn.close()
        logger.info("Oracle connection closed")
