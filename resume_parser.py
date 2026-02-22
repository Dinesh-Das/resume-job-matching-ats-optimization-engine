"""
Resume Parser Module
Extracts raw text from PDF and DOCX resume files.
"""

import io
import logging

logger = logging.getLogger(__name__)


def parse_pdf(file) -> str:
    """Extract text from a PDF file using pdfplumber."""
    import pdfplumber

    text_parts = []
    # Handle both file paths and file-like objects
    if isinstance(file, (str,)):
        pdf = pdfplumber.open(file)
    else:
        pdf = pdfplumber.open(io.BytesIO(file.read() if hasattr(file, "read") else file))

    with pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)


def parse_docx(file) -> str:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document

    if isinstance(file, (str,)):
        doc = Document(file)
    else:
        doc = Document(io.BytesIO(file.read() if hasattr(file, "read") else file))

    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())

    # Also extract from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                text_parts.append(row_text)

    return "\n".join(text_parts)


def parse_txt(file) -> str:
    """Read plain text file."""
    if isinstance(file, str):
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        content = file.read() if hasattr(file, "read") else file
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        return content


def parse_resume(file, filename: str = None) -> str:
    """
    Auto-detect format and parse resume.

    Parameters
    ----------
    file : str or file-like
        Path or uploaded file object.
    filename : str, optional
        Original filename (used to detect extension for file-like objects).

    Returns
    -------
    str
        Extracted resume text.
    """
    if isinstance(file, str):
        name = file.lower()
    elif filename:
        name = filename.lower()
    else:
        name = getattr(file, "name", "").lower()

    if name.endswith(".pdf"):
        text = parse_pdf(file)
    elif name.endswith(".docx"):
        text = parse_docx(file)
    elif name.endswith(".txt"):
        text = parse_txt(file)
    else:
        # Try plain text as fallback
        text = parse_txt(file)

    logger.info(f"Parsed resume: {len(text)} characters extracted")
    return text
