"""
Layout Processor Module — Text Repair & Normalization

Repairs text extracted from PDFs/DOCX by:
- Multi-column reconstruction using spatial clustering of bounding boxes
- Header/footer removal via cross-page pattern detection
- Broken-line repair (joining mid-sentence line breaks)
- Hyphenation resolution
- Bullet standardization
- Encoding normalization (mojibake, Unicode NFKC, smart quotes)
- Semantic paragraph restoration via spacing analysis
- Table-layout normalization
- Whitespace cleanup

Returns both raw and cleaned text. All repairs logged to anomaly list.
"""

import re
import unicodedata
import logging
from collections import Counter
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# ── Encoding Normalization ───────────────────────────────

def normalize_encoding(text: str, anomalies: list) -> str:
    """
    Fix encoding issues: mojibake, smart quotes, Unicode normalization.
    """
    original = text

    # 1. Unicode NFKC normalization (e.g., ﬁ → fi, ™ → TM)
    text = unicodedata.normalize("NFKC", text)

    # 2. Common mojibake repairs (UTF-8 interpreted as Latin-1)
    mojibake_map = {
        "â€™": "'", "â€˜": "'",
        "\xe2\x80\x9c": '"', "\xe2\x80\x9d": '"',
        "\xe2\x80\x93": "\u2013", "\xe2\x80\x94": "\u2014",
        "â€¢": "•", "Ã©": "é",
        "Ã¨": "è", "Ã¼": "ü",
        "Ã¶": "ö", "Ã¤": "ä",
        "Ã±": "ñ", "Ã§": "ç",
        "â€¦": "…",
    }
    for bad, good in mojibake_map.items():
        if bad in text:
            text = text.replace(bad, good)

    # 3. Smart quotes → straight quotes
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # single
    text = text.replace("\u201c", '"').replace("\u201d", '"')  # double
    text = text.replace("\u2013", "-").replace("\u2014", "-")  # dashes

    # 4. Remove null bytes and control characters (except newline, tab)
    text = re.sub(r'[\x00-\x08\x0b\x0e-\x1f\x7f]', '', text)

    if text != original:
        anomalies.append("ENCODING: Normalized encoding artifacts")

    return text


# ── Multi-Column Reconstruction ──────────────────────────

def reconstruct_reading_order(pages: list, anomalies: list) -> Optional[str]:
    """
    Reconstruct logical reading order from bounding-box data.
    Detects multi-column layouts by analyzing X-coordinate gaps.

    Parameters
    ----------
    pages : list of PageData
        Pages with word bounding boxes from pdfplumber.
    anomalies : list
        Anomaly log for recording detected issues.

    Returns
    -------
    str or None
        Reconstructed text in correct reading order, or None if
        no bounding-box data is available.
    """
    if not pages:
        return None

    all_text_parts = []
    columns_detected = False

    for page in pages:
        if not hasattr(page, 'words') or not page.words:
            if hasattr(page, 'text') and page.text:
                all_text_parts.append(page.text)
            continue

        words = page.words
        if not words:
            continue

        page_width = page.width if hasattr(page, 'width') and page.width else 612

        # Group words into lines by Y-coordinate (cluster by y0)
        lines = {}
        y_tolerance = 5.0
        for w in words:
            # Find or create a Y-cluster
            matched_y = None
            for existing_y in lines.keys():
                if abs(w.y0 - existing_y) < y_tolerance:
                    matched_y = existing_y
                    break
            if matched_y is None:
                matched_y = w.y0
                lines[matched_y] = []
            lines[matched_y].append(w)

        # Sort lines by Y, words within each line by X
        sorted_y_keys = sorted(lines.keys())
        for y in sorted_y_keys:
            lines[y].sort(key=lambda w: w.x0)

        # Detect columns: check if there's a consistent X-gap in the middle
        x_midpoints = []
        for y in sorted_y_keys:
            line_words = lines[y]
            if len(line_words) >= 2:
                for i in range(len(line_words) - 1):
                    gap = line_words[i + 1].x0 - line_words[i].x1
                    mid = (line_words[i].x1 + line_words[i + 1].x0) / 2
                    if gap > page_width * 0.05:  # Gap > 5% of page width
                        x_midpoints.append(mid)

        # If many lines have a gap around the same X, it's a two-column layout
        if x_midpoints:
            # Find the most common gap region (cluster midpoints)
            bins = {}
            bin_width = page_width * 0.05
            for mp in x_midpoints:
                bin_key = int(mp / bin_width)
                bins[bin_key] = bins.get(bin_key, 0) + 1

            if bins:
                most_common_bin = max(bins, key=bins.get)
                gap_count = bins[most_common_bin]

                # Consider it multi-column if > 30% of lines have the gap
                if gap_count > len(sorted_y_keys) * 0.3:
                    columns_detected = True
                    column_x = (most_common_bin + 0.5) * bin_width

                    # Split into left and right columns
                    left_lines = {}
                    right_lines = {}

                    for y in sorted_y_keys:
                        for w in lines[y]:
                            center_x = (w.x0 + w.x1) / 2
                            target = left_lines if center_x < column_x else right_lines
                            if y not in target:
                                target[y] = []
                            target[y].append(w)

                    # Build text: left column first (top to bottom), then right
                    for column_lines in [left_lines, right_lines]:
                        for y in sorted(column_lines.keys()):
                            col_words = sorted(column_lines[y], key=lambda w: w.x0)
                            line_text = " ".join(w.text for w in col_words)
                            if line_text.strip():
                                all_text_parts.append(line_text)
                        all_text_parts.append("")  # separator between columns

                    continue

        # Single column: just output lines in order
        for y in sorted_y_keys:
            line_text = " ".join(w.text for w in lines[y])
            if line_text.strip():
                all_text_parts.append(line_text)

    if columns_detected:
        anomalies.append("LAYOUT: Multi-column layout detected and reconstructed")

    return "\n".join(all_text_parts) if all_text_parts else None


# ── Header/Footer Removal ───────────────────────────────

def remove_headers_footers(text: str, anomalies: list) -> str:
    """
    Remove repeating header/footer lines across pages.
    Uses form-feed (\\x0c) as page delimiter.
    """
    pages = text.split('\x0c')
    if len(pages) <= 1:
        return text

    first_lines = []
    last_lines = []

    for page in pages:
        lines = [line.strip() for line in page.split('\n') if line.strip()]
        if lines:
            first_lines.append(lines[0])
            last_lines.append(lines[-1])

    threshold = max(2, len(pages) // 2)

    header_counts = Counter(first_lines)
    footer_counts = Counter(last_lines)

    repeating_headers = {
        line for line, count in header_counts.items()
        if count >= threshold and len(line) > 3
    }
    repeating_footers = {
        line for line, count in footer_counts.items()
        if count >= threshold and len(line) > 3
    }

    if not repeating_headers and not repeating_footers:
        return text

    if repeating_headers:
        anomalies.append(f"LAYOUT: Removed {len(repeating_headers)} repeating header pattern(s)")
    if repeating_footers:
        anomalies.append(f"LAYOUT: Removed {len(repeating_footers)} repeating footer pattern(s)")

    cleaned_pages = []
    for page in pages:
        lines = page.split('\n')

        start_idx = 0
        end_idx = len(lines)

        # Check first non-empty line
        for i, line in enumerate(lines):
            if line.strip():
                if line.strip() in repeating_headers:
                    start_idx = i + 1
                break

        # Check last non-empty line
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                if lines[i].strip() in repeating_footers:
                    end_idx = i
                break

        cleaned_pages.append('\n'.join(lines[start_idx:end_idx]))

    return '\x0c'.join(cleaned_pages)


# ── Hyphenation Repair ───────────────────────────────────

def repair_hyphenation(text: str, anomalies: list) -> str:
    """Join words split across lines with a hyphen: 'ex-\\ntraction' → 'extraction'."""
    count = len(re.findall(r'[a-z]-\s*\n\s*[a-z]', text, re.IGNORECASE))
    repaired = re.sub(
        r'([a-z])-\s*\n\s*([a-z])', r'\1\2',
        text, flags=re.IGNORECASE
    )
    if count > 0:
        anomalies.append(f"LAYOUT: Repaired {count} hyphenated line break(s)")
    return repaired


# ── Broken-Line Repair ──────────────────────────────────

def repair_broken_lines(text: str, anomalies: list) -> str:
    """
    Join lines that were broken mid-sentence.
    Heuristic: line ends without terminal punctuation AND next line
    starts with a lowercase letter → join them.
    """
    lines = text.split('\n')
    repaired = []
    join_count = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        if (i + 1 < len(lines)
            and stripped
            and not stripped[-1] in '.!?:;,|•'
            and not stripped.endswith('-')
            and len(stripped) > 20):  # Only for substantial lines

            next_line = lines[i + 1].lstrip()
            if next_line and next_line[0].islower():
                # Join lines
                repaired.append(stripped + ' ' + next_line)
                join_count += 1
                i += 2
                continue

        repaired.append(line)
        i += 1

    if join_count > 0:
        anomalies.append(f"LAYOUT: Repaired {join_count} broken line(s)")

    return '\n'.join(repaired)


# ── Bullet Standardization ──────────────────────────────

def standardize_bullets(text: str, anomalies: list) -> str:
    """Convert various bullet characters to a standard format."""
    # Count replacements
    bullet_pattern = r'^(\s*)[•\*·▪❖➢➔►▸◆○]\s+'
    bullet_count = len(re.findall(bullet_pattern, text, re.MULTILINE))

    standardized = re.sub(bullet_pattern, r'\1• ', text, flags=re.MULTILINE)

    # Dash-based bullets (only at start of line)
    dash_pattern = r'^(\s*)-\s+'
    dash_count = len(re.findall(dash_pattern, standardized, re.MULTILINE))
    standardized = re.sub(dash_pattern, r'\1• ', standardized, flags=re.MULTILINE)

    total = bullet_count + dash_count
    if total > 0:
        anomalies.append(f"LAYOUT: Standardized {total} bullet point(s)")

    return standardized


# ── Table-Layout Normalization ───────────────────────────

def normalize_table_layouts(text: str, anomalies: list) -> str:
    """
    Convert pipe-delimited 2-column table rows into key: value lines
    when the table clearly maps labels to values.
    """
    lines = text.split('\n')
    new_lines = []
    table_conv_count = 0

    for line in lines:
        if ' | ' in line:
            parts = [p.strip() for p in line.split(' | ') if p.strip()]
            # Two-column table with short label → key: value
            if len(parts) == 2 and len(parts[0]) < 30 and ':' not in parts[0]:
                new_lines.append(f"{parts[0]}: {parts[1]}")
                table_conv_count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if table_conv_count > 0:
        anomalies.append(f"LAYOUT: Normalized {table_conv_count} table row(s) to key-value format")

    return '\n'.join(new_lines)


# ── Paragraph Restoration ───────────────────────────────

def restore_paragraphs(text: str, anomalies: list) -> str:
    """
    Restore semantic paragraph structure.
    Collapse excessive blank lines, normalize spacing.
    """
    # Collapse 3+ newlines to 2 (paragraph break)
    collapsed = re.sub(r'\n{3,}', '\n\n', text)

    # Remove trailing whitespace from lines
    lines = [line.rstrip() for line in collapsed.split('\n')]
    result = '\n'.join(lines)

    return result


# ── Main Layout Repair Pipeline ──────────────────────────

def repair_layout(text: str, pages: list = None) -> Tuple[str, List[str]]:
    """
    Run full layout repair pipeline on extracted text.

    Parameters
    ----------
    text : str
        Raw extracted text.
    pages : list, optional
        List of PageData objects with bounding-box info for column reconstruction.

    Returns
    -------
    tuple of (cleaned_text, anomalies)
        Cleaned text and list of all anomalies/repairs logged.
    """
    if not text:
        return text, ["LAYOUT: Empty text, nothing to repair"]

    anomalies = []
    logger.info("Running layout repair pipeline...")
    length_before = len(text)

    # 1. Try multi-column reconstruction from bounding boxes
    if pages:
        reconstructed = reconstruct_reading_order(pages, anomalies)
        if reconstructed and len(reconstructed.strip()) > len(text.strip()) * 0.5:
            text = reconstructed
            anomalies.append("LAYOUT: Using bounding-box reconstructed text")

    # 2. Encoding normalization
    text = normalize_encoding(text, anomalies)

    # 3. Remove headers/footers
    text = remove_headers_footers(text, anomalies)

    # 4. Repair hyphenation
    text = repair_hyphenation(text, anomalies)

    # 5. Repair broken lines
    text = repair_broken_lines(text, anomalies)

    # 6. Standardize bullets
    text = standardize_bullets(text, anomalies)

    # 7. Normalize table layouts
    text = normalize_table_layouts(text, anomalies)

    # 8. Restore paragraphs & whitespace
    text = restore_paragraphs(text, anomalies)

    # 9. Strip form-feeds (pages already processed)
    text = text.replace('\x0c', '\n')

    logger.info(
        f"Layout repair complete "
        f"(before: {length_before}, after: {len(text)}, "
        f"repairs: {len(anomalies)})"
    )

    return text, anomalies
