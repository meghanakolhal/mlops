from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
import sys
import os


def check_model_exists():
    """
    Check if model exists in GCS using Python (not gsutil).
    This uses google-cloud-storage library which is already installed.
    """
    from google.cloud import storage
    
    bucket_name = "ml-model-bucket-22"
    model_path = "ticket_urgency_model/ticket_urgency_model.pkl"
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(model_path)
        
        if blob.exists():
            print(f"✅ Model exists: gs://{bucket_name}/{model_path}")
            print(f"   Size: {blob.size} bytes")
            print(f"   Updated: {blob.updated}")
            return True
        else:
            print(f"⚠️  Model not found: gs://{bucket_name}/{model_path}")
            return False
    except Exception as e:
        print(f"❌ Error checking model: {e}")
        raise


def run_train_script():
    """
    Directly call the training script's main() so that:
    - All logs appear in the Airflow task log
    - Any error in training causes the task to fail
    """
    # Ensure /opt/airflow is on sys.path so we can import scripts.train
    airflow_root = "/opt/airflow"
    if airflow_root not in sys.path:
        sys.path.insert(0, airflow_root)

    from scripts.train import main

    # Use the same default MLflow URI as in train.py (can be overridden via env)
    os.environ.setdefault("MLFLOW_TRACKING_URI", "http://mlflow:5000/")

    main()

# Define the default_args for the DAG
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'start_date': datetime(2025, 12, 16),  # Adjust start date as necessary
    # 'email': ['team@example.com'],
    # 'email_on_failure': True,
}

# Define the DAG
dag = DAG(
    'ticket_urgency_model_training',
    default_args=default_args,
    description='This DAG is used to train the ticket urgency model',
    schedule_interval='@daily',  # Run this DAG daily (adjust as needed)
    catchup=False,
)

# Define the task in the DAG
train_task = PythonOperator(
    task_id='train_ticket_urgency_model',
    python_callable=run_train_script,
    dag=dag,
)

# Example: PythonOperator (checks model in GCS using Python library)
check_model_task = PythonOperator(
    task_id='check_model_exists',
    python_callable=check_model_exists,
    dag=dag,
)

# Example: BashOperator (simple bash command - works without external tools)
print_info_task = BashOperator(
    task_id='print_environment_info',
    bash_command='echo "Training DAG started at $(date)" && echo "Python version: $(python --version)" && ls -la /opt/airflow/scripts/ | head -5',
    dag=dag,
)

# Task dependencies: print_info -> check_model -> train
print_info_task >> check_model_task >> train_task