"""
Vectorizer Module
Fits a TF-IDF vectoriser on the job corpus and transforms text to vectors.
"""

import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from config import TFIDF_PARAMS, DOMAIN_STOP_WORDS

logger = logging.getLogger(__name__)


def build_vectorizer(corpus_size: int = 0) -> TfidfVectorizer:
    """
    Create a TfidfVectorizer with project configuration.
    Dynamically scale max_features down for massive datasets to save RAM.
    """
    # Combine sklearn's English stop words with our domain stop words
    stop_words = list(DOMAIN_STOP_WORDS)
    # User has 32GB RAM, so we can afford slightly higher feature ceilings
    # for massive datasets without hitting OOM, yielding better accuracy
    max_features = TFIDF_PARAMS["max_features"]
    if corpus_size > 300000:
        max_features = min(max_features, 6000)
    elif corpus_size > 150000:
        max_features = min(max_features, 8000)

    # Note: TfidfVectorizer does not natively accept n_jobs parameters in the constructor for version <1.3 
    # but the underlying transformations in later versions or specific pipelines handle it. 
    # For TfidfVectorizer itself, the heavy lifting is single-threaded in the vocabulary building phase, 
    # but we can configure its token pattern.
    vectorizer = TfidfVectorizer(
        ngram_range=TFIDF_PARAMS["ngram_range"],
        max_features=max_features,
        min_df=TFIDF_PARAMS["min_df"],
        max_df=TFIDF_PARAMS["max_df"],
        sublinear_tf=TFIDF_PARAMS["sublinear_tf"],
        stop_words=stop_words,
        dtype=np.float32,
    )
    return vectorizer


def fit_tfidf(corpus: list):
    """
    Fit TF-IDF vectoriser on the job corpus.

    Parameters
    ----------
    corpus : list of str
        Processed job texts.

    Returns
    -------
    vectorizer : TfidfVectorizer (fitted)
    tfidf_matrix : sparse matrix (n_jobs x n_features)
    """
    vectorizer = build_vectorizer(len(corpus))
    tfidf_matrix = vectorizer.fit_transform(corpus)
    feature_names = vectorizer.get_feature_names_out().tolist()
    logger.info(
        f"TF-IDF fitted: {tfidf_matrix.shape[0]} docs × {tfidf_matrix.shape[1]} features"
    )
    return vectorizer, tfidf_matrix, feature_names


def transform_text(text: str, vectorizer: TfidfVectorizer):
    """
    Transform a single text (e.g. resume) using a fitted vectoriser.

    Returns sparse matrix (1 x n_features).
    """
    return vectorizer.transform([text])
