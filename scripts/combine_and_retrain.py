"""
Script to combine reference data + new data and retrain model.
Run this when new production data arrives and drift is detected.
"""
import os
import pandas as pd
from google.cloud import storage
import joblib
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Import functions from train.py
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.train import (
    prepare_data, build_pipeline, upload_model_to_gcs, RANDOM_STATE
)

# Configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
REFERENCE_DATA_GCS_PATH = "datasets/tickets.csv"
NEW_DATA_GCS_PATH = "datasets/new_tickets.csv"
COMBINED_DATA_GCS_PATH = "datasets/combined_tickets.csv"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "ticket_urgency_model.pkl")
LOCAL_DATA_FALLBACK = os.path.join("data", "raw", "tickets.csv")

# MLflow config
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000/")
EXPERIMENT_NAME = "ticket_urgency_experiment"

# Ensure GCP credentials
DEFAULT_GCP_KEY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "service-acc-key.json")
)
if (
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    and os.path.isfile(DEFAULT_GCP_KEY_PATH)
):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = DEFAULT_GCP_KEY_PATH


def load_data_from_gcs(bucket_name: str, gcs_path: str, local_fallback: str = None):
    """Load CSV data from GCS."""
    try:
        print(f"Loading data from GCS: gs://{bucket_name}/{gcs_path}")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            if local_fallback and os.path.exists(local_fallback):
                print(f"⚠️  GCS file not found, using local fallback: {local_fallback}")
                return pd.read_csv(local_fallback)
            raise FileNotFoundError(f"Data not found: gs://{bucket_name}/{gcs_path}")
        
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


def upload_combined_data_to_gcs(df: pd.DataFrame, bucket_name: str, gcs_path: str):
    """Upload combined DataFrame to GCS."""
    import tempfile
    try:
        print(f"Uploading combined data to gs://{bucket_name}/{gcs_path}...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            df.to_csv(tmp_file.name, index=False)
            tmp_path = tmp_file.name
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(tmp_path)
        os.unlink(tmp_path)
        print(f"✅ Combined data uploaded: {len(df)} rows")
    except Exception as e:
        print(f"❌ Failed to upload combined data: {e}")
        raise


def split_data(X, y):
    """Split data into train/val/test."""
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.25, random_state=RANDOM_STATE, stratify=y_train_val
    )
    print(f"Train size: {len(X_train)}, Val size: {len(X_val)}, Test size: {len(X_test)}")
    return X_train, X_val, X_test, y_train, y_val, y_test


def evaluate_model(model, X, y, split_name: str):
    """Evaluate model and return metrics."""
    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred, pos_label="urgent")
    recall = recall_score(y, y_pred, pos_label="urgent")
    f1 = f1_score(y, y_pred, pos_label="urgent")
    print(f"\n=== {split_name} Metrics ===")
    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1-score : {f1:.4f}")
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main():
    """Combine reference + new data and retrain model."""
    print("=" * 60)
    print("Combining Data and Retraining Model")
    print("=" * 60)
    
    # Configure MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    with mlflow.start_run(run_name="retrain_with_new_data") as run:
        print(f"MLflow run_id: {run.info.run_id}")
        
        # 1. Load reference data
        print("\n1. Loading reference data...")
        reference_data = load_data_from_gcs(
            GCS_BUCKET_NAME, REFERENCE_DATA_GCS_PATH, LOCAL_DATA_FALLBACK
        )
        print(f"   Reference data: {len(reference_data)} rows")
        
        # 2. Load new data
        print("\n2. Loading new production data...")
        try:
            new_data = load_data_from_gcs(GCS_BUCKET_NAME, NEW_DATA_GCS_PATH, None)
            print(f"   New data: {len(new_data)} rows")
        except FileNotFoundError:
            print(f"⚠️  New data not found at gs://{GCS_BUCKET_NAME}/{NEW_DATA_GCS_PATH}")
            print("   Training only on reference data")
            new_data = None
        
        # 3. Combine data
        if new_data is not None:
            print("\n3. Combining reference + new data...")
            combined_data = pd.concat([reference_data, new_data], ignore_index=True)
            print(f"   Combined data: {len(combined_data)} rows")
            
            # Upload combined data to GCS for future reference
            upload_combined_data_to_gcs(
                combined_data, GCS_BUCKET_NAME, COMBINED_DATA_GCS_PATH
            )
            training_data = combined_data
        else:
            training_data = reference_data
        
        # 4. Prepare features
        print("\n4. Preparing features...")
        X, y = prepare_data(training_data)
        
        # 5. Split data
        print("\n5. Splitting data...")
        X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)
        
        # 6. Build and train model
        print("\n6. Building and training model...")
        model, hyperparams = build_pipeline()
        
        # Log hyperparameters
        for name, value in hyperparams.items():
            mlflow.log_param(name, value)
        mlflow.log_param("training_data_size", len(training_data))
        mlflow.log_param("combined_with_new_data", new_data is not None)
        
        print("Training model...")
        model.fit(X_train, y_train)
        print("Training complete.")
        
        # 7. Evaluate
        print("\n7. Evaluating model...")
        train_metrics = evaluate_model(model, X_train, y_train, "Train")
        val_metrics = evaluate_model(model, X_val, y_val, "Validation")
        test_metrics = evaluate_model(model, X_test, y_test, "Test")
        
        # Log metrics
        mlflow.log_metric("train_accuracy", train_metrics["accuracy"])
        mlflow.log_metric("train_f1", train_metrics["f1"])
        mlflow.log_metric("val_accuracy", val_metrics["accuracy"])
        mlflow.log_metric("val_precision", val_metrics["precision"])
        mlflow.log_metric("val_recall", val_metrics["recall"])
        mlflow.log_metric("val_f1", val_metrics["f1"])
        mlflow.log_metric("test_accuracy", test_metrics["accuracy"])
        mlflow.log_metric("test_precision", test_metrics["precision"])
        mlflow.log_metric("test_recall", test_metrics["recall"])
        mlflow.log_metric("test_f1", test_metrics["f1"])
        
        # 8. Save and upload model
        print("\n8. Saving and uploading model...")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        print(f"Saved model to: {MODEL_PATH}")
        
        # Upload to GCS (this updates the model file, triggering API reload)
        bucket_name = GCS_BUCKET_NAME
        destination_blob_name = 'ticket_urgency_model/ticket_urgency_model.pkl'
        upload_model_to_gcs(MODEL_PATH, bucket_name, destination_blob_name)
        
        print("\n" + "=" * 60)
        print("✅ Retraining complete!")
        print(f"   Model saved to: {MODEL_PATH}")
        print(f"   Model uploaded to: gs://{bucket_name}/{destination_blob_name}")
        print("\n⚠️  Next step: API will auto-reload model (checks version on next request)")
        print("   Or call: curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model")
        print("=" * 60)


if __name__ == "__main__":
    main()
