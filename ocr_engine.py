"""
OCR Engine Module — Advanced Fallback Extraction

Handles text extraction from image-based or corrupted PDFs using:
- pdf2image for rendering pages to images
- OpenCV preprocessing (grayscale, CLAHE contrast, deskew, denoise, binarize)
- Multi-PSM pytesseract strategy with confidence scoring
- Localized re-OCR for low-confidence page regions
"""

import io
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import cv2
    import pytesseract
    from pdf2image import convert_from_bytes
    _OCR_AVAILABLE = True
except ImportError:
    logger.warning("OCR dependencies missing. Install opencv-python-headless, pytesseract, pdf2image.")
    cv2 = None
    _OCR_AVAILABLE = False


# ── Data Classes ──────────────────────────────────────────

@dataclass
class OcrPageResult:
    """OCR result for a single page."""
    page_number: int
    text: str = ""
    confidence: float = 0.0
    psm_used: int = 3
    anomalies: List[str] = field(default_factory=list)


@dataclass
class OcrResult:
    """Complete OCR result across all pages."""
    text: str = ""
    pages: List[OcrPageResult] = field(default_factory=list)
    mean_confidence: float = 0.0
    anomalies: List[str] = field(default_factory=list)


# ── Image Preprocessing Pipeline ────────────────────────

def _to_opencv(image) -> np.ndarray:
    """Convert PIL image to OpenCV BGR numpy array."""
    img_cv = np.array(image)
    if len(img_cv.shape) == 3 and img_cv.shape[2] >= 3:
        img_cv = img_cv[:, :, :3]  # Drop alpha if present
        img_cv = img_cv[:, :, ::-1].copy()  # RGB → BGR
    return img_cv


def _to_grayscale(img_cv: np.ndarray) -> np.ndarray:
    """Convert to grayscale."""
    if len(img_cv.shape) == 3:
        return cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    return img_cv


def _enhance_contrast_clahe(gray: np.ndarray) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _deskew(gray: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Detect text skew angle and rotate to straighten.
    Returns (deskewed_image, angle_corrected).
    """
    # Threshold to find text regions
    thresh = cv2.bitwise_not(
        cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    )
    coords = np.column_stack(np.where(thresh > 0))

    if len(coords) < 50:
        return gray, 0.0

    angle = cv2.minAreaRect(coords)[-1]

    # Normalize angle to [-45, 45]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Only rotate if skew is significant (> 0.5 degrees)
    if abs(angle) > 0.5:
        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        gray = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return gray, angle

    return gray, 0.0


def _denoise(gray: np.ndarray) -> np.ndarray:
    """Apply non-local means denoising."""
    return cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)


def _binarize(gray: np.ndarray) -> np.ndarray:
    """Apply adaptive Gaussian thresholding for binarization."""
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )


def _upscale_if_low_dpi(image, target_dpi: int = 300) -> np.ndarray:
    """
    Upscale image if it appears to be low resolution.
    Heuristic: if either dimension < 1000px, scale up.
    """
    img_cv = _to_opencv(image)
    h, w = img_cv.shape[:2]

    if h < 1000 or w < 700:
        scale = max(target_dpi / 150, 1.5)  # Assume ~150 DPI for small images
        new_w = int(w * scale)
        new_h = int(h * scale)
        img_cv = cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    return img_cv


def preprocess_image_for_ocr(image, enhanced: bool = True) -> np.ndarray:
    """
    Full OpenCV preprocessing pipeline for OCR.
    Steps: Upscale → Grayscale → CLAHE → Deskew → Denoise → Binarize
    """
    if cv2 is None:
        return np.array(image)

    # Upscale low-DPI images
    img_cv = _upscale_if_low_dpi(image)

    # Grayscale
    gray = _to_grayscale(img_cv)

    if enhanced:
        # CLAHE contrast enhancement
        gray = _enhance_contrast_clahe(gray)

    # Deskew
    gray, _ = _deskew(gray)

    # Denoise
    denoised = _denoise(gray)

    # Binarize
    binarized = _binarize(denoised)

    return binarized


# ── Per-Page OCR with Confidence ─────────────────────────

def _get_page_confidence(processed_img: np.ndarray, config: str = "") -> Tuple[str, float]:
    """
    Run OCR and return (text, mean_confidence).
    Uses image_to_data for confidence scoring.
    """
    try:
        data = pytesseract.image_to_data(
            processed_img, config=config, output_type=pytesseract.Output.DICT
        )

        # Calculate mean confidence (ignoring -1 entries which are non-text)
        confidences = [
            int(c) for c in data.get("conf", [])
            if int(c) >= 0
        ]
        mean_conf = sum(confidences) / len(confidences) if confidences else 0.0

        # Reconstruct text from data
        words = []
        prev_block = -1
        prev_line = -1
        for i, word in enumerate(data.get("text", [])):
            if not word.strip():
                continue
            block = data["block_num"][i]
            line = data["line_num"][i]
            if block != prev_block or line != prev_line:
                if words:
                    words.append("\n")
                prev_block = block
                prev_line = line
            words.append(word)

        text = " ".join(words).replace(" \n ", "\n").strip()
        return text, mean_conf / 100.0  # Normalize to 0-1

    except Exception as e:
        # Fallback to simple image_to_string
        text = pytesseract.image_to_string(processed_img, config=config)
        return text.strip(), 0.5  # Default confidence


def _ocr_page_multi_psm(processed_img: np.ndarray) -> OcrPageResult:
    """
    Try multiple PSM modes and pick the best result by confidence.
    PSM 3 = Fully automatic page segmentation (default)
    PSM 4 = Assume single column of text
    PSM 6 = Assume uniform block of text
    """
    best_text = ""
    best_conf = 0.0
    best_psm = 3
    anomalies = []

    psm_modes = [3, 6, 4]

    for psm in psm_modes:
        config = f"--oem 3 --psm {psm}"
        try:
            text, conf = _get_page_confidence(processed_img, config)

            if conf > best_conf and len(text.strip()) > 0:
                best_text = text
                best_conf = conf
                best_psm = psm

            # If we get good confidence, no need to try more
            if conf > 0.75:
                break

        except Exception as e:
            anomalies.append(f"OCR PSM {psm} failed: {e}")

    return OcrPageResult(
        page_number=0,  # Will be set by caller
        text=best_text,
        confidence=best_conf,
        psm_used=best_psm,
        anomalies=anomalies
    )


# ── Localized Re-OCR ────────────────────────────────────

def _reocr_low_confidence_regions(
    image, page_data: OcrPageResult, threshold: float = 0.4
) -> OcrPageResult:
    """
    If page confidence is below threshold, re-OCR at higher DPI
    with more aggressive preprocessing.
    """
    if page_data.confidence >= threshold:
        return page_data

    if cv2 is None:
        return page_data

    page_data.anomalies.append(
        f"RE-OCR: Confidence {page_data.confidence:.2f} below {threshold}, re-processing"
    )

    # Re-process with more aggressive settings
    img_cv = _to_opencv(image)
    h, w = img_cv.shape[:2]

    # Upscale to 2x
    img_cv = cv2.resize(img_cv, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    gray = _to_grayscale(img_cv)
    gray = _enhance_contrast_clahe(gray)
    gray, _ = _deskew(gray)

    # More aggressive denoising
    gray = cv2.fastNlMeansDenoising(gray, None, 15, 7, 21)

    # Otsu binarization (often better for scanned docs)
    _, binarized = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    # OCR with PSM 3
    config = "--oem 3 --psm 3"
    text, conf = _get_page_confidence(binarized, config)

    if conf > page_data.confidence and len(text) >= len(page_data.text) * 0.8:
        page_data.text = text
        page_data.confidence = conf
        page_data.anomalies.append(
            f"RE-OCR: Improved confidence to {conf:.2f}"
        )
    else:
        page_data.anomalies.append("RE-OCR: Re-processing did not improve results")

    return page_data


# ── Main OCR Orchestrator ────────────────────────────────

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> OcrResult:
    """
    Render PDF to images and extract text using multi-strategy OCR.
    Returns OcrResult with per-page confidence and anomalies.
    """
    result = OcrResult()

    if not _OCR_AVAILABLE:
        result.anomalies.append("OCR: Dependencies not installed")
        return result

    try:
        logger.info("Converting PDF to images for OCR (300 DPI)...")
        images = convert_from_bytes(pdf_bytes, dpi=300, fmt="jpeg")
    except Exception as e:
        result.anomalies.append(f"OCR: PDF-to-image conversion failed: {e}")
        return result

    page_results = []

    for i, img in enumerate(images):
        logger.info(f"OCR processing page {i+1}/{len(images)}...")

        # Preprocess
        processed_img = preprocess_image_for_ocr(img, enhanced=True)

        # Multi-PSM OCR
        page_result = _ocr_page_multi_psm(processed_img)
        page_result.page_number = i + 1

        # Localized re-OCR if confidence is low
        page_result = _reocr_low_confidence_regions(img, page_result)

        page_results.append(page_result)

    # Aggregate results
    result.pages = page_results
    all_text = []
    total_conf = 0.0

    for pr in page_results:
        if pr.text.strip():
            all_text.append(pr.text.strip())
        total_conf += pr.confidence
        result.anomalies.extend(pr.anomalies)

    result.text = "\n".join(all_text)
    result.mean_confidence = (
        total_conf / len(page_results) if page_results else 0.0
    )

    logger.info(
        f"OCR complete: {len(result.text)} chars, "
        f"{len(page_results)} pages, "
        f"mean confidence {result.mean_confidence:.2f}"
    )

    return result
