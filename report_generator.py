"""
Report Generator Module
Exports analysis results to CSV, Excel, and JSON formats.
"""

import os
import json
import logging
import pandas as pd
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def export_csv(df: pd.DataFrame, filename: str) -> str:
    """Export a DataFrame to CSV. Returns the file path."""
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info(f"Exported CSV: {path}")
    return path


def export_excel(sheets: dict, filename: str) -> str:
    """
    Export multiple DataFrames to an Excel workbook.

    Parameters
    ----------
    sheets : dict
        Mapping of sheet_name → DataFrame.
    filename : str
        Output filename (e.g., 'report.xlsx').

    Returns the file path.
    """
    path = os.path.join(OUTPUT_DIR, filename)
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        for sheet_name, df in sheets.items():
            # Truncate sheet name to 31 chars (Excel limit)
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)

            # Auto-fit columns
            worksheet = writer.sheets[safe_name]
            for col_idx, col in enumerate(df.columns):
                max_len = max(
                    df[col].astype(str).str.len().max(),
                    len(str(col))
                ) + 2
                worksheet.set_column(col_idx, col_idx, min(max_len, 50))

    logger.info(f"Exported Excel: {path}")
    return path


def export_json(data: dict, filename: str) -> str:
    """Export a dictionary to JSON. Returns the file path."""
    path = os.path.join(OUTPUT_DIR, filename)

    # Make JSON-serialisable (handle DataFrames, numpy types)
    def _serialise(obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict("records")
        if hasattr(obj, "item"):  # numpy scalar
            return obj.item()
        if hasattr(obj, "tolist"):  # numpy array
            return obj.tolist()
        return str(obj)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=_serialise, ensure_ascii=False)

    logger.info(f"Exported JSON: {path}")
    return path


def generate_full_report(score_summary: dict,
                          gap_summary: dict,
                          recommendations_df: pd.DataFrame,
                          skill_freq_df: pd.DataFrame,
                          scores_df: pd.DataFrame) -> str:
    """
    Generate a comprehensive Excel report with multiple sheets.
    Returns the file path.
    """
    sheets = {}

    # Sheet 1: Score Summary
    summary_data = {k: v for k, v in score_summary.items()
                    if not isinstance(v, (pd.DataFrame, list))}
    sheets["Score Summary"] = pd.DataFrame([summary_data])

    # Sheet 2: All Job Scores
    if scores_df is not None and not scores_df.empty:
        sheets["Job Scores"] = scores_df

    # Sheet 3: Gap Summary
    gap_data = {k: v for k, v in gap_summary.items()
                if not isinstance(v, list)}
    sheets["Gap Summary"] = pd.DataFrame([gap_data])

    # Sheet 4: Recommendations
    if recommendations_df is not None and not recommendations_df.empty:
        sheets["Recommendations"] = recommendations_df

    # Sheet 5: Industry Skills
    if skill_freq_df is not None and not skill_freq_df.empty:
        sheets["Industry Skills"] = skill_freq_df.head(100)

    return export_excel(sheets, "ats_full_report.xlsx")
