import os
import sys
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import mlflow
import mlflow.sklearn
from google.cloud import storage  # For GCS upload

# Ensure GCP credentials are picked up when running inside Airflow
DEFAULT_GCP_KEY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "service-acc-key.json")
)
if (
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    and os.path.isfile(DEFAULT_GCP_KEY_PATH)
):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = DEFAULT_GCP_KEY_PATH

# Set paths for data and model
# Load training data from GCS
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "ml-model-bucket-22")
# Use combined data if available (reference + new), otherwise use reference only
GCS_DATA_PATH = os.getenv("GCS_DATA_PATH", "datasets/combined_tickets.csv")  # Combined data for retraining
GCS_REFERENCE_DATA_PATH = "datasets/tickets.csv"  # Reference data (frozen snapshot)
LOCAL_DATA_PATH = os.path.join("data", "raw", "tickets.csv")  # Fallback to local if GCS fails
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "ticket_urgency_model.pkl")

RANDOM_STATE = 42

# MLflow config: local file backend in ./mlruns
# MLFLOW_TRACKING_URI = "file:mlruns"
# Allow override via env (use container hostname by default)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000/")
EXPERIMENT_NAME = "ticket_urgency_experiment"



# Function to load data from GCS or local fallback
def load_data(gcs_bucket: str, gcs_path: str, local_fallback: str) -> pd.DataFrame:
    """
    Try to load data from GCS first, fallback to local file if GCS fails.
    """
    try:
        print(f"Attempting to load data from GCS: gs://{gcs_bucket}/{gcs_path}")
        client = storage.Client()
        bucket = client.bucket(gcs_bucket)
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            print(f"⚠️  File not found in GCS: gs://{gcs_bucket}/{gcs_path}")
            print(f"Falling back to local file: {local_fallback}")
            if os.path.exists(local_fallback):
                df = pd.read_csv(local_fallback)
                print(f"✅ Loaded {len(df)} rows from local file")
                return df
            else:
                raise FileNotFoundError(f"Neither GCS nor local file found: {local_fallback}")
        
        # Download from GCS to temp file and load
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp_file:
            blob.download_to_filename(tmp_file.name)
            df = pd.read_csv(tmp_file.name)
            os.unlink(tmp_file.name)  # Clean up temp file
        
        print(f"✅ Loaded {len(df)} rows from GCS: gs://{gcs_bucket}/{gcs_path}")
        return df
    except Exception as e:
        print(f"⚠️  Failed to load from GCS: {e}")
        print(f"Falling back to local file: {local_fallback}")
        if os.path.exists(local_fallback):
            df = pd.read_csv(local_fallback)
            print(f"✅ Loaded {len(df)} rows from local file")
            return df
        else:
            raise FileNotFoundError(f"Failed to load data from both GCS and local: {e}")


# Function to prepare data: text + categorical features
def prepare_data(df: pd.DataFrame):
    df = df.copy()
    df["text"] = df["title"].astype(str) + " " + df["description"].astype(str)

    feature_cols = ["text", "source", "customer_tier"]
    target_col = "label_urgency"

    X = df[feature_cols]
    y = df[target_col]

    return X, y


# Function to split data into train/validation/test
def split_data(X, y):
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y
    )

    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val,
        y_train_val,
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=y_train_val
    )

    print(f"Train size: {len(X_train)}")
    print(f"Validation size: {len(X_val)}")
    print(f"Test size: {len(X_test)}")

    return X_train, X_val, X_test, y_train, y_val, y_test
# Function to upload the model to GCS
def upload_model_to_gcs(model_path, bucket_name, gcs_path):
    """Uploads the model to GCS"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")

    try:
        print(f"Uploading model to GCS: gs://{bucket_name}/{gcs_path}")
        sys.stdout.flush()
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(model_path)
        print(f"Model uploaded to gs://{bucket_name}/{gcs_path}")
        sys.stdout.flush()
    except Exception as exc:
        # Log detailed error before raising
        print(f"Failed to upload model to GCS: {exc}")
        import traceback
        print(traceback.format_exc())
        sys.stdout.flush()
        # Raise after logging so Airflow marks task as failed
        raise


# Function to build the model pipeline
def build_pipeline():
    text_feature = "text"
    categorical_features = ["source", "customer_tier"]

    # Hyperparameters for the model
    tfidf_ngram_min = 1
    tfidf_ngram_max = 2
    tfidf_max_features = 5000
    log_reg_max_iter = 1000

    # Text transformer (TF-IDF)
    text_transformer = TfidfVectorizer(
        ngram_range=(tfidf_ngram_min, tfidf_ngram_max),
        max_features=tfidf_max_features,
    )

    # Categorical transformer (OneHotEncoder)
    categorical_transformer = OneHotEncoder(handle_unknown="ignore")

    # Preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("text", text_transformer, text_feature),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    # Logistic regression classifier
    classifier = LogisticRegression(
        max_iter=log_reg_max_iter,
        class_weight="balanced",
        n_jobs=None,  # Avoid FutureWarning about n_jobs
    )

    # Full pipeline with preprocessing and classifier
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    # Hyperparameters to log to MLflow
    hyperparams = {
        "tfidf_ngram_min": tfidf_ngram_min,
        "tfidf_ngram_max": tfidf_ngram_max,
        "tfidf_max_features": tfidf_max_features,
        "log_reg_max_iter": log_reg_max_iter,
        "model_type": "logistic_regression",
    }

    return model, hyperparams


# Function to evaluate the model
def evaluate_model(model, X, y, split_name: str):
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


# Function to save the model locally and upload to GCS
def save_model(model, path: str):
    """Save model locally and upload to GCS"""
    # Ensure model directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Save model locally
    joblib.dump(model, path)
    print(f"\nSaved trained model pipeline to: {path}")
    sys.stdout.flush()
    
    # Upload to GCS
    bucket_name = GCS_BUCKET_NAME
    destination_blob_name = 'ticket_urgency_model/ticket_urgency_model.pkl'  # Destination path in GCS

    # Upload to GCS (argument order: model_path, bucket_name, gcs_path)
    upload_model_to_gcs(path, bucket_name, destination_blob_name)




# Main function to run the entire pipeline
def main():
    # Configure MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Start a new MLflow run
    with mlflow.start_run(run_name="baseline_log_reg") as run:
        print(f"MLflow run_id: {run.info.run_id}")

        # 1. Load data from GCS (with local fallback)
        # Try combined data first (for retraining), fallback to reference data
        try:
            df = load_data(GCS_BUCKET_NAME, GCS_DATA_PATH, LOCAL_DATA_PATH)
            # combined data here is new data which was created for detecting data drfit
            print(f"✅ Using combined dataset: {GCS_DATA_PATH}")
        except FileNotFoundError:
            print(f"⚠️  Combined data not found: {GCS_DATA_PATH}")
            # reference dat here is old data which is being considered as so, so that data drift could be detected 
            print(f"   Falling back to reference data: {GCS_REFERENCE_DATA_PATH}")
            df = load_data(GCS_BUCKET_NAME, GCS_REFERENCE_DATA_PATH, LOCAL_DATA_PATH)

        # 2. Prepare features and target
        X, y = prepare_data(df)

        # 3. Split into train/val/test
        X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

        # 4. Build model pipeline + hyperparameters
        model, hyperparams = build_pipeline()

        # Log hyperparameters to MLflow
        for name, value in hyperparams.items():
            mlflow.log_param(name, value)

        # 5. Train model
        print("\nTraining model...")
        model.fit(X_train, y_train)
        print("Training complete.")

        # 6. Evaluate on train/val/test
        train_metrics = evaluate_model(model, X_train, y_train, "Train")
        val_metrics = evaluate_model(model, X_val, y_val, "Validation")
        test_metrics = evaluate_model(model, X_test, y_test, "Test")

        # Log metrics (mainly from validation and test)
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

        # 7. Save trained model locally and upload to GCS
        try:
            save_model(model, MODEL_PATH)
            sys.stdout.flush()  # Ensure output is flushed
        except Exception as e:
            print(f"\n⚠️  Error during model save/upload: {e}")
            import traceback
            print(traceback.format_exc())
            sys.stdout.flush()
            raise  # Re-raise to mark task as failed in Airflow

        # 8. (Optional) Log model file as MLflow artifact.
        # This can fail if the MLflow server's artifact root points to a path
        # that is not writable from this container (e.g., '/mlflow').
        # If needed later, configure a proper artifact store and re-enable.
        # mlflow.log_artifact(MODEL_PATH, artifact_path="model")

        print("\nRun finished. Metrics logged to MLflow and model saved/uploaded.")
        print(f"\n🏃 View run baseline_log_reg at: {MLFLOW_TRACKING_URI}#/experiments/1/runs/{run.info.run_id}")
        print(f"🧪 View experiment at: {MLFLOW_TRACKING_URI}#/experiments/1")
        sys.stdout.flush()  # Ensure final output is flushed


if __name__ == "__main__":
    main()
