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
    for line in lines:
        clean_line = line.strip().lower().rstrip(":")
        if clean_line in STANDARD_HEADINGS:
            found_headings.append(clean_line)
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
    has_email = bool(re.search(r"\S+@\S+\.\S+", text))
    has_phone = bool(re.search(r"[\+]?[\d\-\(\)\s]{7,15}", text))
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


def segment_resume_sections(resume_text: str) -> dict:
    """
    Basic rule-based resume section segmentation.
    Identifies standard sections by heading detection.

    Returns dict mapping section_name -> section_text
    """
    lines = resume_text.split("\n")
    sections = {}
    current_section = "header"
    current_lines = []

    heading_pattern = re.compile(
        r"^\s*("
        + "|".join(re.escape(h) for h in sorted(STANDARD_HEADINGS, key=len, reverse=True))
        + r")\s*:?\s*$",
        re.IGNORECASE
    )

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match:
            # Save previous section
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = match.group(1).lower().strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    logger.info(f"Section segmentation: {len(sections)} sections found ({', '.join(sections.keys())})")
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
        weight = SECTION_WEIGHTS.get(section_name, 0.4)
        weighted[section_name] = {
            "weight": weight,
            "text": text,
            "word_count": len(text.split()),
        }

    return weighted
