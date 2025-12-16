from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
import os


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
}

# Define the DAG
dag = DAG(
    'ticket_urgency_model_training',
    default_args=default_args,
    schedule_interval='@daily',  # Run this DAG daily (adjust as needed)
)

# Define the task in the DAG
train_task = PythonOperator(
    task_id='train_ticket_urgency_model',
    python_callable=run_train_script,
    dag=dag,
)

