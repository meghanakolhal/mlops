"""
Script to upload training data and new production data to GCS.
Run this once to set up your GCS bucket with data files.
"""
import os
from google.cloud import storage

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
LOCAL_TRAINING_DATA = os.path.join("data", "raw", "tickets.csv")
LOCAL_NEW_DATA = os.path.join("data", "raw", "new_tickets.csv")
GCS_TRAINING_DATA_PATH = "datasets/tickets.csv"
GCS_NEW_DATA_PATH = "datasets/new_tickets.csv"

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
        print(f"❌ File not found: {local_path}")
        return False
    
    try:
        print(f"Uploading {local_path} to gs://{bucket_name}/{gcs_path}...")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        print(f"✅ Successfully uploaded to gs://{bucket_name}/{gcs_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to upload: {e}")
        return False


def main():
    print("=" * 60)
    print("Uploading Data Files to GCS")
    print("=" * 60)
    
    # Upload training data (reference data)
    print("\n1. Uploading training/reference data...")
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
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ All files uploaded successfully!")
        print(f"\nReference data: gs://{BUCKET_NAME}/{GCS_TRAINING_DATA_PATH}")
        print(f"New data: gs://{BUCKET_NAME}/{GCS_NEW_DATA_PATH}")
    else:
        print("⚠️  Some uploads failed. Check errors above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
