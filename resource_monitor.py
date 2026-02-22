"""
Resource Monitor Module
Monitors RAM usage, enforces a 30 GB hard limit, and provides
decorators / utilities to prevent OOM crashes.
"""

import os
import gc
import logging
import functools

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────
MAX_RAM_GB = 30
MAX_RAM_BYTES = MAX_RAM_GB * (1024 ** 3)

# ── Core Functions ────────────────────────────────

def _get_process():
    """Lazy-import psutil and return the current process handle."""
    import psutil
    return psutil.Process(os.getpid())


def get_memory_usage_gb() -> float:
    """Return current process RSS (Resident Set Size) in GB."""
    try:
        proc = _get_process()
        return proc.memory_info().rss / (1024 ** 3)
    except Exception:
        return 0.0


def get_memory_usage_bytes() -> int:
    """Return current process RSS in bytes."""
    try:
        proc = _get_process()
        return proc.memory_info().rss
    except Exception:
        return 0


def get_system_memory_info() -> dict:
    """Return system-wide memory statistics."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "total_gb": round(vm.total / (1024 ** 3), 1),
            "available_gb": round(vm.available / (1024 ** 3), 1),
            "used_gb": round(vm.used / (1024 ** 3), 1),
            "percent": vm.percent,
        }
    except Exception:
        return {}


def check_memory(context: str = ""):
    """
    Check if process RSS exceeds the 30 GB limit.
    Logs a warning at 80% and raises MemoryError at 100%.
    """
    current_bytes = get_memory_usage_bytes()
    current_gb = current_bytes / (1024 ** 3)
    limit_gb = MAX_RAM_GB

    # Warning at 80%
    warning_threshold = MAX_RAM_BYTES * 0.80
    if current_bytes >= warning_threshold:
        ctx = f" [{context}]" if context else ""
        logger.warning(
            f"⚠️  HIGH MEMORY{ctx}: {current_gb:.1f} GB / {limit_gb} GB "
            f"({current_bytes / MAX_RAM_BYTES * 100:.0f}%)"
        )

    # Hard limit
    if current_bytes >= MAX_RAM_BYTES:
        gc.collect()  # Last-ditch garbage collection
        # Re-check after GC
        current_bytes = get_memory_usage_bytes()
        current_gb = current_bytes / (1024 ** 3)
        if current_bytes >= MAX_RAM_BYTES:
            ctx = f" during {context}" if context else ""
            raise MemoryError(
                f"RAM limit exceeded{ctx}: {current_gb:.1f} GB >= {limit_gb} GB. "
                f"Aborting to prevent system crash."
            )


def log_memory(logger_instance=None, context: str = ""):
    """Log current memory usage at INFO level."""
    log = logger_instance or logger
    current_gb = get_memory_usage_gb()
    ctx = f" [{context}]" if context else ""
    log.info(f"💾 Memory{ctx}: {current_gb:.1f} GB / {MAX_RAM_GB} GB")


# ── Decorator ─────────────────────────────────────

def memory_guard(context: str = ""):
    """
    Decorator that checks memory before and after function execution.
    Raises MemoryError if the 30 GB limit is breached.

    Usage:
        @memory_guard("TF-IDF fitting")
        def fit_tfidf(corpus):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            fn_context = context or func.__name__
            check_memory(f"before {fn_context}")
            result = func(*args, **kwargs)
            check_memory(f"after {fn_context}")
            return result
        return wrapper
    return decorator


def compute_safe_batch_size(
    item_size_bytes: int,
    max_fraction: float = 0.25,
    min_batch: int = 100,
    max_batch: int = 10000,
) -> int:
    """
    Dynamically compute a safe batch size based on available RAM.

    Parameters
    ----------
    item_size_bytes : int
        Estimated memory cost per item in bytes.
    max_fraction : float
        Maximum fraction of remaining RAM headroom to use.
    min_batch : int
        Minimum batch size to return.
    max_batch : int
        Maximum batch size to return.

    Returns
    -------
    int : safe batch size
    """
    current = get_memory_usage_bytes()
    headroom = max(MAX_RAM_BYTES - current, 0)
    usable = int(headroom * max_fraction)

    if item_size_bytes <= 0:
        return max_batch

    batch = usable // max(item_size_bytes, 1)
    return max(min_batch, min(batch, max_batch))
