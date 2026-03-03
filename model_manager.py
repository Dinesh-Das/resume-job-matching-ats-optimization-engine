import os
import joblib
import logging
from config import MODEL_PATH

logger = logging.getLogger(__name__)

def get_model_path(role: str = None) -> str:
    """
    Get the file path for a specific role model.
    Standardizes the naming convention: engine_model_{role}.joblib
    """
    if not role or role.lower() == "all":
        return MODEL_PATH
    
    base_dir = os.path.dirname(MODEL_PATH)
    return os.path.join(base_dir, f"engine_model_{role.lower().replace(' ', '_')}.joblib")

def save_model(model_data: dict, role: str = None):
    """
    Save the trained model artifacts to disk using joblib.
    """
    filepath = get_model_path(role)
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(model_data, filepath, compress=3)
        logger.info(f"Model ({role or 'all'}) successfully saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save model to {filepath}: {e}")
        return False

def load_model(role: str = None) -> dict:
    """
    Load the trained model artifacts from disk.
    """
    filepath = get_model_path(role)
    try:
        if not os.path.exists(filepath):
            logger.warning(f"Model file not found: {filepath}")
            return None
        model_data = joblib.load(filepath)
        logger.info(f"Model ({role or 'all'}) successfully loaded from {filepath}")
        return model_data
    except Exception as e:
        logger.error(f"Failed to load model from {filepath}: {e}")
        return None

def is_model_trained(role: str = None) -> bool:
    """
    Check if the model file exists on disk.
    """
    return os.path.exists(get_model_path(role))
