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
API_URL = os.getenv("API_URL", "https://ticket-urgency-api-xxxxx.run.app")
DATA_PATH = os.path.join("data", "raw", "tickets.csv")


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
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}


def test_prediction():
    """Test API prediction endpoint."""
    test_data = {
        "title": "Server down",
        "description": "Production server is not responding",
        "source": "email",
        "customer_tier": "premium"
    }
    
    try:
        response = requests.post(f"{API_URL}/predict", json=test_data, timeout=10)
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
    
    # 3. Check data drift (if new data available)
    print("\n3. Checking for data drift...")
    try:
        reference_data = pd.read_csv(DATA_PATH)
        # In production, fetch recent production data
        # For now, use same data as reference
        drift_detected, drift_report = check_data_drift(reference_data, reference_data)
        
        if drift_detected:
            print("⚠️  Data drift detected!")
            print(json.dumps(drift_report, indent=2))
        else:
            print("✅ No significant data drift detected")
    except Exception as e:
        print(f"⚠️  Could not check data drift: {e}")
    
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

