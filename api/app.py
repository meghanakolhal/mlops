"""
FastAPI service for ticket urgency prediction.
Deploy this to Cloud Run for model serving.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
from google.cloud import storage
import os
import tempfile
import logging

app = FastAPI(title="Ticket Urgency Prediction API", version="1.0.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GCS configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
MODEL_GCS_PATH = os.getenv("MODEL_GCS_PATH", "ticket_urgency_model/ticket_urgency_model.pkl")
MODEL_CACHE_PATH = "/tmp/model.pkl"
MODEL_VERSION_CACHE_PATH = "/tmp/model_version.txt"  # Track model version

# Global model variable
model = None
model_version = None  # Track current model version (GCS blob updated time)


class PredictionRequest(BaseModel):
    title: str
    description: str
    source: str
    customer_tier: str


class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    model_version: str


def get_model_version_from_gcs():
    """Get model version (updated timestamp) from GCS."""
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(MODEL_GCS_PATH)
        if blob.exists():
            # Use updated time as version identifier
            return blob.updated.isoformat() if blob.updated else None
        return None
    except Exception as e:
        logger.warning(f"Failed to get model version from GCS: {e}")
        return None


def download_model_from_gcs(force_reload=False):
    """
    Download model from GCS to local cache.
    Checks if model version changed and reloads if needed.
    """
    global model, model_version
    
    # Get current model version from GCS
    gcs_model_version = get_model_version_from_gcs()
    
    # Check if we need to reload (new model version or force reload)
    if not force_reload and model is not None:
        # Check if cached version matches GCS version
        cached_version = None
        if os.path.exists(MODEL_VERSION_CACHE_PATH):
            try:
                with open(MODEL_VERSION_CACHE_PATH, 'r') as f:
                    cached_version = f.read().strip()
            except Exception:
                pass
        
        if cached_version == gcs_model_version and gcs_model_version is not None:
            logger.info("Model already loaded and version matches GCS")
            return
        elif gcs_model_version is not None:
            logger.info(f"Model version changed: {cached_version} -> {gcs_model_version}. Reloading...")
            # Clear cache to force reload
            model = None
            if os.path.exists(MODEL_CACHE_PATH):
                os.remove(MODEL_CACHE_PATH)
    
    # Check if model exists in cache (and version matches)
    if not force_reload and os.path.exists(MODEL_CACHE_PATH):
        cached_version = None
        if os.path.exists(MODEL_VERSION_CACHE_PATH):
            try:
                with open(MODEL_VERSION_CACHE_PATH, 'r') as f:
                    cached_version = f.read().strip()
            except Exception:
                pass
        
        if cached_version == gcs_model_version and gcs_model_version is not None:
            logger.info(f"Loading model from cache: {MODEL_CACHE_PATH}")
            try:
                model = joblib.load(MODEL_CACHE_PATH)
                model_version = cached_version
                logger.info("Model loaded from cache successfully")
                return
            except Exception as e:
                logger.warning(f"Failed to load cached model: {e}. Will download from GCS.")
                os.remove(MODEL_CACHE_PATH)  # Remove corrupted cache
    
    # Download from GCS
    logger.info(f"Downloading model from gs://{BUCKET_NAME}/{MODEL_GCS_PATH}")
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(MODEL_GCS_PATH)
        
        # Check if blob exists
        if not blob.exists():
            error_msg = f"Model file not found: gs://{BUCKET_NAME}/{MODEL_GCS_PATH}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Get model version (updated timestamp)
        gcs_model_version = blob.updated.isoformat() if blob.updated else None
        logger.info(f"Model file exists. Size: {blob.size} bytes. Updated: {gcs_model_version}")
        
        # Download to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as tmp_file:
            blob.download_to_filename(tmp_file.name)
            logger.info(f"Model downloaded to {tmp_file.name}")
            model = joblib.load(tmp_file.name)
            # Cache for future requests
            os.rename(tmp_file.name, MODEL_CACHE_PATH)
            
            # Save model version
            if gcs_model_version:
                model_version = gcs_model_version
                with open(MODEL_VERSION_CACHE_PATH, 'w') as f:
                    f.write(gcs_model_version)
            
            logger.info("Model downloaded and cached successfully")
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@app.post("/reload-model")
async def reload_model():
    """
    Admin endpoint to force reload model from GCS.
    Useful when new model is deployed.
    """
    global model, model_version
    try:
        logger.info("Force reloading model from GCS...")
        model = None  # Clear in-memory model
        model_version = None
        
        # Remove cache files
        if os.path.exists(MODEL_CACHE_PATH):
            os.remove(MODEL_CACHE_PATH)
        if os.path.exists(MODEL_VERSION_CACHE_PATH):
            os.remove(MODEL_VERSION_CACHE_PATH)
        
        # Download fresh model
        download_model_from_gcs(force_reload=True)
        
        return {
            "status": "success",
            "message": "Model reloaded successfully",
            "model_version": model_version,
            "model_loaded": model is not None
        }
    except Exception as e:
        logger.error(f"Failed to reload model: {e}")
        raise HTTPException(status_code=500, detail=f"Model reload failed: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Load model when service starts."""
    logger.info("Starting up... Loading model from GCS")
    try:
        download_model_from_gcs()
        logger.info("✅ Model loaded successfully")
    except Exception as e:
        logger.error(f"⚠️ Model loading failed on startup: {e}")
        logger.info("Service will start but model will be None. Model will be loaded on first prediction request.")
        # Don't raise exception - allow service to start even if model fails to load


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_version": model_version,
        "bucket": BUCKET_NAME,
        "model_path": MODEL_GCS_PATH
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predict ticket urgency.
    
    Example request:
    {
        "title": "Server down",
        "description": "Production server is not responding",
        "source": "email",
        "customer_tier": "premium"
    }
    """
    if model is None:
        download_model_from_gcs()
    
    try:
        # Prepare input data (same format as training)
        input_data = pd.DataFrame({
            "text": [f"{request.title} {request.description}"],
            "source": [request.source],
            "customer_tier": [request.customer_tier]
        })
        
        # Make prediction
        prediction = model.predict(input_data)[0]
        probabilities = model.predict_proba(input_data)[0]
        
        # Get confidence (probability of predicted class)
        confidence = float(max(probabilities))
        
        return PredictionResponse(
            prediction=prediction,
            confidence=confidence,
            model_version=MODEL_GCS_PATH  # Could use MLflow run_id instead
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Ticket Urgency Prediction API",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "docs": "/docs"
        }
    }

