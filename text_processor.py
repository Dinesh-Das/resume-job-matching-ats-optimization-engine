"""
Text Processing Module
Cleans, normalises, lemmatises, and applies synonym mapping to text.
"""

import re
import logging
from config import SYNONYM_MAP, DOMAIN_STOP_WORDS, MAX_WORKERS, CHUNK_SIZE

logger = logging.getLogger(__name__)

# ── spaCy model (lazy loaded) ────────────────
_nlp = None


def _get_nlp():
    """Lazy-load spaCy model. Falls back to simple tokenisation if unavailable."""
    global _nlp
    if _nlp is None:
        try:
            import os
            
            # ── CRITICAL FIX ──
            # Force CPU for spaCy and strictly limit internal C++ thread pools.
            # On Windows, loky 'spawn' workers do not inherit runtime OS variables.
            # These must be set before importing spacy inside the child process to prevent 
            # 8 workers * 20 threads = 160 threads fighting for the CPU and timing out.
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["OPENBLAS_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
            os.environ["NUMEXPR_NUM_THREADS"] = "1"
            
            import spacy
            spacy.require_cpu()
            
            try:
                _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "textcat", "custom"])
                # Increase max_length for very long job texts
                _nlp.max_length = 2_000_000
            except OSError:
                logger.warning("spaCy model 'en_core_web_sm' not found. "
                               "Run: python -m spacy download en_core_web_sm")
                _nlp = "fallback"
        except ImportError:
            logger.warning("spaCy not installed, using fallback lemmatisation")
            _nlp = "fallback"
    return _nlp


# ── Cleaning functions ────────────────────────

def clean_text(text: str) -> str:
    """
    Core text cleaning:
    - lowercase
    - remove URLs, emails, phone numbers
    - remove special characters (keep alphanumeric, spaces, hyphens)
    - normalise whitespace
    """
    if not text:
        return ""

    text = text.lower()

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Remove emails
    text = re.sub(r"\S+@\S+\.\S+", " ", text)

    # Remove phone numbers
    text = re.sub(r"[\+]?[\d\-\(\)\s]{7,15}", " ", text)

    # Keep letters, digits, spaces, hyphens, plus signs, periods, hash
    text = re.sub(r"[^a-zA-Z0-9\s\-\+\.#]", " ", text)

    # Normalise whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def lemmatize(text: str) -> str:
    """
    Lemmatise text using spaCy.
    Falls back to simple whitespace tokenisation if spaCy unavailable.
    """
    nlp = _get_nlp()
    if nlp == "fallback":
        return text

    doc = nlp(text)
    tokens = []
    for token in doc:
        if not token.is_stop and not token.is_punct and len(token.text) > 1:
            tokens.append(token.lemma_)
    return " ".join(tokens)


_SYNONYM_PATTERN = None
_CACHED_SYNONYM_MAP = None

def _get_synonym_pattern_and_map(synonym_map: dict):
    global _SYNONYM_PATTERN, _CACHED_SYNONYM_MAP
    if _SYNONYM_PATTERN is None:
        if synonym_map is None:
            synonym_map = SYNONYM_MAP
        _CACHED_SYNONYM_MAP = synonym_map
        # Sort by length descending to match longest alias first
        sorted_aliases = sorted(synonym_map.keys(), key=len, reverse=True)
        escaped = [re.escape(a) for a in sorted_aliases]
        pattern_str = r"\b(" + "|".join(escaped) + r")\b"
        _SYNONYM_PATTERN = re.compile(pattern_str, re.IGNORECASE)
    return _SYNONYM_PATTERN, _CACHED_SYNONYM_MAP

def apply_synonyms(text: str, synonym_map: dict = None) -> str:
    """
    Replace known aliases with canonical skill names.
    Uses word-boundary regex for exact matching.
    """
    if not text:
        return text

    pattern, current_map = _get_synonym_pattern_and_map(synonym_map)
    
    # The replacement function looks up the matched alias (lowercased) in the map
    def replacer(match):
        alias = match.group(0).lower()
        return current_map.get(alias, alias)

    return pattern.sub(replacer, text)


def remove_domain_stopwords(text: str) -> str:
    """Remove domain-specific stop words."""
    words = text.split()
    stop_set = set(DOMAIN_STOP_WORDS)
    filtered = [w for w in words if w not in stop_set]
    return " ".join(filtered)


def process(text: str) -> str:
    """
    Full text processing pipeline:
    clean → synonyms → lemmatise → remove domain stopwords
    """
    text = clean_text(text)
    text = apply_synonyms(text)
    text = lemmatize(text)
    text = remove_domain_stopwords(text)
    return text


def _pre_process_worker(text: str) -> str:
    """Helper worker for multiprocessing text cleanup."""
    return apply_synonyms(clean_text(text))


def remove_domain_stopwords_worker(text: str) -> str:
    """Helper worker for multiprocessing stopword removal."""
    return remove_domain_stopwords(text)

def _lemmatize_batch_worker(texts_group: list) -> list:
    """
    Worker for multiprocessing spaCy Lemmatization.
    Initializes spaCy inside the child process and processes a batch.
    """
    nlp = _get_nlp()
    if nlp == "fallback":
        # simple lowercase tokenization
        results = []
        for text in texts_group:
            results.append(lemmatize(text))
        return results
    
    # Using spaCy's optimized pipe inside the worker
    batch_lemmatized = []
    for doc in nlp.pipe(texts_group, batch_size=200):
        tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and len(token.text) > 1]
        batch_lemmatized.append(" ".join(tokens))
    return batch_lemmatized

def process_series(series) -> list:
    """Process a pandas Series of text using loky ProcessPoolExecutor and spaCy's optimized nlp.pipe loop."""
    # Use loky to dynamically chunk and memmap string buffers to prevent OS IPC Pipe deadlocks on Windows.
    from joblib.externals.loky import ProcessPoolExecutor
    from logging_config import ProgressLogger
    from resource_monitor import check_memory

    texts = [str(text) for text in series]
    total = len(texts)

    check_memory("text_processing start")

    # Stage 1: Clean + Synonyms (multiprocess)
    logger.info(f"🧠 Text Processing — Stage 1/3: Clean + Synonyms ({MAX_WORKERS} workers, chunk={CHUNK_SIZE})")
    progress = ProgressLogger("Clean + Synonyms", total, logger, report_every_pct=20)
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        pre_processed = []
        for i, result in enumerate(executor.map(_pre_process_worker, texts, chunksize=CHUNK_SIZE)):
            pre_processed.append(result)
            if (i + 1) % CHUNK_SIZE == 0 or i + 1 == total:
                progress.update(CHUNK_SIZE if (i + 1) % CHUNK_SIZE == 0 else (i + 1) % CHUNK_SIZE)
    progress.finish()

    check_memory("after clean+synonyms")

    # Stage 2: Lemmatization (multiprocess)
    nlp = _get_nlp()
    gpu_str = "GPU accelerated" if hasattr(nlp, 'prefer_gpu') else "CPU/Fallback"
    
    # Use maximum available OS cores now that Windows OpenMP scaling limits are safely injected
    spacy_workers = MAX_WORKERS
    
    import os
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    
    logger.info(f"🧠 Text Processing — Stage 2/3: spaCy Lemmatisation ({gpu_str}, {spacy_workers} workers)")
    logger.info(f"   ⏳ Note: Deep NLP analysis on {total:,} items is a heavy operation and will take several minutes to complete.")
    progress = ProgressLogger("spaCy Lemmatisation", total, logger, report_every_pct=2)
    
    # Chunk the pre_processed array into smaller, safer batches for IPC
    batch_size = max(500, min(1000, total // (spacy_workers * 4)))
    batches = [pre_processed[i:i + batch_size] for i in range(0, total, batch_size)]
    lemmatized = []
    
    with ProcessPoolExecutor(max_workers=spacy_workers) as executor:
        for result_batch in executor.map(_lemmatize_batch_worker, batches):
            lemmatized.extend(result_batch)
            progress.update(len(result_batch))
    
    progress.finish()

    check_memory("after lemmatisation")

    # Stage 3: Domain Stopwords (multiprocess)
    logger.info(f"🧠 Text Processing — Stage 3/3: Domain Stopwords ({MAX_WORKERS} workers)")
    progress = ProgressLogger("Domain Stopwords", total, logger, report_every_pct=25)
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = []
        for i, result in enumerate(executor.map(remove_domain_stopwords_worker, lemmatized, chunksize=CHUNK_SIZE)):
            results.append(result)
            if (i + 1) % CHUNK_SIZE == 0 or i + 1 == total:
                progress.update(CHUNK_SIZE if (i + 1) % CHUNK_SIZE == 0 else (i + 1) % CHUNK_SIZE)
    progress.finish()

    check_memory("text_processing end")
    logger.info("✅ Text processing pipeline complete.")
    return results
