"""
Model Manager Module
Handles saving and loading the trained ATS engine model artifacts.
"""

import os
import joblib
import logging
from config import MODEL_PATH

logger = logging.getLogger(__name__)

def save_model(model_data: dict, filepath: str = MODEL_PATH):
    """
    Save the trained model artifacts to disk using joblib.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(model_data, filepath)
        logger.info(f"Model successfully saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save model to {filepath}: {e}")
        return False

def load_model(filepath: str = MODEL_PATH) -> dict:
    """
    Load the trained model artifacts from disk.
    """
    try:
        model_data = joblib.load(filepath)
        logger.info(f"Model successfully loaded from {filepath}")
        return model_data
    except Exception as e:
        logger.error(f"Failed to load model from {filepath}: {e}")
        return None

def is_model_trained(filepath: str = MODEL_PATH) -> bool:
    """
    Check if the model file exists on disk.
    """
    return os.path.exists(filepath)
