"""
Script to upload training data and new production data to GCS.
Also combines reference + new data for retraining.

Workflow:
1. Upload reference data (frozen snapshot) → datasets/tickets.csv
2. Upload new production data → datasets/new_tickets.csv  
3. Combine reference + new → datasets/combined_tickets.csv (for retraining)
4. Run monitoring → compares reference vs new (detects drift)
5. Retrain → uses combined data
"""
import os
import pandas as pd
from google.cloud import storage

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
LOCAL_TRAINING_DATA = os.path.join("data", "raw", "tickets.csv")
LOCAL_NEW_DATA = os.path.join("data", "raw", "new_tickets.csv")
GCS_TRAINING_DATA_PATH = "datasets/tickets.csv"  # Reference (frozen snapshot)
GCS_NEW_DATA_PATH = "datasets/new_tickets.csv"  # New production data
GCS_COMBINED_DATA_PATH = "datasets/combined_tickets.csv"  # Reference + New (for retraining)

# Ensure GCP credentials are set
DEFAULT_GCP_KEY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "service-acc-key.json")
)
if (
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    and os.path.isfile(DEFAULT_GCP_KEY_PATH)
):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = DEFAULT_GCP_KEY_PATH


def upload_file_to_gcs(local_path: str, bucket_name: str, gcs_path: str):
    """Upload a file to GCS."""
    if not os.path.exists(local_path):
        print(f"[ERROR] File not found: {local_path}")
        return False
    
    try:
        print(f"Uploading {local_path} to gs://{bucket_name}/{gcs_path}...")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        print(f"[SUCCESS] Successfully uploaded to gs://{bucket_name}/{gcs_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to upload: {e}")
        return False


def combine_and_upload_data(bucket_name: str, gcs_ref_path: str, gcs_new_path: str, gcs_combined_path: str):
    """
    Combine reference data + new data and upload combined dataset to GCS.
    This combined dataset will be used for retraining.
    """
    try:
        print(f"\n3. Combining reference + new data...")
        
        # Download reference data from GCS
        print(f"   Downloading reference data from GCS...")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        ref_blob = bucket.blob(gcs_ref_path)
        
        import tempfile
        # Use binary mode and close file before reading (Windows compatibility)
        tmp_ref_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_ref:
                tmp_ref_path = tmp_ref.name
                ref_blob.download_to_filename(tmp_ref_path)
            ref_df = pd.read_csv(tmp_ref_path)
            os.unlink(tmp_ref_path)
            tmp_ref_path = None
        finally:
            if tmp_ref_path and os.path.exists(tmp_ref_path):
                try:
                    os.unlink(tmp_ref_path)
                except:
                    pass
        
        print(f"   [SUCCESS] Loaded {len(ref_df)} rows from reference data")
        
        # Download new data from GCS
        print(f"   Downloading new data from GCS...")
        new_blob = bucket.blob(gcs_new_path)
        tmp_new_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_new:
                tmp_new_path = tmp_new.name
                new_blob.download_to_filename(tmp_new_path)
            new_df = pd.read_csv(tmp_new_path)
            os.unlink(tmp_new_path)
            tmp_new_path = None
        finally:
            if tmp_new_path and os.path.exists(tmp_new_path):
                try:
                    os.unlink(tmp_new_path)
                except:
                    pass
        
        print(f"   [SUCCESS] Loaded {len(new_df)} rows from new data")
        
        # Combine datasets
        combined_df = pd.concat([ref_df, new_df], ignore_index=True)
        print(f"   [SUCCESS] Combined dataset: {len(combined_df)} total rows")
        
        # Upload combined dataset to GCS
        print(f"   Uploading combined data to gs://{bucket_name}/{gcs_combined_path}...")
        tmp_combined_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp_combined:
                tmp_combined_path = tmp_combined.name
            combined_df.to_csv(tmp_combined_path, index=False)
            combined_blob = bucket.blob(gcs_combined_path)
            combined_blob.upload_from_filename(tmp_combined_path)
            os.unlink(tmp_combined_path)
            tmp_combined_path = None
        finally:
            if tmp_combined_path and os.path.exists(tmp_combined_path):
                try:
                    os.unlink(tmp_combined_path)
                except:
                    pass
        
        print(f"   [SUCCESS] Combined data uploaded successfully!")
        return True
    except Exception as e:
        print(f"   [ERROR] Failed to combine data: {e}")
        return False


def main():
    print("=" * 60)
    print("Uploading Data Files to GCS")
    print("=" * 60)
    
    # Upload training data (reference data) - frozen snapshot
    print("\n1. Uploading training/reference data (frozen snapshot)...")
    success1 = upload_file_to_gcs(
        LOCAL_TRAINING_DATA,
        BUCKET_NAME,
        GCS_TRAINING_DATA_PATH
    )
    
    # Upload new production data (for drift testing)
    print("\n2. Uploading new production data (for drift testing)...")
    success2 = upload_file_to_gcs(
        LOCAL_NEW_DATA,
        BUCKET_NAME,
        GCS_NEW_DATA_PATH
    )
    
    # Combine reference + new data (for retraining)
    success3 = False
    if success1 and success2:
        success3 = combine_and_upload_data(
            BUCKET_NAME,
            GCS_TRAINING_DATA_PATH,
            GCS_NEW_DATA_PATH,
            GCS_COMBINED_DATA_PATH
        )
    
    print("\n" + "=" * 60)
    if success1 and success2 and success3:
        print("[SUCCESS] All files uploaded successfully!")
        print(f"\nData Structure:")
        print(f"   Reference (frozen): gs://{BUCKET_NAME}/{GCS_TRAINING_DATA_PATH}")
        print(f"   New production:     gs://{BUCKET_NAME}/{GCS_NEW_DATA_PATH}")
        print(f"   Combined (retrain): gs://{BUCKET_NAME}/{GCS_COMBINED_DATA_PATH}")
        print(f"\nNext Steps:")
        print(f"   1. Run monitoring DAG -> compares reference vs new (detects drift)")
        print(f"   2. Trigger training DAG -> uses combined data to retrain model")
        print(f"   3. Reload model in API -> curl -X POST <API_URL>/reload-model")
        print(f"   4. Test new model with curl commands")
    else:
        print("[WARNING] Some uploads failed. Check errors above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
