from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
import sys
import os
import requests


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


def reload_model_in_api():
    """
    Automatically reload the model in the API after training completes.
    This calls the /reload-model endpoint to clear cache and load the new model.
    """
    api_url = os.getenv("API_URL", "https://ticket-urgency-api-7j3n5753uq-el.a.run.app")
    reload_endpoint = f"{api_url}/reload-model"
    
    try:
        print(f"🔄 Reloading model in API: {reload_endpoint}")
        
        # Call the reload endpoint
        response = requests.post(
            reload_endpoint,
            headers={"Content-Length": "0"},
            timeout=30  # Give it time to download model from GCS
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Model reloaded successfully!")
            print(f"   Status: {result.get('status')}")
            print(f"   Model loaded: {result.get('model_loaded')}")
            print(f"   Model path: {result.get('model_path')}")
            return True
        else:
            print(f"⚠️  Reload endpoint returned status {response.status_code}")
            print(f"   Response: {response.text}")
            # Don't fail the DAG - model reload is optional
            return False
            
    except requests.exceptions.Timeout:
        print(f"⚠️  Timeout calling reload endpoint (model may still be downloading)")
        print(f"   You can manually reload later: curl -X POST {reload_endpoint} -H 'Content-Length: 0'")
        return False
    except Exception as e:
        print(f"⚠️  Failed to reload model automatically: {e}")
        print(f"   Model is uploaded to GCS, but API may still be using old model")
        print(f"   You can manually reload: curl -X POST {reload_endpoint} -H 'Content-Length: 0'")
        # Don't fail the DAG - model reload is optional
        return False

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

# Define the tasks in the DAG

# Example: BashOperator (simple bash command - works without external tools)
print_info_task = BashOperator(
    task_id='print_environment_info',
    bash_command='echo "Training DAG started at $(date)" && echo "Python version: $(python --version)" && ls -la /opt/airflow/scripts/ | head -5',
    dag=dag,
)

# Example: PythonOperator (checks model in GCS using Python library)
check_model_task = PythonOperator(
    task_id='check_model_exists',
    python_callable=check_model_exists,
    dag=dag,
)

# Training task
train_task = PythonOperator(
    task_id='train_ticket_urgency_model',
    python_callable=run_train_script,
    dag=dag,
)

# Automatic model reload task (runs after training succeeds)
reload_model_task = PythonOperator(
    task_id='reload_model_in_api',
    python_callable=reload_model_in_api,
    dag=dag,
)

# Task dependencies: print_info -> check_model -> train -> reload_model
print_info_task >> check_model_task >> train_task >> reload_model_task