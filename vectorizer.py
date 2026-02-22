"""
Vectorizer Module
Fits a TF-IDF vectoriser on the job corpus and transforms text to vectors.
"""

import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from config import TFIDF_PARAMS, DOMAIN_STOP_WORDS

logger = logging.getLogger(__name__)


def build_vectorizer() -> TfidfVectorizer:
    """
    Create a TfidfVectorizer with project configuration.
    """
    # Combine sklearn's English stop words with our domain stop words
    stop_words = list(DOMAIN_STOP_WORDS)

    vectorizer = TfidfVectorizer(
        ngram_range=TFIDF_PARAMS["ngram_range"],
        max_features=TFIDF_PARAMS["max_features"],
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
    vectorizer = build_vectorizer()
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
