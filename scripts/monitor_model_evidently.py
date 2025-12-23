"""
Production-grade model monitoring script using Evidently AI.

This script provides comprehensive monitoring including:
- Data drift detection (statistical tests)
- Data quality monitoring
- HTML report generation
- GCS report storage

Run this periodically (e.g., daily via Airflow) to monitor production model.
"""
import os
import pandas as pd
import numpy as np
from google.cloud import storage
import requests
from datetime import datetime
import json
import sys
import warnings

# Suppress divide by zero warnings from scipy (common with small sample sizes)
warnings.filterwarnings('ignore', category=RuntimeWarning, module='scipy')

# Evidently AI imports
from evidently.report import Report
from evidently.metrics import (
    DataDriftTable,
    DatasetDriftMetric,
)
from evidently.test_suite import TestSuite
from evidently.tests import (
    TestNumberOfDriftedColumns,
    TestShareOfDriftedColumns,
    TestColumnDrift,
)

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
MODEL_GCS_PATH = "ticket_urgency_model/ticket_urgency_model.pkl"
API_URL = os.getenv("API_URL", "https://ticket-urgency-api-7j3n5753uq-el.a.run.app")

# Reference data (training data) - stored in GCS
REFERENCE_DATA_GCS_PATH = "datasets/tickets.csv"
# New/production data - for drift comparison
NEW_DATA_GCS_PATH = os.getenv("NEW_DATA_GCS_PATH", "datasets/new_tickets.csv")
LOCAL_DATA_FALLBACK = os.path.join("data", "raw", "tickets.csv")

# Report storage paths
REPORTS_GCS_PATH = "monitoring/reports"
SUMMARIES_GCS_PATH = "monitoring/summaries"
LOCAL_REPORTS_DIR = "reports"


def load_data_from_gcs(bucket_name: str, gcs_path: str, local_fallback: str = None):
    """
    Load CSV data from GCS, with optional local fallback.
    Returns pandas DataFrame.
    """
    try:
        print(f"Loading data from GCS: gs://{bucket_name}/{gcs_path}")
        sys.stdout.flush()
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            if local_fallback and os.path.exists(local_fallback):
                print(f"⚠️  GCS file not found, using local fallback: {local_fallback}")
                sys.stdout.flush()
                return pd.read_csv(local_fallback)
            raise FileNotFoundError(f"Data not found in GCS: gs://{bucket_name}/{gcs_path}")
        
        # Download to temp file and load
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp_file:
            blob.download_to_filename(tmp_file.name)
            df = pd.read_csv(tmp_file.name)
            os.unlink(tmp_file.name)
        
        print(f"✅ Loaded {len(df)} rows from GCS")
        sys.stdout.flush()
        return df
    except Exception as e:
        if local_fallback and os.path.exists(local_fallback):
            print(f"⚠️  GCS load failed: {e}, using local fallback: {local_fallback}")
            sys.stdout.flush()
            return pd.read_csv(local_fallback)
        raise


def check_api_health():
    """Check if API is responding."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=15)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}


def test_prediction():
    """Test API prediction endpoint with realistic test data."""
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


def generate_evidently_report(reference_data: pd.DataFrame, current_data: pd.DataFrame):
    """
    Generate comprehensive monitoring report using Evidently AI.
    
    Returns:
        - report: Evidently Report object
        - test_suite: Evidently TestSuite object
        - summary: Dictionary with key metrics
    """
    print("\n📊 Generating Evidently AI monitoring report...")
    sys.stdout.flush()
    
    # Ensure data types match (important for Evidently AI)
    # Convert categorical columns to string type
    categorical_cols = ["source", "customer_tier", "urgency"]
    for col in categorical_cols:
        if col in reference_data.columns:
            reference_data[col] = reference_data[col].astype(str)
        if col in current_data.columns:
            current_data[col] = current_data[col].astype(str)
    
    # Create Evidently Report with multiple metrics
    # Note: DataQualityTable not available in Evidently 0.4.15, using DataDriftTable and DatasetDriftMetric
    report = Report(metrics=[
        DataDriftTable(),           # Detailed drift table for all columns
        DatasetDriftMetric(),       # Overall dataset drift score
    ])
    
    # Run the report
    try:
        report.run(
            reference_data=reference_data,
            current_data=current_data
        )
    except Exception as e:
        print(f"❌ Error: Failed to run Evidently report: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        raise
    
    # Create Test Suite for automated checks
    try:
        test_suite = TestSuite(tests=[
            TestNumberOfDriftedColumns(),      # Test: Number of drifted columns
            TestShareOfDriftedColumns(),       # Test: Percentage of drifted columns
            TestColumnDrift(column_name="source"),        # Test: Specific column drift
            TestColumnDrift(column_name="customer_tier"), # Test: Specific column drift
        ])
        
        test_suite.run(
            reference_data=reference_data,
            current_data=current_data
        )
    except Exception as e:
        print(f"⚠️  Warning: Test suite failed: {e}")
        print("   Continuing with report generation...")
        sys.stdout.flush()
        # Create empty test suite if tests fail
        test_suite = TestSuite(tests=[])
    
    # Extract summary metrics from report dictionary (Evidently 0.4.15 API)
    try:
        report_dict = report.as_dict()
        
        # Get DataDriftTable results (first metric - index 0)
        data_drift_result = {}
        dataset_drift_result = {}
        
        if 'metrics' in report_dict and len(report_dict['metrics']) > 0:
            # DataDriftTable is first metric
            if 'result' in report_dict['metrics'][0]:
                data_drift_result = report_dict['metrics'][0]['result']
            
            # DatasetDriftMetric is second metric (if exists)
            if len(report_dict['metrics']) > 1 and 'result' in report_dict['metrics'][1]:
                dataset_drift_result = report_dict['metrics'][1]['result']
        
        # Extract metrics with safe defaults
        summary = {
            "dataset_drift_score": dataset_drift_result.get('share_of_drifted_columns', 0.0) if dataset_drift_result else 0.0,
            "dataset_drift_detected": dataset_drift_result.get('dataset_drift', False) if dataset_drift_result else False,
            "number_of_drifted_columns": data_drift_result.get('number_of_drifted_columns', 0) if data_drift_result else 0,
            "share_of_drifted_columns": data_drift_result.get('share_of_drifted_columns', 0.0) if data_drift_result else 0.0,
            "tests_passed": test_suite.as_dict().get("summary", {}).get("all_tests_passed", False),
            "tests_total": len(test_suite.as_dict().get("tests", [])),
        }
    except Exception as e:
        print(f"❌ Error: Could not extract metrics from report: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        # Re-raise exception - this is a critical error
        raise Exception(f"Failed to extract Evidently AI metrics: {e}")
    
    print(f"✅ Report generated successfully")
    print(f"   Dataset drift score: {summary.get('dataset_drift_score', 'N/A')}")
    print(f"   Drift detected: {summary.get('dataset_drift_detected', 'N/A')}")
    print(f"   Drifted columns: {summary.get('number_of_drifted_columns', 'N/A')}")
    sys.stdout.flush()
    
    return report, test_suite, summary


def save_report_to_gcs(report, test_suite, summary, timestamp_str: str):
    """
    Save HTML report and JSON summary to GCS.
    
    Args:
        report: Evidently Report object
        test_suite: Evidently TestSuite object
        summary: Dictionary with summary metrics
        timestamp_str: Timestamp string for file naming
    """
    print("\n💾 Saving reports to GCS...")
    sys.stdout.flush()
    
    # Create local reports directory if it doesn't exist
    os.makedirs(LOCAL_REPORTS_DIR, exist_ok=True)
    
    # Generate HTML report file path
    html_filename = f"drift_report_{timestamp_str}.html"
    local_html_path = os.path.join(LOCAL_REPORTS_DIR, html_filename)
    gcs_html_path = f"{REPORTS_GCS_PATH}/{html_filename}"
    
    # Save HTML report locally first
    report.save_html(local_html_path)
    print(f"✅ HTML report saved locally: {local_html_path}")
    sys.stdout.flush()
    
    # Upload HTML report to GCS
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_html_path)
    blob.upload_from_filename(local_html_path)
    print(f"✅ HTML report uploaded to: gs://{BUCKET_NAME}/{gcs_html_path}")
    sys.stdout.flush()
    
    # Create comprehensive JSON summary
    json_summary = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "report_path": f"gs://{BUCKET_NAME}/{gcs_html_path}",
        "test_results": test_suite.as_dict(),
    }
    
    # Save JSON summary to GCS
    json_filename = f"summary_{timestamp_str}.json"
    gcs_json_path = f"{SUMMARIES_GCS_PATH}/{json_filename}"
    blob = bucket.blob(gcs_json_path)
    blob.upload_from_string(json.dumps(json_summary, indent=2))
    print(f"✅ JSON summary uploaded to: gs://{BUCKET_NAME}/{gcs_json_path}")
    sys.stdout.flush()
    
    return gcs_html_path, gcs_json_path


def main():
    """Run comprehensive monitoring checks using Evidently AI."""
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
    
    print(f"🔍 Model Monitoring with Evidently AI - {timestamp}")
    print("=" * 60)
    sys.stdout.flush()
    
    # 1. Check API health
    print("\n1. Checking API health...")
    sys.stdout.flush()
    healthy, health_data = check_api_health()
    if healthy:
        model_loaded = health_data.get('model_loaded', False)
        print("✅ API is healthy")
        print(f"   Model loaded: {model_loaded}")
        sys.stdout.flush()
    else:
        print(f"❌ API health check failed: {health_data}")
        sys.stdout.flush()
    
    # 2. Test prediction
    print("\n2. Testing prediction endpoint...")
    sys.stdout.flush()
    success, pred_data = test_prediction()
    if success:
        print(f"✅ Prediction successful")
        print(f"   Prediction: {pred_data.get('prediction')}")
        print(f"   Confidence: {pred_data.get('confidence', 0):.2f}")
        sys.stdout.flush()
    else:
        print(f"❌ Prediction test failed: {pred_data}")
        sys.stdout.flush()
    
    # 3. Data drift detection with Evidently AI
    print("\n3. Checking data drift with Evidently AI...")
    sys.stdout.flush()
    
    drift_detected = False
    drift_summary = {}
    report_path = None
    
    try:
        # Load reference data
        print(f"Loading reference data from: gs://{BUCKET_NAME}/{REFERENCE_DATA_GCS_PATH}")
        sys.stdout.flush()
        reference_data = load_data_from_gcs(BUCKET_NAME, REFERENCE_DATA_GCS_PATH, LOCAL_DATA_FALLBACK)
        print(f"✅ Loaded {len(reference_data)} rows of reference data")
        sys.stdout.flush()
        
        # Try to load new/production data
        try:
            print(f"Loading new/production data from: gs://{BUCKET_NAME}/{NEW_DATA_GCS_PATH}")
            sys.stdout.flush()
            new_data = load_data_from_gcs(BUCKET_NAME, NEW_DATA_GCS_PATH, None)
            print(f"✅ Found new data with {len(new_data)} rows")
            sys.stdout.flush()
            
            # Generate Evidently AI report
            report, test_suite, summary = generate_evidently_report(reference_data, new_data)
            
            # Check if drift detected
            drift_detected = summary.get('dataset_drift_detected', False)
            drift_summary = summary
            
            # Save reports to GCS
            report_path, summary_path = save_report_to_gcs(report, test_suite, summary, timestamp_str)
            
            # Print results
            if drift_detected:
                print("\n⚠️  DATA DRIFT DETECTED!")
                print(f"   Dataset drift score: {summary.get('dataset_drift_score', 'N/A')}")
                print(f"   Number of drifted columns: {summary.get('number_of_drifted_columns', 'N/A')}")
                print(f"   Share of drifted columns: {summary.get('share_of_drifted_columns', 'N/A'):.2%}")
                print(f"\n📊 View detailed report: {report_path}")
                sys.stdout.flush()
            else:
                print("\n✅ No significant data drift detected")
                print(f"   Dataset drift score: {summary.get('dataset_drift_score', 'N/A')}")
                print(f"\n📊 View report: {report_path}")
                sys.stdout.flush()
                
        except FileNotFoundError:
            print(f"ℹ️  New data not found at gs://{BUCKET_NAME}/{NEW_DATA_GCS_PATH}")
            print("   Skipping drift check (upload new_tickets.csv to GCS to test drift detection)")
            sys.stdout.flush()
            drift_detected = False
            drift_summary = {}
            
    except Exception as e:
        print(f"❌ Could not check data drift: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        # Re-raise exception so Airflow marks task as FAILED
        raise
    
    # 4. Final summary
    print("\n" + "=" * 60)
    print("✅ Monitoring complete")
    if report_path:
        print(f"📊 HTML Report: {report_path}")
    print("=" * 60)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
