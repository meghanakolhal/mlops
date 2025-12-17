"""
Model monitoring script - checks for data drift and model performance.
Run this periodically (e.g., daily via Airflow) to monitor production model.
"""
import os
import pandas as pd
import numpy as np
from google.cloud import storage
import joblib
import requests
from datetime import datetime
import json

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
MODEL_GCS_PATH = "ticket_urgency_model/ticket_urgency_model.pkl"
API_URL = os.getenv("API_URL", "https://ticket-urgency-api-7j3n5753uq-el.a.run.app")
# Reference data (training data) - stored in GCS
REFERENCE_DATA_GCS_PATH = "datasets/tickets.csv"
# New/production data - for drift comparison (can be updated later)
NEW_DATA_GCS_PATH = os.getenv("NEW_DATA_GCS_PATH", "datasets/new_tickets.csv")  # Will be created when new data arrives
LOCAL_DATA_FALLBACK = os.path.join("data", "raw", "tickets.csv")


def load_data_from_gcs(bucket_name: str, gcs_path: str, local_fallback: str = None):
    """
    Load CSV data from GCS, with optional local fallback.
    Returns pandas DataFrame.
    """
    try:
        print(f"Loading data from GCS: gs://{bucket_name}/{gcs_path}")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            if local_fallback and os.path.exists(local_fallback):
                print(f"⚠️  GCS file not found, using local fallback: {local_fallback}")
                return pd.read_csv(local_fallback)
            raise FileNotFoundError(f"Data not found in GCS: gs://{bucket_name}/{gcs_path}")
        
        # Download to temp file and load
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp_file:
            blob.download_to_filename(tmp_file.name)
            df = pd.read_csv(tmp_file.name)
            os.unlink(tmp_file.name)
        
        print(f"✅ Loaded {len(df)} rows from GCS")
        return df
    except Exception as e:
        if local_fallback and os.path.exists(local_fallback):
            print(f"⚠️  GCS load failed: {e}, using local fallback: {local_fallback}")
            return pd.read_csv(local_fallback)
        raise


def download_model():
    """Download model from GCS."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(MODEL_GCS_PATH)
    
    with open("/tmp/model.pkl", "wb") as f:
        blob.download_to_fileobj(f)
    
    return joblib.load("/tmp/model.pkl")


def check_data_drift(reference_data, new_data):
    """
    Simple data drift detection using statistical tests.
    In production, use libraries like Evidently AI or NannyML.
    """
    drift_detected = False
    drift_report = {}
    
    # Check feature distributions
    for col in ["source", "customer_tier"]:
        ref_dist = reference_data[col].value_counts(normalize=True)
        new_dist = new_data[col].value_counts(normalize=True)
        
        # Simple check: if distribution changed significantly
        diff = abs(ref_dist - new_dist.reindex(ref_dist.index, fill_value=0)).sum()
        if diff > 0.1:  # Threshold
            drift_detected = True
            drift_report[col] = {
                "drift_score": float(diff),
                "reference_dist": ref_dist.to_dict(),
                "new_dist": new_dist.to_dict()
            }
    
    return drift_detected, drift_report


def check_api_health():
    """Check if API is responding."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=15)  # Increased timeout
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}


def test_prediction():
    """Test API prediction endpoint with realistic test data."""
    # Use test data similar to training data for better confidence
    test_data = {
        "title": "Application running slow",
        "description": "Report export stuck at 80 percent for several minutes.",
        "source": "web",
        "customer_tier": "Gold"
    }
    
    try:
        response = requests.post(f"{API_URL}/predict", json=test_data, timeout=15)
        if response.status_code == 200:
            return True, response.json()
        return False, {"error": f"Status {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}


def main():
    """Run monitoring checks."""
    print(f"🔍 Model Monitoring - {datetime.now()}")
    print("=" * 50)
    
    # 1. Check API health
    print("\n1. Checking API health...")
    healthy, health_data = check_api_health()
    if healthy:
        print("✅ API is healthy")
        print(f"   Model loaded: {health_data.get('model_loaded', False)}")
    else:
        print(f"❌ API health check failed: {health_data}")
    
    # 2. Test prediction
    print("\n2. Testing prediction endpoint...")
    success, pred_data = test_prediction()
    if success:
        print(f"✅ Prediction successful")
        print(f"   Prediction: {pred_data.get('prediction')}")
        print(f"   Confidence: {pred_data.get('confidence', 0):.2f}")
    else:
        print(f"❌ Prediction test failed: {pred_data}")
    
    # 3. Check data drift
    print("\n3. Checking for data drift...")
    drift_detected = False
    drift_report = {}
    
    try:
        # Load reference data (training data) from GCS
        print(f"Loading reference data from: gs://{BUCKET_NAME}/{REFERENCE_DATA_GCS_PATH}")
        reference_data = load_data_from_gcs(BUCKET_NAME, REFERENCE_DATA_GCS_PATH, LOCAL_DATA_FALLBACK)
        
        # Try to load new/production data from GCS
        # If new data doesn't exist yet, we'll compare reference to itself (no drift)
        try:
            print(f"Loading new/production data from: gs://{BUCKET_NAME}/{NEW_DATA_GCS_PATH}")
            new_data = load_data_from_gcs(BUCKET_NAME, NEW_DATA_GCS_PATH, None)
            print(f"✅ Found new data with {len(new_data)} rows")
        except FileNotFoundError:
            print(f"ℹ️  New data not found at gs://{BUCKET_NAME}/{NEW_DATA_GCS_PATH}")
            print("   Using reference data for comparison (no drift expected)")
            new_data = reference_data.copy()
        
        # Compare distributions
        drift_detected, drift_report = check_data_drift(reference_data, new_data)
        
        if drift_detected:
            print("⚠️  Data drift detected!")
            print(json.dumps(drift_report, indent=2))
        else:
            print("✅ No significant data drift detected")
    except Exception as e:
        print(f"⚠️  Could not check data drift: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Save monitoring report
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_health": health_data,
        "prediction_test": pred_data if success else {"error": str(pred_data)},
        "drift_detected": drift_detected,
        "drift_report": drift_report
    }
    
    # Upload report to GCS
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    report_path = f"monitoring/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    blob = bucket.blob(report_path)
    blob.upload_from_string(json.dumps(report, indent=2))
    print(f"\n📊 Monitoring report saved to: gs://{BUCKET_NAME}/{report_path}")
    
    print("\n" + "=" * 50)
    print("✅ Monitoring complete")


if __name__ == "__main__":
    main()

