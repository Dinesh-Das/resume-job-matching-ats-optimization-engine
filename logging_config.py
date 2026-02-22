"""
Logging Configuration Module
Rich console logging with timestamps, progress bars, memory usage, and stage tracking.
"""

import os
import re
import sys
import time
import logging
import threading


# ── Custom Formatter ──────────────────────────────
class PIIFilter(logging.Filter):
    """
    Logging filter that redacts PII (emails, phone numbers, SSNs) from log messages.
    Prevents resume content from leaking sensitive data into console logs.
    """
    _PATTERNS = [
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
        (re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"), "[SSN]"),
        (re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE]"),
    ]

    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self._PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


class RichFormatter(logging.Formatter):
    """
    Custom formatter with timestamps, emoji indicators, and coloured level names.
    Works on both Windows Terminal and legacy consoles.
    """

    LEVEL_ICONS = {
        logging.DEBUG: "🔧",
        logging.INFO: "ℹ️ ",
        logging.WARNING: "⚠️ ",
        logging.ERROR: "❌",
        logging.CRITICAL: "🔥",
    }

    def format(self, record):
        icon = self.LEVEL_ICONS.get(record.levelno, "  ")
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        # Pad module name for alignment
        module = record.name[-25:].ljust(25)
        msg = record.getMessage()
        return f"[{timestamp}] {icon} {module} │ {msg}"


# ── Progress Logger ──────────────────────────────
class ProgressLogger:
    """
    Tracks progress of batch operations, printing periodic progress bars
    with item counts, percentage, elapsed time, and memory usage.

    Usage:
        progress = ProgressLogger("Text Processing", total=50000, logger=logger)
        for batch in batches:
            process(batch)
            progress.update(len(batch))
        progress.finish()
    """

    def __init__(self, stage_name: str, total: int, logger=None,
                 report_every_pct: float = 10.0):
        self.stage_name = stage_name
        self.total = max(total, 1)
        self.processed = 0
        self.logger = logger or logging.getLogger(__name__)
        self.report_every = max(1, int(self.total * report_every_pct / 100))
        self.start_time = time.time()
        self._last_report = 0
        self._lock = threading.Lock()

        self.logger.info(f"┌── {stage_name} ── starting ({total:,} items)")

    def update(self, count: int = 1):
        with self._lock:
            self.processed = min(self.processed + count, self.total)
            if self.processed - self._last_report >= self.report_every or self.processed == self.total:
                self._report()
                self._last_report = self.processed

    def _report(self):
        pct = self.processed / self.total * 100
        bar_len = 30
        filled = int(bar_len * self.processed / self.total)
        bar = "█" * filled + "░" * (bar_len - filled)
        elapsed = time.time() - self.start_time

        # Memory usage (optional, graceful fallback)
        mem_str = ""
        try:
            from resource_monitor import get_memory_usage_gb
            mem_gb = get_memory_usage_gb()
            mem_str = f" | RAM: {mem_gb:.1f} GB"
        except Exception:
            pass

        rate = self.processed / max(elapsed, 0.001)
        self.logger.info(
            f"│  [{bar}] {pct:5.1f}% ({self.processed:,}/{self.total:,}) "
            f"| {elapsed:.1f}s | {rate:,.0f} items/s{mem_str}"
        )

    def finish(self, extra_msg: str = ""):
        elapsed = time.time() - self.start_time
        self.processed = self.total
        mem_str = ""
        try:
            from resource_monitor import get_memory_usage_gb
            mem_gb = get_memory_usage_gb()
            mem_str = f" | RAM: {mem_gb:.1f} GB"
        except Exception:
            pass
        suffix = f" — {extra_msg}" if extra_msg else ""
        self.logger.info(
            f"└── {self.stage_name} ── done in {elapsed:.1f}s "
            f"({self.total:,} items){mem_str}{suffix}"
        )


# ── Pipeline Banner ──────────────────────────────
def log_banner(logger, title: str, char="═", width=60):
    """Print a decorative banner to visually separate pipeline stages."""
    line = char * width
    logger.info(line)
    logger.info(f"  {title}")
    logger.info(line)


def log_stage(logger, stage_num: int, total_stages: int, title: str):
    """Log a numbered pipeline stage header."""
    logger.info(f"── Stage {stage_num}/{total_stages}: {title} ──")


# ── Setup Function ───────────────────────────────
def setup_logging(level=logging.INFO):
    """
    Configure the root logger with the rich formatter.
    Call once at application startup (server.py).
    """
    root = logging.getLogger()

    # Remove existing handlers to avoid duplicates on reload
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RichFormatter())
    handler.addFilter(PIIFilter())
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy third-party loggers
    for noisy in ["uvicorn.access", "uvicorn.error", "multipart", "httpcore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging initialised (rich console mode)")
