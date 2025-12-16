import os
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
DATA_PATH = os.path.join("data", "raw", "tickets.csv")
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "ticket_urgency_model.pkl")

RANDOM_STATE = 42

# MLflow config: local file backend in ./mlruns
# MLFLOW_TRACKING_URI = "file:mlruns"
# Allow override via env (use container hostname by default)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000/")
EXPERIMENT_NAME = "ticket_urgency_experiment"



# Function to load data
def load_data(path: str) -> pd.DataFrame:
    print(f"Loading data from: {path}")
    df = pd.read_csv(path)
    return df


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
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(model_path)
        print(f"Model uploaded to gs://{bucket_name}/{gcs_path}")
    except Exception as exc:
        # Raise after logging so Airflow marks task as failed
        print(f"Failed to upload model to GCS: {exc}")
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


# Function to save the model locally
def save_model(model, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    print(f"\nSaved trained model pipeline to: {path}")
    
    
    bucket_name = 'ml-model-bucket-22'  # Replace with your actual bucket name
    destination_blob_name = 'ticket_urgency_model/ticket_urgency_model.pkl'  # Destination path in GCS

    # Upload to GCS (argument order: model_path, bucket_name, gcs_path)
    upload_model_to_gcs(MODEL_PATH, bucket_name, destination_blob_name)




# Main function to run the entire pipeline
def main():
    # Configure MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Start a new MLflow run
    with mlflow.start_run(run_name="baseline_log_reg") as run:
        print(f"MLflow run_id: {run.info.run_id}")

        # 1. Load data
        df = load_data(DATA_PATH)

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

        # 7. Save trained model locally
        save_model(model, MODEL_PATH)

        # 8. (Optional) Log model file as MLflow artifact.
        # This can fail if the MLflow server's artifact root points to a path
        # that is not writable from this container (e.g., '/mlflow').
        # If needed later, configure a proper artifact store and re-enable.
        # mlflow.log_artifact(MODEL_PATH, artifact_path="model")

        print("\nRun finished. Metrics logged to MLflow and model saved/uploaded.")


if __name__ == "__main__":
    main()
