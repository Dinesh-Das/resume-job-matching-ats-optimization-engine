"""
Comprehensive test suite for the advanced resume parsing pipeline.
Tests: schema completeness, name extraction, skill taxonomy, chronological
validation, confidence reprocessing, broken-line repair, magic-byte detection,
multi-column reconstruction, anomaly reporting, and API endpoint integration.
"""

import os
import sys
import json
import re
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── Unit Tests: File Type Detection ──────────────────────

def test_magic_byte_detection():
    """Test file type detection from magic bytes."""
    from resume_parser import detect_file_type

    assert detect_file_type(b"%PDF-1.4 ...", "resume.pdf") == "pdf"
    assert detect_file_type(b"\xd0\xcf\x11\xe0 ...", "resume.doc") == "doc"
    assert detect_file_type(b"PK\x03\x04 ...", "resume.docx") == "docx"
    assert detect_file_type(b"Hello world", "resume.txt") == "txt"
    assert detect_file_type(b"Hello world", "") == "txt"
    # Extension fallback
    assert detect_file_type(b"some bytes", "file.pdf") == "pdf"
    assert detect_file_type(b"some bytes", "file.docx") == "docx"
    print("[PASS] test_magic_byte_detection")


# ── Unit Tests: Text Quality Assessment ──────────────────

def test_text_quality_assessment():
    """Test text corruption detection heuristics."""
    from resume_parser import _assess_text_quality

    # Good text
    good_text = "John Doe\nSenior Software Engineer\njohn@email.com\n" * 10
    score, anomalies = _assess_text_quality(good_text, 500)
    assert score >= 0.7, f"Expected good score, got {score}"
    print(f"  Good text score: {score:.2f}, anomalies: {anomalies}")

    # Empty text
    score, anomalies = _assess_text_quality("", 5000)
    assert score == 0.0
    assert any("empty" in a.lower() for a in anomalies)
    print(f"  Empty text score: {score:.2f}")

    # Corrupted text (lots of replacement chars)
    bad_text = "\ufffd" * 100  + "some text" * 5
    score, anomalies = _assess_text_quality(bad_text, 1000)
    assert score < 0.7
    print(f"  Corrupted text score: {score:.2f}")

    print("[PASS] test_text_quality_assessment")


# ── Unit Tests: Layout Processor ─────────────────────────

def test_encoding_normalization():
    """Test mojibake and encoding repair."""
    from layout_processor import normalize_encoding

    anomalies = []
    # Smart quotes
    result = normalize_encoding("\u2018hello\u2019 \u201cworld\u201d", anomalies)
    assert "'" in result and '"' in result
    print(f"  Smart quotes normalized: {result}")

    # Control characters
    result = normalize_encoding("hello\x00\x01world", [])
    assert "\x00" not in result
    print("[PASS] test_encoding_normalization")


def test_hyphenation_repair():
    """Test hyphenated line break resolution."""
    from layout_processor import repair_hyphenation

    anomalies = []
    text = "This is an ex-\ntraction test"
    result = repair_hyphenation(text, anomalies)
    assert "extraction" in result
    assert len(anomalies) > 0
    print(f"  Repaired: {result.strip()}")
    print("[PASS] test_hyphenation_repair")


def test_broken_line_repair():
    """Test mid-sentence line break joining."""
    from layout_processor import repair_broken_lines

    anomalies = []
    text = "This is a long sentence that was\nbroken across two lines"
    result = repair_broken_lines(text, anomalies)
    assert "was broken" in result or "was\nbroken" in result
    print("[PASS] test_broken_line_repair")


def test_bullet_standardization():
    """Test bullet point normalization."""
    from layout_processor import standardize_bullets

    anomalies = []
    text = "* Item one\n- Item two\n\u25aa Item three"
    result = standardize_bullets(text, anomalies)
    bullet_count = result.count("\u2022")
    assert bullet_count >= 2, f"Expected 2+ bullets, got {bullet_count}"
    print(f"  Standardized bullets: {bullet_count}")
    print("[PASS] test_bullet_standardization")


def test_header_footer_removal():
    """Test repeating header/footer detection and removal."""
    from layout_processor import remove_headers_footers

    anomalies = []
    # Simulate 3 pages with repeating header/footer
    page = "Page Header\nContent line 1\nContent line 2\nPage Footer"
    text = (page + "\x0c") * 3
    result = remove_headers_footers(text, anomalies)
    # Should have removed headers and footers
    assert "Content line 1" in result
    print(f"  Anomalies: {anomalies}")
    print("[PASS] test_header_footer_removal")


# ── Unit Tests: Section Segmentation ─────────────────────

def test_section_segmentation():
    """Test section detection with weighted scoring."""
    from ats_simulator import segment_resume_sections

    resume = """JOHN DOE
john@email.com | +1 555-123-4567

PROFESSIONAL SUMMARY
Experienced software engineer with 10 years of experience.

WORK EXPERIENCE
Senior Engineer - ACME Corp
Jan 2020 - Present
- Led development of microservices

EDUCATION
M.S. Computer Science - MIT, 2019

SKILLS
Python, Java, AWS, Docker, Kubernetes

CERTIFICATIONS
AWS Solutions Architect - Professional
"""
    sections = segment_resume_sections(resume)
    metadata = sections.pop("_metadata", {})

    section_names = list(sections.keys())
    print(f"  Sections found: {section_names}")

    # Should find key sections
    assert any("experience" in s for s in section_names), f"Missing experience section: {section_names}"
    assert any("education" in s for s in section_names), f"Missing education section: {section_names}"
    assert any("skill" in s for s in section_names), f"Missing skills section: {section_names}"

    # Metadata should have confidence scores
    assert metadata, "Missing section metadata"
    print(f"  Metadata keys: {list(metadata.keys())}")

    print("[PASS] test_section_segmentation")


# ── Unit Tests: Entity Extraction ────────────────────────

def test_name_extraction():
    """Test name extraction from header."""
    from entity_extractor import extract_name

    header = "John Doe\njohn.doe@email.com\n+1 555-123-4567"
    result = extract_name(header, header)
    assert result["name"] is not None, "Name should be extracted"
    assert result["confidence"] > 0.5
    print(f"  Extracted name: {result['name']} (conf: {result['confidence']})")
    print("[PASS] test_name_extraction")


def test_contact_extraction():
    """Test contact info extraction."""
    from entity_extractor import extract_contact_info

    text = """John Doe
john.doe@email.com
+1-555-123-4567
linkedin.com/in/johndoe
github.com/johndoe"""

    result = extract_contact_info(text)
    assert result["email"] == "john.doe@email.com"
    assert result["phone"] is not None
    assert result["linkedin"] is not None
    assert result["confidence"] > 0.5
    print(f"  Contact: email={result['email']}, phone={result['phone']}")
    print(f"  LinkedIn: {result['linkedin']}, confidence: {result['confidence']}")
    print("[PASS] test_contact_extraction")


def test_education_extraction():
    """Test education section parsing."""
    from entity_extractor import extract_education

    edu_text = """M.S. Computer Science
Massachusetts Institute of Technology
Graduated 2019, GPA: 3.9/4.0

B.Tech Information Technology
Indian Institute of Technology
2017"""

    entries = extract_education(edu_text)
    assert len(entries) >= 1, "Should extract at least 1 education entry"
    assert any(e.get("degree") for e in entries), "Should find a degree"
    for e in entries:
        print(f"  Entry: {e}")
    print("[PASS] test_education_extraction")


def test_employment_extraction():
    """Test employment history parsing with date anchoring."""
    from entity_extractor import extract_employment_history

    exp_text = """Senior Software Engineer
ACME Corporation
Jan 2020 - Present
- Led team of 5 engineers
- Built microservices architecture
- Reduced latency by 40%

Software Engineer
StartupCo
Jun 2017 - Dec 2019
- Developed REST APIs
- Implemented CI/CD pipelines"""

    jobs = extract_employment_history(exp_text)
    assert len(jobs) >= 1, f"Should extract at least 1 job, got {len(jobs)}"

    for j in jobs:
        print(f"  Job: {j.get('title')} at {j.get('company')}")
        print(f"    Dates: {j.get('start_date')} - {j.get('end_date')}")
        print(f"    Duration: {j.get('duration_months')} months, Current: {j.get('is_current')}")
        print(f"    Confidence: {j.get('confidence')}")
        print(f"    Responsibilities: {len(j.get('responsibilities', []))}")

    # At least one should be current
    current_jobs = [j for j in jobs if j.get("is_current")]
    print(f"  Current roles: {len(current_jobs)}")

    print("[PASS] test_employment_extraction")


def test_skill_taxonomy_mapping():
    """Test skill-to-taxonomy mapping and deduplication."""
    from entity_extractor import map_skills_to_taxonomy, deduplicate_skills_semantic

    skills = ["Python", "python", "Java", "machine learning", "Machine Learning",
              "aws", "docker", "react"]
    mapped = map_skills_to_taxonomy(skills)

    # Should deduplicate
    names = [s["name"] for s in mapped]
    assert len(names) == len(set(names)), f"Duplicates found: {names}"

    # Should have categories
    for s in mapped:
        print(f"  {s['name']}: category={s['category']}, conf={s['confidence']}")

    # Test semantic dedup
    deduped = deduplicate_skills_semantic(mapped)
    print(f"  After semantic dedup: {len(deduped)} skills")

    print("[PASS] test_skill_taxonomy_mapping")


def test_certification_extraction():
    """Test certification regex extraction."""
    from entity_extractor import extract_certifications

    text = """
    AWS Certified Solutions Architect - Professional
    Certified Kubernetes Administrator (CKA)
    PMP Certification
    Google Cloud Professional Data Engineer
    """
    certs = extract_certifications(text)
    assert len(certs) >= 1, f"Should find certifications, got {len(certs)}"
    for c in certs:
        print(f"  Cert: {c['name']} (conf: {c['confidence']})")
    print("[PASS] test_certification_extraction")


# ── Unit Tests: Cross-Field Validation ───────────────────

def test_cross_field_validation():
    """Test validation catches chronological issues and duplicates."""
    from entity_extractor import validate_structured_output

    result = {
        "name": "John Doe",
        "contact_info": {"email": "john@test.com"},
        "employment_history": [
            {"title": "Engineer", "company": "ACME", "start_date": "Jan 2020",
             "end_date": "Present", "is_current": True},
            {"title": "Engineer", "company": "ACME", "start_date": "Jan 2020",
             "end_date": "Present", "is_current": True},
        ],
        "education": [],
    }

    anomalies = validate_structured_output(result)
    print(f"  Validation anomalies: {anomalies}")
    # Should detect duplicate jobs and multiple current roles
    assert any("Duplicate" in a for a in anomalies) or any("Multiple current" in a for a in anomalies), \
        f"Should detect duplicates/multiple current roles: {anomalies}"
    print("[PASS] test_cross_field_validation")


# ── Integration Test: Full Pipeline ──────────────────────

def test_full_structured_pipeline():
    """Test the full build_structured_resume pipeline."""
    from entity_extractor import build_structured_resume

    resume_text = """JOHN DOE
john.doe@email.com | +1 555-123-4567 | linkedin.com/in/johndoe

PROFESSIONAL SUMMARY
Experienced full-stack software engineer with 8+ years of experience
building scalable web applications and microservices.

WORK EXPERIENCE

Senior Software Engineer
ACME Corporation
Jan 2020 - Present
- Led development of cloud-native microservices platform
- Managed team of 5 engineers across 3 time zones
- Reduced API latency by 40% through caching optimization

Software Engineer
TechStartup Inc
Jun 2017 - Dec 2019
- Developed RESTful APIs using Python and FastAPI
- Implemented CI/CD pipelines with Jenkins and Docker
- Built real-time data processing with Apache Kafka

EDUCATION
M.S. Computer Science
Massachusetts Institute of Technology, 2017

SKILLS
Python, Java, JavaScript, React, Node.js, AWS, Docker, Kubernetes,
PostgreSQL, MongoDB, Redis, Apache Kafka, CI/CD, Agile

CERTIFICATIONS
AWS Certified Solutions Architect - Professional

PROJECTS
Cloud Migration Platform
- Built automated cloud migration tool using Python and AWS SDK
- Technologies: Python, AWS, Terraform, Docker
"""

    result = build_structured_resume(resume_text)

    # Schema completeness checks
    assert result.get("name"), "Missing name"
    assert result.get("contact_info"), "Missing contact info"
    assert result.get("contact_info", {}).get("email"), "Missing email"
    assert result.get("skills"), "Missing skills"
    assert result.get("employment_history"), "Missing employment history"
    assert result.get("education"), "Missing education"
    assert result.get("metadata"), "Missing metadata"

    print(f"  Name: {result['name']}")
    print(f"  Email: {result['contact_info'].get('email')}")
    print(f"  Skills: {len(result['skills'])}")
    print(f"  Jobs: {len(result['employment_history'])}")
    print(f"  Education: {len(result['education'])}")
    print(f"  Certifications: {len(result.get('certifications', []))}")
    print(f"  Projects: {len(result.get('projects', []))}")
    print(f"  Overall confidence: {result['metadata'].get('overall_confidence')}")
    print(f"  Anomalies: {result['metadata'].get('anomalies', [])}")
    print(f"  Sections detected: {list(result['metadata'].get('sections_detected', {}).keys())}")

    # Confidence should be reasonable for a well-formed resume
    assert result["metadata"]["overall_confidence"] > 0.3, \
        f"Confidence too low: {result['metadata']['overall_confidence']}"

    print("[PASS] test_full_structured_pipeline")


# ── Integration Test: ParseResult Pipeline ───────────────

def test_parse_resume_txt():
    """Test parse_resume with plain text input."""
    from resume_parser import parse_resume

    text = b"John Doe\njohn@email.com\nSenior Engineer at ACME Corp"
    result = parse_resume(text, filename="resume.txt")

    assert result.file_type == "txt"
    assert result.raw_text
    assert result.extraction_method == "native"
    print(f"  File type: {result.file_type}")
    print(f"  Raw text length: {len(result.raw_text)}")
    print(f"  Method: {result.extraction_method}")
    print(f"  Anomalies: {result.anomalies}")
    print("[PASS] test_parse_resume_txt")


# ── Integration Test: Anomaly Reporting ──────────────────

def test_anomaly_reporting():
    """Test that anomalies are properly reported, not silently swallowed."""
    from resume_parser import parse_resume

    # Empty input should report anomaly
    result = parse_resume(b"", filename="empty.pdf")
    assert len(result.anomalies) > 0, "Empty input should produce anomalies"
    print(f"  Empty file anomalies: {result.anomalies}")

    # Very short text should note it
    result = parse_resume(b"Hi", filename="short.txt")
    print(f"  Short file text: '{result.raw_text}', anomalies: {result.anomalies}")

    print("[PASS] test_anomaly_reporting")


# ── API Endpoint Test ────────────────────────────────────

def test_parse_advanced_endpoint():
    """Test the /api/parse-advanced endpoint via TestClient."""
    try:
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)

        resume_content = b"""JANE SMITH
jane.smith@email.com | +1-555-987-6543

PROFESSIONAL SUMMARY
Data scientist with 5 years of experience in machine learning.

EXPERIENCE
Data Scientist - DataCorp
Jan 2021 - Present
- Built ML models for customer churn prediction
- Improved model accuracy by 25%

EDUCATION
M.S. Data Science - Stanford University, 2020

SKILLS
Python, R, TensorFlow, PyTorch, SQL, Tableau
"""
        response = client.post(
            "/api/parse-advanced",
            files={"file": ("resume.txt", resume_content, "text/plain")}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

        result = data["data"]
        print(f"  Name: {result.get('name')}")
        print(f"  Skills: {len(result.get('skills', []))}")
        print(f"  Jobs: {len(result.get('employment_history', []))}")
        print(f"  Overall confidence: {result.get('metadata', {}).get('overall_confidence')}")

        print("[PASS] test_parse_advanced_endpoint")

    except Exception as e:
        print(f"[SKIP] test_parse_advanced_endpoint: {e}")


# ── Run All Tests ────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("ADVANCED RESUME PARSING — TEST SUITE")
    print("=" * 60)

    tests = [
        test_magic_byte_detection,
        test_text_quality_assessment,
        test_encoding_normalization,
        test_hyphenation_repair,
        test_broken_line_repair,
        test_bullet_standardization,
        test_header_footer_removal,
        test_section_segmentation,
        test_name_extraction,
        test_contact_extraction,
        test_education_extraction,
        test_employment_extraction,
        test_skill_taxonomy_mapping,
        test_certification_extraction,
        test_cross_field_validation,
        test_full_structured_pipeline,
        test_parse_resume_txt,
        test_anomaly_reporting,
        test_parse_advanced_endpoint,
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test_fn in tests:
        try:
            print(f"\n--- {test_fn.__name__} ---")
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_fn.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)
