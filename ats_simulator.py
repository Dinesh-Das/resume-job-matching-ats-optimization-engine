"""
ATS Simulation Engine
Evaluates resume machine readability by detecting formatting issues,
structural problems, and producing a parsing confidence score.
"""

import re
import logging

logger = logging.getLogger(__name__)


# ── Section Heading Patterns ──────────────────────
STANDARD_HEADINGS = [
    "summary", "objective", "professional summary", "career objective",
    "experience", "work experience", "professional experience", "employment",
    "education", "academic", "qualifications",
    "skills", "technical skills", "core competencies", "key skills",
    "certifications", "certificates", "licenses",
    "projects", "personal projects", "key projects",
    "awards", "achievements", "honors",
    "languages", "interests", "hobbies",
    "references", "publications",
    "contact", "contact information",
]

# ── Date Patterns ─────────────────────────────────
DATE_PATTERNS = [
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,]+\d{4}\b",
    r"\b\d{1,2}/\d{4}\b",
    r"\b\d{4}\s*[-–—]\s*(?:\d{4}|present|current|now)\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}\s*[-–—]\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}\b",
    r"\b\d{2}/\d{2}/\d{4}\b",
]


def detect_formatting_issues(resume_text: str, raw_bytes: bytes = None) -> list:
    """
    Detect ATS-unfriendly formatting in the resume.

    Returns a list of dicts: [{"issue": str, "severity": str, "detail": str}, ...]
    Severity: "high", "medium", "low"
    """
    issues = []
    text = resume_text or ""
    lines = text.split("\n")

    # 1. Multi-column layout detection
    # Heuristic: many lines with large whitespace gaps (tab or 4+ spaces in the middle)
    column_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped and re.search(r"\S\s{4,}\S", stripped):
            column_lines += 1
    if column_lines > len(lines) * 0.15 and column_lines > 5:
        issues.append({
            "issue": "Multi-column layout detected",
            "severity": "high",
            "detail": f"{column_lines} lines appear to have multi-column formatting. "
                      "Most ATS systems read left-to-right, which scrambles column-based layouts."
        })

    # 2. Table detection
    pipe_lines = sum(1 for l in lines if l.count("|") >= 2)
    tab_heavy_lines = sum(1 for l in lines if l.count("\t") >= 3)
    if pipe_lines > 3 or tab_heavy_lines > 3:
        issues.append({
            "issue": "Table structure detected",
            "severity": "high",
            "detail": "Tables are often misread by ATS parsers. Convert tabular data to "
                      "simple bullet points or comma-separated lists."
        })

    # 3. Section heading clarity
    found_headings = []
    
    # Track unique headings to avoid duplicates like "Experience" on multiple pages
    unique_headings = set()
    for line in lines:
        clean_line = line.strip().lower()
        # Only check reasonably short lines that might be headings
        if len(clean_line) > 0 and len(clean_line) < 60:
            for heading in STANDARD_HEADINGS:
                # If the line starts with the heading (or equals it)
                if clean_line.startswith(heading) or heading in clean_line:
                    unique_headings.add(heading)
                    break
                    
    found_headings = list(unique_headings)

    if len(found_headings) < 3:
        issues.append({
            "issue": "Missing standard section headings",
            "severity": "high",
            "detail": f"Found only {len(found_headings)} standard headings ({', '.join(found_headings) or 'none'}). "
                      "ATS systems rely on headings like 'Experience', 'Education', 'Skills' to parse sections."
        })

    # 4. Date parsing consistency
    dates_found = []
    for pattern in DATE_PATTERNS:
        dates_found.extend(re.findall(pattern, text, re.IGNORECASE))
    if not dates_found:
        issues.append({
            "issue": "No dates detected",
            "severity": "medium",
            "detail": "ATS systems expect date ranges for experience and education entries. "
                      "Use formats like 'Jan 2020 - Dec 2023' or 'MM/YYYY'."
        })

    # 5. Very short resume
    word_count = len(text.split())
    if word_count < 100:
        issues.append({
            "issue": "Resume is very short",
            "severity": "high",
            "detail": f"Only {word_count} words detected. Most ATS systems expect "
                      "400+ words for proper scoring."
        })
    elif word_count < 300:
        issues.append({
            "issue": "Resume is short",
            "severity": "medium",
            "detail": f"Only {word_count} words detected. Consider expanding to at least "
                      "400-600 words for better ATS coverage."
        })

    # 6. Excessive special characters / graphics indicators
    special_chars = len(re.findall(r"[^\w\s\-\.\,\;\:\!\?\(\)\@\#\$\%\&\*\/\\]", text))
    if special_chars > word_count * 0.1 and special_chars > 20:
        issues.append({
            "issue": "Excessive special characters or icons",
            "severity": "medium",
            "detail": f"{special_chars} non-standard characters found. Icons, emojis, and "
                      "decorative characters are often stripped or misread by ATS."
        })

    # 7. All-caps overuse (can confuse some parsers)
    all_caps_words = len(re.findall(r"\b[A-Z]{4,}\b", text))
    if all_caps_words > 15:
        issues.append({
            "issue": "Excessive ALL-CAPS usage",
            "severity": "low",
            "detail": f"{all_caps_words} all-caps words found. Some ATS systems may "
                      "misinterpret all-caps text. Use standard title case for headings."
        })

    # 8. Email and contact info presence
    # Robust email regex handling common extraction artifacts
    has_email = bool(re.search(r"[a-zA-Z0-9\.\-+_]+@[a-zA-Z0-9\.\-+_]+\.[a-zA-Z]+", text))
    
    # Robust phone regex (10-15 digits with optional spaces/dashes/parens in between, starting/ending with digit or +)
    phone_matches = re.findall(r"[\+\(]?\d[\d\s\-\(\)]{8,20}\d", text)
    # Validate that the match actually contains at least 9 numbers
    has_phone = any(sum(c.isdigit() for c in match) >= 9 for match in phone_matches)

    if not has_email:
        issues.append({
            "issue": "No email address detected",
            "severity": "medium",
            "detail": "Include a professional email address in the contact section."
        })
    if not has_phone:
        issues.append({
            "issue": "No phone number detected",
            "severity": "low",
            "detail": "Consider adding a phone number to the contact section."
        })

    # 9. Header/footer text loss (heuristic: first or last lines extremely short)
    if lines and len(lines[0].strip()) < 5 and len(lines) > 5:
        issues.append({
            "issue": "Possible header text loss",
            "severity": "low",
            "detail": "The first line of parsed text is very short, which may indicate "
                      "header content was lost during PDF extraction."
        })

    logger.info(f"ATS scan: {len(issues)} formatting issues detected")
    return issues


def compute_ats_parseability_score(resume_text: str, raw_bytes: bytes = None) -> dict:
    """
    Compute an ATS parseability score (0-100) based on detected formatting issues.

    Returns:
        {
            "score": float (0-100),
            "confidence": float (0-1),
            "issues": list,
            "summary": str
        }
    """
    issues = detect_formatting_issues(resume_text, raw_bytes)

    # Penalty weights
    SEVERITY_PENALTY = {"high": 15, "medium": 8, "low": 3}

    total_penalty = 0
    for issue in issues:
        total_penalty += SEVERITY_PENALTY.get(issue["severity"], 5)

    # Score = 100 - penalties (clamped to 0)
    score = max(0, min(100, 100 - total_penalty))

    # Confidence based on content quantity
    word_count = len(resume_text.split())
    if word_count > 300:
        confidence = 0.9
    elif word_count > 100:
        confidence = 0.7
    else:
        confidence = 0.4

    # Summary text
    high_count = sum(1 for i in issues if i["severity"] == "high")
    if high_count == 0 and score >= 80:
        summary = "Resume is well-formatted for ATS systems."
    elif high_count <= 1 and score >= 60:
        summary = "Resume has minor formatting issues that may affect ATS parsing."
    else:
        summary = "Resume has significant formatting issues that will likely cause ATS parsing errors."

    logger.info(f"ATS parseability score: {score:.1f} (confidence: {confidence:.1f})")

    return {
        "score": round(score, 1),
        "confidence": round(confidence, 2),
        "issues": issues,
        "summary": summary,
    }


def segment_resume_sections(resume_text: str, fuzzy_threshold: int = 85) -> dict:
    """
    Intelligent resume section segmentation using weighted heading detection.

    Scoring: fuzzy match (40%) + typography cues (30%) + spacing heuristics (30%).
    Falls back to semantic content classification for ambiguous headings.

    Parameters
    ----------
    resume_text : str
        Cleaned resume text.
    fuzzy_threshold : int
        Minimum fuzzy score (default 85, can be relaxed to 75 for reprocessing).

    Returns
    -------
    dict
        Maps section_name -> section_text. Also stores section metadata
        in the '_metadata' key: {section_name: {start_line, end_line,
        heading_text, heading_confidence, section_type}}.
    """
    from thefuzz import fuzz
    from config import STANDARD_HEADINGS as CONFIG_HEADINGS

    lines = resume_text.split("\n")
    sections = {}
    section_metadata = {}
    current_section = "header"
    current_lines = []
    current_start_line = 0

    # ── Semantic content keywords for classification ──
    SECTION_CONTENT_SIGNALS = {
        "experience": [
            "responsible for", "managed", "developed", "implemented",
            "led", "designed", "collaborated", "built", "created",
            "present", "current",
        ],
        "education": [
            "university", "college", "institute", "bachelor", "master",
            "ph.d", "diploma", "degree", "gpa", "graduated",
        ],
        "skills": [
            "proficient", "experienced in", "familiar with", "expertise",
            "technologies", "tools", "frameworks", "languages",
        ],
        "certifications": [
            "certified", "certification", "certificate", "credential",
            "aws certified", "pmp", "ccna",
        ],
    }

    # Date range pattern for detecting experience-like content
    date_range_re = re.compile(
        r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{2,4}\s*[-–—]\s*'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{2,4}|\d{4}\s*[-–—]\s*(?:\d{4}|present|current|now)\b',
        re.IGNORECASE
    )

    def _compute_heading_score(line: str, line_idx: int) -> tuple:
        """
        Compute composite heading score for a line.
        Returns (best_heading_match, composite_score, components).
        """
        cleaned = line.strip()
        if not cleaned or len(cleaned) > 60:
            return None, 0.0, {}

        cleaned_lower = cleaned.lower()
        # Remove trailing colon/dash
        if cleaned_lower.endswith(":") or cleaned_lower.endswith("-"):
            cleaned_lower = cleaned_lower[:-1].strip()

        # ── Typography Score (0-100) ──
        typography_score = 0
        alpha_chars = [c for c in cleaned if c.isalpha()]
        word_count = len(cleaned.split())

        # ALL CAPS = strong signal
        if len(alpha_chars) >= 3 and all(c.isupper() for c in alpha_chars):
            typography_score = 90

        # Title Case with few words = moderate signal
        elif cleaned.istitle() and word_count <= 4:
            typography_score = 60

        # Short line (1-5 words) = some signal
        elif word_count <= 5:
            typography_score = 40

        # ── Spacing Score (0-100) ──
        spacing_score = 0

        # Preceded by blank line = strong signal
        if line_idx > 0 and not lines[line_idx - 1].strip():
            spacing_score += 50

        # Followed by non-empty line (content follows heading)
        if line_idx < len(lines) - 1 and lines[line_idx + 1].strip():
            spacing_score += 30

        # First few lines = header likely
        if line_idx <= 3:
            spacing_score += 20

        spacing_score = min(100, spacing_score)

        # ── Fuzzy Match Score (0-100) ──
        best_match = None
        best_fuzzy = 0

        for heading in CONFIG_HEADINGS:
            score = fuzz.token_sort_ratio(cleaned_lower, heading.lower())
            if score > best_fuzzy:
                best_fuzzy = score
                best_match = heading

        # ── Composite Score ──
        # Weights: fuzzy 40%, typography 30%, spacing 30%
        composite = (best_fuzzy * 0.40) + (typography_score * 0.30) + (spacing_score * 0.30)

        if best_fuzzy >= fuzzy_threshold:
            return best_match, composite, {
                "fuzzy": best_fuzzy, "typography": typography_score,
                "spacing": spacing_score, "composite": composite
            }

        # Ambiguous zone (60-84): use semantic fallback
        if best_fuzzy >= 60 and composite >= 55:
            return best_match, composite, {
                "fuzzy": best_fuzzy, "typography": typography_score,
                "spacing": spacing_score, "composite": composite,
                "semantic_fallback": True
            }

        return None, composite, {}

    def _classify_content_semantically(text_block: str) -> str:
        """Classify a text block into a section type by content keywords."""
        text_lower = text_block.lower()
        best_section = None
        best_count = 0
        for section, keywords in SECTION_CONTENT_SIGNALS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_section = section
        # Also check for date ranges (strong experience signal)
        if date_range_re.search(text_block):
            if best_section != "education":
                best_section = "experience"
        return best_section

    # ── Main segmentation loop ──
    for i, line in enumerate(lines):
        matched_heading, score, components = _compute_heading_score(line, i)

        if matched_heading and score >= 50:
            # Save previous section
            if current_lines:
                section_text = "\n".join(current_lines).strip()
                sections[current_section] = section_text
                section_metadata[current_section] = {
                    "start_line": current_start_line,
                    "end_line": i - 1,
                    "heading_text": lines[current_start_line].strip() if current_start_line < len(lines) else "",
                    "heading_confidence": round(score / 100.0, 2),
                    "section_type": current_section,
                }

            current_section = matched_heading.lower().strip()
            current_lines = []
            current_start_line = i + 1
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        section_text = "\n".join(current_lines).strip()
        sections[current_section] = section_text
        section_metadata[current_section] = {
            "start_line": current_start_line,
            "end_line": len(lines) - 1,
            "heading_text": "",
            "heading_confidence": 0.5,
            "section_type": current_section,
        }

    # ── Post-process: detect missing headings via content classification ──
    if "experience" not in sections and "work experience" not in sections:
        # Check if header or any unnamed section contains experience content
        for section_name, text in list(sections.items()):
            if section_name == "header" and len(text) > 200:
                inferred = _classify_content_semantically(text)
                if inferred == "experience":
                    logger.info("Inferred 'experience' section from header content")
                    sections["experience"] = text
                    section_metadata["experience"] = section_metadata.get(section_name, {})
                    section_metadata["experience"]["section_type"] = "experience (inferred)"

    # Store metadata in a special key
    sections["_metadata"] = section_metadata

    section_names = [k for k in sections.keys() if k != "_metadata"]
    logger.info(f"Section segmentation: {len(section_names)} sections found ({', '.join(section_names)})")
    return sections


def extract_experience_years(resume_text: str) -> dict:
    """
    Extract years of experience from resume text using date range parsing.

    Returns:
        {
            "total_years": float,
            "date_ranges_found": int,
            "earliest_year": int or None,
            "latest_year": int or None,
            "confidence": float (0-1)
        }
    """
    import datetime

    years_found = []

    # Find all 4-digit years
    all_years = [int(y) for y in re.findall(r"\b(19|20)\d{2}\b", resume_text)]
    current_year = datetime.datetime.now().year

    # Filter reasonable years
    valid_years = [y for y in all_years if 1970 <= y <= current_year + 1]

    # Find date ranges like "2018 - 2023" or "2018 - present"
    range_pattern = r"\b((?:19|20)\d{2})\s*[-–—]+\s*((?:19|20)\d{2}|present|current|now)"
    ranges = re.findall(range_pattern, resume_text, re.IGNORECASE)

    total_years = 0
    for start_str, end_str in ranges:
        start = int(start_str)
        if end_str.lower() in ("present", "current", "now"):
            end = current_year
        else:
            end = int(end_str)
        if 1970 <= start <= current_year and start <= end <= current_year + 1:
            total_years += max(0, end - start)

    if not ranges and valid_years:
        # Fallback: estimate from year range
        total_years = max(valid_years) - min(valid_years) if len(valid_years) >= 2 else 0

    return {
        "total_years": round(total_years, 1),
        "date_ranges_found": len(ranges),
        "earliest_year": min(valid_years) if valid_years else None,
        "latest_year": max(valid_years) if valid_years else None,
        "confidence": 0.8 if ranges else (0.5 if valid_years else 0.2),
    }


# ── Seniority Levels ─────────────────────────────
SENIORITY_KEYWORDS = {
    "intern": 0, "trainee": 0, "apprentice": 0,
    "junior": 1, "associate": 1, "entry": 1,
    "mid": 2, "intermediate": 2,
    "senior": 3, "lead": 3, "staff": 3, "principal": 3,
    "manager": 4, "director": 4, "head": 4,
    "vp": 5, "vice president": 5, "cto": 5, "ceo": 5, "cio": 5, "chief": 5,
}


def analyze_career_progression(resume_text: str) -> dict:
    """
    Analyze career progression from resume text.

    Returns:
        {
            "seniority_level": int (0-5),
            "seniority_trend": str ("ascending" | "flat" | "descending" | "unknown"),
            "role_titles_found": list[str],
            "domain_keywords": list[str],
            "domain_continuity": float (0-1),
        }
    """
    text_lower = resume_text.lower()

    # Detect seniority keywords
    found_levels = []
    for keyword, level in SENIORITY_KEYWORDS.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
            found_levels.append(level)

    current_seniority = max(found_levels) if found_levels else 1
    min_seniority = min(found_levels) if found_levels else 1

    # Determine trend
    if len(found_levels) < 2:
        trend = "unknown"
    elif current_seniority > min_seniority:
        trend = "ascending"
    elif current_seniority == min_seniority:
        trend = "flat"
    else:
        trend = "descending"

    # Extract role titles (common patterns)
    title_patterns = [
        r"(?:^|\n)\s*((?:senior|junior|lead|staff|principal|associate)?\s*(?:software|data|devops|cloud|ml|ai|full[\s-]?stack|front[\s-]?end|back[\s-]?end|mobile|qa|test|security|network|systems?|database|bi|analytics|product|project|program|ux|ui)\s*(?:engineer|developer|architect|analyst|scientist|manager|lead|specialist|consultant|administrator|designer|coordinator))",
        r"(?:^|\n)\s*((?:senior|junior|lead|head|chief)?\s*(?:technical|engineering|technology|it|development)?\s*(?:manager|director|vp|vice president|officer|head))",
    ]
    role_titles = []
    for pattern in title_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        role_titles.extend([m.strip() for m in matches if len(m.strip()) > 5])
    role_titles = list(set(role_titles))[:10]

    # Domain continuity: check if roles share common domain keywords
    domain_terms = ["software", "data", "devops", "cloud", "ml", "ai", "web",
                    "mobile", "security", "network", "product", "analytics"]
    found_domains = [d for d in domain_terms if d in text_lower]

    # Continuity = fraction of roles mentioning the most common domain
    domain_continuity = 0.5  # default
    if found_domains and role_titles:
        from collections import Counter
        domain_counts = Counter()
        for title in role_titles:
            for d in domain_terms:
                if d in title:
                    domain_counts[d] += 1
        if domain_counts:
            most_common_count = domain_counts.most_common(1)[0][1]
            domain_continuity = min(1.0, most_common_count / max(len(role_titles), 1))

    logger.info(f"Career progression: seniority={current_seniority}, trend={trend}, "
                f"{len(role_titles)} roles, continuity={domain_continuity:.2f}")

    return {
        "seniority_level": current_seniority,
        "seniority_trend": trend,
        "role_titles_found": role_titles,
        "domain_keywords": found_domains,
        "domain_continuity": round(domain_continuity, 2),
    }


def compute_section_weights(resume_text: str) -> dict:
    """
    Compute section-weighted skill distribution from segmented resume.
    Higher weight for skills, recent experience, job titles, and summary.

    Returns dict: section_name -> weight (0-1 multiplier)
    """
    SECTION_WEIGHTS = {
        "skills": 1.0,
        "technical skills": 1.0,
        "core competencies": 1.0,
        "key skills": 1.0,
        "experience": 0.85,
        "work experience": 0.85,
        "professional experience": 0.85,
        "employment": 0.85,
        "summary": 0.7,
        "professional summary": 0.7,
        "objective": 0.6,
        "career objective": 0.6,
        "projects": 0.65,
        "personal projects": 0.65,
        "key projects": 0.65,
        "education": 0.5,
        "certifications": 0.55,
        "certificates": 0.55,
        "header": 0.3,
    }

    sections = segment_resume_sections(resume_text)
    weighted = {}
    for section_name, text in sections.items():
        if section_name == "_metadata":
            continue
        weight = SECTION_WEIGHTS.get(section_name, 0.4)
        weighted[section_name] = {
            "weight": weight,
            "text": text,
            "word_count": len(text.split()),
        }

    return weighted
