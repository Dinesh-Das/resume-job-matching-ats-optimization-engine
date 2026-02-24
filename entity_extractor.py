"""
Entity Extractor Module — Structured Resume Data Extraction

Hybrid extraction using regex, rule-based parsing, dictionary matching, and NLP:
- Name, contact info, professional summary
- Employment history with date anchoring, duration inference, title taxonomy
- Education with degree/institution/year parsing
- Certifications via regex patterns
- Projects and publications
- Skill taxonomy mapping with semantic deduplication
- Per-field confidence scoring and traceability
- Cross-field validation and anomaly reporting
- Automatic reprocessing for low-confidence results
"""

import re
import logging
import dateparser
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Source Traceability ──────────────────────────────────

def _make_source(section: str, line_range: Tuple[int, int] = None,
                 text_snippet: str = "") -> Dict[str, Any]:
    """Create a traceability source dict."""
    src = {"section": section}
    if line_range:
        src["line_range"] = list(line_range)
    if text_snippet:
        src["text_snippet"] = text_snippet[:200]  # Cap snippet length
    return src


# ── Name Extraction ──────────────────────────────────────

def extract_name(header_text: str, full_text: str) -> Dict[str, Any]:
    """
    Extract candidate name using positional heuristic + NLP validation.
    Strategy: first non-empty line that doesn't look like contact info.
    """
    result = {"name": None, "confidence": 0.0, "source": {}, "anomalies": []}

    lines = [l.strip() for l in (header_text or full_text[:500]).split("\n") if l.strip()]
    if not lines:
        result["anomalies"].append("NAME: No text available for name extraction")
        return result

    # Skip lines that look like contact info
    contact_patterns = [
        r'@',           # email
        r'\d{3}',       # phone fragments
        r'linkedin',    # URLs
        r'github',
        r'http',
        r'www\.',
        r'\d{5}',       # zip codes
    ]

    candidate_line = None
    for i, line in enumerate(lines[:5]):  # Check first 5 lines
        is_contact = any(re.search(p, line, re.IGNORECASE) for p in contact_patterns)
        if is_contact:
            continue
        # Name should be reasonably short (1-5 words) and mostly alphabetic
        words = line.split()
        if 1 <= len(words) <= 5:
            alpha_ratio = sum(c.isalpha() or c == ' ' for c in line) / max(len(line), 1)
            if alpha_ratio > 0.8:
                candidate_line = line
                result["source"] = _make_source("header", (i, i), line)
                break

    if candidate_line:
        # Clean up — remove trailing commas, periods
        name = candidate_line.strip().rstrip('.,;:')

        # Validate with spaCy NER if available
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm", disable=["parser", "textcat"])
            doc = nlp(name)
            person_ents = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            if person_ents:
                result["name"] = person_ents[0]
                result["confidence"] = 0.95
            else:
                # NER didn't confirm, but positional heuristic is still good
                result["name"] = name
                result["confidence"] = 0.75
        except (ImportError, OSError):
            # No spaCy — use positional heuristic only
            result["name"] = name
            result["confidence"] = 0.70
    else:
        result["anomalies"].append("NAME: Could not identify name from header")

    return result


# ── Contact Info Extraction ──────────────────────────────

def extract_contact_info(text: str) -> Dict[str, Any]:
    """Extract email, phone, LinkedIn, GitHub, portfolio with confidence."""
    contact = {
        "email": None, "phone": None, "linkedin": None,
        "github": None, "portfolio": None,
        "confidence": 0.0, "source": _make_source("header"),
        "anomalies": []
    }

    # Email
    email_match = re.search(
        r"([a-zA-Z0-9.\-+_]+@[a-zA-Z0-9.\-+_]+\.[a-zA-Z]{2,})", text
    )
    if email_match:
        email = email_match.group(1).lower()
        # Validate format
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            contact["email"] = email
            contact["confidence"] += 0.3
        else:
            contact["anomalies"].append(f"CONTACT: Invalid email format: {email}")
    else:
        contact["anomalies"].append("CONTACT: No email address found")

    # Phone
    phone_pattern = r"(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{0,4})"
    for match in re.finditer(phone_pattern, text):
        phone_str = match.group(1)
        digits = sum(c.isdigit() for c in phone_str)
        if 7 <= digits <= 15:
            contact["phone"] = phone_str.strip()
            contact["confidence"] += 0.25
            break
    if not contact["phone"]:
        contact["anomalies"].append("CONTACT: No phone number found")

    # URLs
    url_pattern = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)"
    urls = re.findall(url_pattern, text)

    for url in urls:
        url_clean = url.rstrip('.,;:)')
        url_lower = url_clean.lower()

        if "linkedin.com" in url_lower and not contact["linkedin"]:
            contact["linkedin"] = url_clean
            contact["confidence"] += 0.15
        elif "github.com" in url_lower and not contact["github"]:
            contact["github"] = url_clean
            contact["confidence"] += 0.15
        elif not contact["portfolio"] and "@" not in url_lower:
            contact["portfolio"] = url_clean

    contact["confidence"] = round(min(1.0, contact["confidence"]), 2)
    return contact


# ── Professional Summary Extraction ──────────────────────

def extract_summary(summary_section: str) -> Dict[str, Any]:
    """Extract professional summary, truncated to ~5 sentences."""
    result = {"text": None, "confidence": 0.0, "source": {}, "anomalies": []}

    if not summary_section or len(summary_section.strip()) < 20:
        result["anomalies"].append("SUMMARY: No summary section found or too short")
        return result

    # Take first 5 sentences
    sentences = re.split(r'(?<=[.!?])\s+', summary_section.strip())
    summary = ' '.join(sentences[:5]).strip()

    if summary:
        result["text"] = summary
        result["confidence"] = 0.85 if len(sentences) >= 2 else 0.6
        result["source"] = _make_source("summary", text_snippet=summary[:100])

    return result


# ── Education Extraction ─────────────────────────────────

def extract_education(education_section: str) -> List[Dict[str, Any]]:
    """Parse education section into structured entries with confidence."""
    if not education_section:
        return []

    entries = []
    lines = [l.strip() for l in education_section.split("\n") if l.strip()]
    current = {}

    degree_patterns = [
        r"\b(Ph\.?D\.?|Doctorate|Doctor\s+of\s+\w+)\b",
        r"\b(M\.?B\.?A\.?)\b",
        r"\b(M\.?S\.?|M\.?A\.?|M\.?E\.?|M\.?Tech|Master[s]?\s+(?:of|in)\s+[A-Za-z\s]+)\b",
        r"\b(B\.?S\.?|B\.?A\.?|B\.?E\.?|B\.?Tech|Bachelor[s]?\s+(?:of|in)\s+[A-Za-z\s]+)\b",
        r"\b(A\.?A\.?|A\.?S\.?|Associate[s]?\s+(?:of|in)\s+[A-Za-z\s]+)\b",
        r"\b(Diploma\s+in\s+[A-Za-z\s]+)\b",
    ]

    institution_keywords = [
        "university", "college", "institute", "school", "academy",
        "polytechnic", "iit", "mit", "stanford", "harvard",
    ]

    for line_idx, line in enumerate(lines):
        line_lower = line.lower()

        # Degree detection
        found_degree = False
        for pattern in degree_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if current.get("degree"):
                    entries.append(current)
                    current = {}
                current["degree"] = match.group(1).strip()
                current["source"] = _make_source("education", (line_idx, line_idx), line)
                found_degree = True
                break

        # Year detection
        year_match = re.search(r"\b((?:19|20)\d{2})\b", line)
        if year_match:
            current["graduation_year"] = year_match.group(1)

        # Institution detection
        if any(kw in line_lower for kw in institution_keywords):
            if current.get("institution") and current.get("degree"):
                entries.append(current)
                current = {}
            current["institution"] = line

        # GPA detection
        gpa_match = re.search(r"(?:gpa|cgpa|grade)[:\s]*(\d+\.?\d*)\s*/?\s*(\d+\.?\d*)?", line_lower)
        if gpa_match:
            current["gpa"] = gpa_match.group(1)
            if gpa_match.group(2):
                current["gpa_scale"] = gpa_match.group(2)

    if current.get("degree") or current.get("institution"):
        entries.append(current)

    # Confidence scoring
    for entry in entries:
        conf = 0.0
        if entry.get("degree"):
            conf += 0.4
        if entry.get("institution"):
            conf += 0.3
        if entry.get("graduation_year"):
            conf += 0.2
        if entry.get("gpa"):
            conf += 0.1
        entry["confidence"] = round(min(1.0, conf), 2)
        if "source" not in entry:
            entry["source"] = _make_source("education")

    return entries


# ── Certification Extraction ─────────────────────────────

def extract_certifications(text: str, cert_section: str = None) -> List[Dict[str, Any]]:
    """Extract certifications using regex patterns from config."""
    from config import CERTIFICATION_PATTERNS

    search_text = cert_section if cert_section else text
    certs = []
    seen = set()

    for pattern in CERTIFICATION_PATTERNS:
        try:
            for match in re.finditer(pattern, search_text, re.IGNORECASE):
                cert_name = match.group(0).strip()
                cert_key = cert_name.lower()
                if cert_key not in seen:
                    seen.add(cert_key)
                    certs.append({
                        "name": cert_name,
                        "confidence": 0.85,
                        "source": _make_source(
                            "certifications" if cert_section else "full_text",
                            text_snippet=cert_name
                        ),
                    })
        except re.error as e:
            logger.warning(f"Invalid certification pattern: {e}")

    return certs


# ── Employment History Extraction ────────────────────────

def extract_employment_history(experience_section: str) -> List[Dict[str, Any]]:
    """
    Extract employment history with date anchoring, duration inference,
    title taxonomy mapping, and per-entry confidence.
    """
    if not experience_section:
        return []

    from config import TITLE_TAXONOMY

    jobs = []
    lines = [l.strip() for l in experience_section.split("\n") if l.strip()]

    # Date range pattern
    date_range_re = re.compile(
        r'\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{2,4}'
        r'|\d{1,2}/\d{2,4}|\d{4})'
        r'\s*[-\u2013\u2014to]+\s*'
        r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{2,4}'
        r'|\d{1,2}/\d{2,4}|\d{4}|present|current|now)\b',
        re.IGNORECASE
    )

    current_job = {
        "title": None, "company": None,
        "start_date": None, "end_date": None,
        "duration_months": None, "is_current": False,
        "canonical_level": None,
        "responsibilities": [],
        "source": {}, "anomalies": []
    }

    for i, line in enumerate(lines):
        date_match = date_range_re.search(line)

        if date_match:
            # Save previous job if it has content
            if current_job["title"] or current_job["responsibilities"]:
                current_job["responsibilities"] = list(current_job["responsibilities"])
                jobs.append(current_job)

            current_job = {
                "title": None, "company": None,
                "start_date": None, "end_date": None,
                "duration_months": None, "is_current": False,
                "canonical_level": None,
                "responsibilities": [],
                "source": _make_source("experience", (i, i), line),
                "anomalies": []
            }

            current_job["start_date"] = date_match.group(1).strip()
            current_job["end_date"] = date_match.group(2).strip()

            # Check if current role
            if current_job["end_date"].lower() in ("present", "current", "now"):
                current_job["is_current"] = True

            # Duration inference
            try:
                dt_start = dateparser.parse(current_job["start_date"])
                if current_job["is_current"]:
                    dt_end = dateparser.parse("today")
                else:
                    dt_end = dateparser.parse(current_job["end_date"])

                if dt_start and dt_end:
                    delta = (dt_end.year - dt_start.year) * 12 + (dt_end.month - dt_start.month)
                    current_job["duration_months"] = max(0, delta)

                    if dt_start > dt_end:
                        current_job["anomalies"].append(
                            f"CHRONOLOGY: Start date after end date ({current_job['start_date']} > {current_job['end_date']})"
                        )
            except Exception:
                pass

            # Extract title/company from context lines
            context = []
            if i > 0:
                context.append(lines[i - 1])
            remainder = line.replace(date_match.group(0), "").strip(" ,|-\u2013\u2014")
            if remainder:
                context.append(remainder)
            if i < len(lines) - 1:
                context.append(lines[i + 1])

            for cl in context:
                cl_clean = cl.strip()
                if not cl_clean or len(cl_clean) < 3:
                    continue
                # Skip bullet points
                if cl_clean.startswith(("\u2022", "-", "*")):
                    continue
                if not current_job["title"] and len(cl_clean) > 5:
                    current_job["title"] = cl_clean
                elif not current_job["company"] and len(cl_clean) > 3:
                    current_job["company"] = cl_clean

            # Map title to canonical seniority level
            if current_job["title"]:
                title_lower = current_job["title"].lower()
                best_level = None
                for keyword, level in TITLE_TAXONOMY.items():
                    if keyword in title_lower:
                        if best_level is None or level > best_level:
                            best_level = level
                current_job["canonical_level"] = best_level

            continue

        # Responsibility/detail lines (bullet points or lines within a job block)
        if current_job["start_date"]:
            # Clean bullet prefix
            clean_line = re.sub(r'^[\u2022\-\*]\s*', '', line)
            if clean_line:
                current_job["responsibilities"].append(clean_line)

    # Save last job
    if current_job["title"] or current_job["responsibilities"]:
        current_job["responsibilities"] = list(current_job["responsibilities"])
        jobs.append(current_job)

    # ── Confidence scoring for each job ──
    for job in jobs:
        conf = 0.0
        if job.get("start_date") and job.get("end_date"):
            conf += 0.35
        if job.get("title"):
            conf += 0.25
        if job.get("company"):
            conf += 0.15
        if job.get("responsibilities"):
            conf += 0.15
        if job.get("duration_months") is not None:
            conf += 0.10

        # Penalty for chronological issues
        if any("CHRONOLOGY" in a for a in job.get("anomalies", [])):
            conf -= 0.25

        job["confidence"] = round(max(0.0, min(1.0, conf)), 2)

    return jobs


# ── Projects Extraction ──────────────────────────────────

def extract_projects(projects_section: str) -> List[Dict[str, Any]]:
    """Extract project entries with name, description, technologies."""
    if not projects_section:
        return []

    projects = []
    lines = [l.strip() for l in projects_section.split("\n") if l.strip()]

    current_project = {"name": None, "description": "", "technologies": []}

    for line in lines:
        # Project name heuristic: short line (1-8 words) not starting with bullet
        is_bullet = line.startswith(("\u2022", "-", "*"))
        words = line.split()

        if not is_bullet and 1 <= len(words) <= 10 and not line[0].islower():
            if current_project["name"]:
                projects.append(current_project)
            current_project = {"name": line, "description": "", "technologies": []}
        elif is_bullet or line[0].islower() if line else False:
            desc_line = re.sub(r'^[\u2022\-\*]\s*', '', line)
            current_project["description"] += desc_line + " "

            # Extract tech mentions
            tech_pattern = r"(?:using|built with|technologies?|tools?|stack)\s*:?\s*(.+)"
            tech_match = re.search(tech_pattern, desc_line, re.IGNORECASE)
            if tech_match:
                techs = [t.strip() for t in re.split(r'[,;|]', tech_match.group(1)) if t.strip()]
                current_project["technologies"].extend(techs)

    if current_project["name"]:
        projects.append(current_project)

    for p in projects:
        p["description"] = p["description"].strip()
        p["confidence"] = 0.7 if p["description"] else 0.4

    return projects


# ── Publications Extraction ──────────────────────────────

def extract_publications(publications_section: str) -> List[Dict[str, Any]]:
    """Extract publications/research entries."""
    if not publications_section:
        return []

    pubs = []
    lines = [l.strip() for l in publications_section.split("\n") if l.strip()]

    for line in lines:
        if len(line) < 15:
            continue

        pub = {"title": line, "venue": None, "year": None, "confidence": 0.5}

        # Try to find year
        year_match = re.search(r'\b((?:19|20)\d{2})\b', line)
        if year_match:
            pub["year"] = year_match.group(1)
            pub["confidence"] += 0.15

        # Try to find venue markers
        venue_patterns = [
            r"(?:in|published\s+in|presented\s+at)\s+(.+?)(?:\d{4}|$)",
            r"(?:journal|conference|proceedings|workshop)\s+(?:of|on)\s+(.+?)(?:\d{4}|$)",
        ]
        for vp in venue_patterns:
            vm = re.search(vp, line, re.IGNORECASE)
            if vm:
                pub["venue"] = vm.group(1).strip().rstrip('.,;')
                pub["confidence"] += 0.15
                break

        pub["confidence"] = round(min(1.0, pub["confidence"]), 2)
        pubs.append(pub)

    return pubs


# ── Skill Taxonomy Mapping & Deduplication ───────────────

def map_skills_to_taxonomy(skills: List[str]) -> List[Dict[str, Any]]:
    """Map extracted skills to canonical categories and deduplicate."""
    from config import SKILL_TAXONOMY, SYNONYM_MAP

    mapped = []
    seen_canonical = set()

    for skill in skills:
        skill_lower = skill.lower().strip()

        # Resolve synonyms first
        canonical = SYNONYM_MAP.get(skill_lower, skill_lower)

        # Skip duplicates
        if canonical in seen_canonical:
            continue
        seen_canonical.add(canonical)

        category = SKILL_TAXONOMY.get(canonical, "Other")

        mapped.append({
            "name": canonical,
            "category": category,
            "original": skill if skill.lower() != canonical else None,
            "confidence": 0.95 if canonical in SKILL_TAXONOMY else 0.7,
        })

    return mapped


def deduplicate_skills_semantic(skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove near-duplicate skills using Levenshtein distance.
    E.g., 'machine learning' and 'machinelearning' → keep one.
    """
    if len(skills) <= 1:
        return skills

    deduped = []
    seen_names = []

    for skill in skills:
        name = skill["name"].lower().replace(" ", "").replace("-", "")
        is_dup = False
        for existing in seen_names:
            # Simple char-level similarity
            if name == existing:
                is_dup = True
                break
            # Check if one is substring of the other
            if name in existing or existing in name:
                if abs(len(name) - len(existing)) <= 3:
                    is_dup = True
                    break
        if not is_dup:
            deduped.append(skill)
            seen_names.append(name)

    return deduped


# ── Cross-Field Validation ───────────────────────────────

def validate_structured_output(result: Dict[str, Any]) -> List[str]:
    """
    Cross-field logical validation.
    Returns list of anomalies found.
    """
    anomalies = []

    # 1. Chronological order of employment
    jobs = result.get("employment_history", [])
    if len(jobs) >= 2:
        for i in range(len(jobs) - 1):
            j1 = jobs[i]
            j2 = jobs[i + 1]
            if j1.get("start_date") and j2.get("start_date"):
                try:
                    d1 = dateparser.parse(j1["start_date"])
                    d2 = dateparser.parse(j2["start_date"])
                    if d1 and d2 and d2 > d1:
                        anomalies.append(
                            f"VALIDATION: Jobs may not be in reverse chronological order "
                            f"({j1.get('title', '?')} before {j2.get('title', '?')})"
                        )
                except Exception:
                    pass

    # 2. Education year should be before first job (soft check)
    edu = result.get("education", [])
    if edu and jobs:
        for e in edu:
            grad_year = e.get("graduation_year")
            if grad_year:
                try:
                    grad_y = int(grad_year)
                    for j in jobs:
                        if j.get("start_date"):
                            dt_start = dateparser.parse(j["start_date"])
                            if dt_start and grad_y > dt_start.year + 5:
                                anomalies.append(
                                    f"VALIDATION: Education year {grad_y} seems after "
                                    f"job start {dt_start.year}"
                                )
                            break
                except (ValueError, TypeError):
                    pass

    # 3. Exactly one current role
    current_roles = [j for j in jobs if j.get("is_current")]
    if len(current_roles) > 1:
        anomalies.append(
            f"VALIDATION: Multiple current roles detected ({len(current_roles)})"
        )

    # 4. Duration sanity
    for j in jobs:
        dur = j.get("duration_months")
        if dur is not None and dur > 360:  # >30 years at one job
            anomalies.append(
                f"VALIDATION: Unusually long tenure ({dur} months) at {j.get('company', '?')}"
            )

    # 5. Name present
    if not result.get("name"):
        anomalies.append("VALIDATION: No candidate name extracted")

    # 6. Email present
    contact = result.get("contact_info", {})
    if not contact.get("email"):
        anomalies.append("VALIDATION: No email address extracted")

    # 7. Duplicate job titles + companies
    job_sigs = []
    for j in jobs:
        sig = f"{(j.get('title') or '').lower()}|{(j.get('company') or '').lower()}"
        if sig in job_sigs and sig != "|":
            anomalies.append(f"VALIDATION: Duplicate job entry detected: {sig}")
        job_sigs.append(sig)

    return anomalies


# ── Overall Confidence Computation ───────────────────────

def compute_overall_confidence(result: Dict[str, Any]) -> float:
    """
    Weighted average of all field confidence scores.
    Returns 0.0–1.0.
    """
    scores = []
    weights = []

    # Name
    name_result = result.get("_name_result", {})
    if name_result.get("confidence"):
        scores.append(name_result["confidence"])
        weights.append(2.0)

    # Contact
    contact = result.get("contact_info", {})
    if contact.get("confidence"):
        scores.append(contact["confidence"])
        weights.append(2.0)

    # Employment
    for job in result.get("employment_history", []):
        if job.get("confidence"):
            scores.append(job["confidence"])
            weights.append(1.5)

    # Education
    for edu in result.get("education", []):
        if edu.get("confidence"):
            scores.append(edu["confidence"])
            weights.append(1.0)

    # Certifications
    for cert in result.get("certifications", []):
        if cert.get("confidence"):
            scores.append(cert["confidence"])
            weights.append(0.5)

    if not scores:
        return 0.0

    weighted_sum = sum(s * w for s, w in zip(scores, weights))
    total_weight = sum(weights)
    return round(weighted_sum / total_weight, 2)


# ── Master Pipeline ──────────────────────────────────────

def build_structured_resume(
    resume_text: str,
    skills: List[str] = None,
    raw_text: str = None,
    sections_override: Dict = None,
    metadata: Dict = None,
    reprocess: bool = True
) -> Dict[str, Any]:
    """
    Master function: parse full resume text into a standardized structured schema.

    Parameters
    ----------
    resume_text : str
        Cleaned resume text.
    skills : list, optional
        Pre-extracted skills list.
    raw_text : str, optional
        Original raw text (for traceability).
    sections_override : dict, optional
        Pre-segmented sections (skip segmentation).
    metadata : dict, optional
        Extraction metadata from resume_parser.
    reprocess : bool
        Whether to attempt reprocessing on low confidence.

    Returns
    -------
    dict
        Full structured resume schema with confidence scores and traceability.
    """
    from ats_simulator import segment_resume_sections
    from skill_extractor import extract_skills_from_text

    logger.info("Building structured resume schema...")
    anomalies = []

    # ── Section Segmentation ──
    if sections_override:
        sections = sections_override
    else:
        sections = segment_resume_sections(resume_text)

    section_metadata = sections.pop("_metadata", {})

    # ── Header / Contact Info ──
    header_text = sections.get("header", "")
    if len(header_text) < 100:
        header_text = resume_text[:1000]

    # Name
    name_result = extract_name(header_text, resume_text)
    anomalies.extend(name_result.get("anomalies", []))

    # Contact
    contact_info = extract_contact_info(header_text)
    anomalies.extend(contact_info.pop("anomalies", []))

    # ── Summary ──
    summary_text = (
        sections.get("summary", "") or
        sections.get("professional summary", "") or
        sections.get("executive summary", "") or
        sections.get("objective", "") or
        sections.get("career objective", "") or
        sections.get("profile", "")
    )
    summary_result = extract_summary(summary_text)
    anomalies.extend(summary_result.pop("anomalies", []))

    # ── Education ──
    education_text = (
        sections.get("education", "") or
        sections.get("academic background", "") or
        sections.get("qualifications", "") or
        sections.get("academic qualifications", "")
    )
    education = extract_education(education_text)

    # ── Employment History ──
    experience_text = (
        sections.get("experience", "") or
        sections.get("work experience", "") or
        sections.get("professional experience", "") or
        sections.get("employment", "") or
        sections.get("employment history", "") or
        sections.get("work history", "") or
        sections.get("career history", "")
    )
    employment = extract_employment_history(experience_text)

    # ── Certifications ──
    cert_text = (
        sections.get("certifications", "") or
        sections.get("licenses", "") or
        sections.get("credentials", "") or
        sections.get("professional certifications", "")
    )
    certifications = extract_certifications(resume_text, cert_text or None)

    # ── Projects ──
    projects_text = (
        sections.get("projects", "") or
        sections.get("key projects", "") or
        sections.get("personal projects", "") or
        sections.get("academic projects", "")
    )
    projects = extract_projects(projects_text)

    # ── Publications ──
    pub_text = (
        sections.get("publications", "") or
        sections.get("research", "") or
        sections.get("papers", "")
    )
    publications = extract_publications(pub_text)

    # ── Skills ──
    if skills is None:
        # Extract from skills section first, then full text
        skills_text = (
            sections.get("skills", "") or
            sections.get("technical skills", "") or
            sections.get("core competencies", "") or
            sections.get("key skills", "") or
            sections.get("areas of expertise", "")
        )
        skills = extract_skills_from_text(skills_text or resume_text)

    # Map to taxonomy & deduplicate
    mapped_skills = map_skills_to_taxonomy(skills)
    mapped_skills = deduplicate_skills_semantic(mapped_skills)

    # ── Build Result ──
    result = {
        "name": name_result.get("name"),
        "contact_info": contact_info,
        "professional_summary": summary_result.get("text"),
        "skills": mapped_skills,
        "employment_history": employment,
        "education": education,
        "certifications": certifications,
        "projects": projects,
        "publications": publications,
        "_name_result": name_result,  # For confidence computation
        "metadata": {
            "extraction_method": (metadata or {}).get("extraction_method", "unknown"),
            "raw_text": raw_text or resume_text,
            "cleaned_text": resume_text,
            "sections_detected": {
                k: {
                    "start_line": v.get("start_line"),
                    "end_line": v.get("end_line"),
                    "confidence": v.get("heading_confidence", 0.5)
                }
                for k, v in section_metadata.items()
            },
            "reprocessed": False,
            "anomalies": [],
        }
    }

    # ── Cross-Field Validation ──
    validation_anomalies = validate_structured_output(result)
    anomalies.extend(validation_anomalies)

    # ── Overall Confidence ──
    overall_confidence = compute_overall_confidence(result)
    result["metadata"]["overall_confidence"] = overall_confidence
    result["metadata"]["anomalies"] = anomalies

    # ── Auto-Reprocessing ──
    if reprocess and overall_confidence < 0.5:
        logger.warning(
            f"Overall confidence {overall_confidence:.2f} < 0.5 — "
            "attempting reprocessing with relaxed thresholds..."
        )
        # Retry with relaxed fuzzy threshold
        relaxed_sections = segment_resume_sections(resume_text, fuzzy_threshold=75)
        relaxed_sections.pop("_metadata", None)

        # Only reprocess if we get more sections
        orig_section_count = len(sections)
        new_section_count = len(relaxed_sections)

        if new_section_count > orig_section_count:
            logger.info(
                f"Reprocessing found {new_section_count} sections "
                f"(vs {orig_section_count} originally)"
            )
            # Re-run with relaxed sections
            result_v2 = build_structured_resume(
                resume_text, skills=skills, raw_text=raw_text,
                sections_override=relaxed_sections, metadata=metadata,
                reprocess=False  # Prevent infinite recursion
            )
            v2_confidence = result_v2.get("metadata", {}).get("overall_confidence", 0)

            if v2_confidence > overall_confidence:
                result_v2["metadata"]["reprocessed"] = True
                result_v2["metadata"]["anomalies"].append(
                    f"REPROCESS: Improved confidence from {overall_confidence:.2f} "
                    f"to {v2_confidence:.2f} with relaxed segmentation"
                )
                return result_v2

        anomalies.append("REPROCESS: Reprocessing did not improve confidence")
        result["metadata"]["anomalies"] = anomalies

    # Clean up internal keys
    result.pop("_name_result", None)

    logger.info(
        f"Structured resume built: confidence={overall_confidence:.2f}, "
        f"{len(anomalies)} anomalies, "
        f"{len(employment)} jobs, {len(education)} edu, "
        f"{len(mapped_skills)} skills"
    )

    return result
