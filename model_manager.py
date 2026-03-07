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


class ModelManager:
    """
    Class-level singleton cache for ML models loaded across requests.
    Heavy models (sentence-transformers) are loaded once and reused for the
    life of the server process.
    """
    _semantic_model = None

    @classmethod
    def get_semantic_model(cls):
        """
        Load and cache the sentence-transformer model.
        Returns None on failure — caller must handle gracefully.
        SentenceTransformer is imported here (not at module level) so that a
        missing package never prevents the rest of the server from starting.
        """
        if cls._semantic_model is None:
            try:
                import torch
                from sentence_transformers import SentenceTransformer
                
                # Auto-detect hardware. User has an RTX 4060.
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Loading semantic model: all-MiniLM-L6-v2 on {device.upper()}")
                
                cls._semantic_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
                
                if device == "cuda":
                    logger.info(f"Semantic model successfully loaded into VRAM ({torch.cuda.get_device_name(0)})")
                else:
                    logger.info("Semantic model loaded successfully on CPU")
            except Exception as e:
                logger.warning(
                    f"Semantic model failed to load: {e}. "
                    "Semantic scoring will be skipped."
                )
                return None
        return cls._semantic_model
