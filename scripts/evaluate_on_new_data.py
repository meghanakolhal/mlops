"""
Evaluate trained model performance on new production data.
This helps understand if model performance degrades due to data drift.
"""
import os
import pandas as pd
import joblib
from google.cloud import storage
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import tempfile

# Configuration
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
MODEL_GCS_PATH = "ticket_urgency_model/ticket_urgency_model.pkl"
NEW_DATA_GCS_PATH = "datasets/new_tickets.csv"

# Ensure GCP credentials
DEFAULT_GCP_KEY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "service-acc-key.json")
)
if (
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    and os.path.isfile(DEFAULT_GCP_KEY_PATH)
):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = DEFAULT_GCP_KEY_PATH


def load_model_from_gcs():
    """Load model from GCS."""
    print(f"Loading model from gs://{BUCKET_NAME}/{MODEL_GCS_PATH}...")
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(MODEL_GCS_PATH)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as tmp_file:
        blob.download_to_filename(tmp_file.name)
        model = joblib.load(tmp_file.name)
        os.unlink(tmp_file.name)
    
    print("✅ Model loaded successfully")
    return model


def load_data_from_gcs(gcs_path):
    """Load CSV data from GCS."""
    print(f"Loading data from gs://{BUCKET_NAME}/{gcs_path}...")
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp_file:
        blob.download_to_filename(tmp_file.name)
        df = pd.read_csv(tmp_file.name)
        os.unlink(tmp_file.name)
    
    print(f"✅ Loaded {len(df)} rows")
    return df


def prepare_features(df):
    """Prepare features same way as training."""
    df = df.copy()
    df["text"] = df["title"].astype(str) + " " + df["description"].astype(str)
    return df[["text", "source", "customer_tier"]], df["label_urgency"]


def main():
    print("=" * 60)
    print("Model Performance Evaluation on New Data")
    print("=" * 60)
    
    # Load model
    model = load_model_from_gcs()
    
    # Load new data
    df = load_data_from_gcs(NEW_DATA_GCS_PATH)
    
    # Prepare features
    X, y_true = prepare_features(df)
    
    # Make predictions
    print("\nMaking predictions...")
    y_pred = model.predict(X)
    
    # Calculate metrics
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, pos_label="urgent", zero_division=0)
    recall = recall_score(y_true, y_pred, pos_label="urgent", zero_division=0)
    f1 = f1_score(y_true, y_pred, pos_label="urgent", zero_division=0)
    
    # Print results
    print("\n" + "=" * 60)
    print("Performance Metrics on New Data:")
    print("=" * 60)
    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1-score : {f1:.4f}")
    
    print("\n" + "=" * 60)
    print("Classification Report:")
    print("=" * 60)
    print(classification_report(y_true, y_pred, target_names=["normal", "urgent"]))
    
    # Show distribution comparison
    print("\n" + "=" * 60)
    print("Data Distribution (New Data):")
    print("=" * 60)
    print("\nSource distribution:")
    print(df["source"].value_counts(normalize=True))
    print("\nCustomer tier distribution:")
    print(df["customer_tier"].value_counts(normalize=True))
    print("\nLabel distribution:")
    print(df["label_urgency"].value_counts(normalize=True))
    
    print("\n" + "=" * 60)
    print("✅ Evaluation complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
