from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
import os


def run_retrain_script():
    """
    Run the combine and retrain script.
    Combines reference + new data and retrains model.
    """
    # Ensure /opt/airflow is on sys.path
    airflow_root = "/opt/airflow"
    if airflow_root not in sys.path:
        sys.path.insert(0, airflow_root)

    # Configure default credentials
    default_key_path = os.path.join(airflow_root, "service-acc-key.json")
    if os.path.isfile(default_key_path):
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", default_key_path)

    # Set MLflow URI
    os.environ.setdefault("MLFLOW_TRACKING_URI", "http://mlflow:5000/")

    from scripts.combine_and_retrain import main
    main()


# Default arguments
default_args = {
    "owner": "airflow",
    "retries": 1,
    "start_date": datetime(2025, 12, 16),
}


# Define the DAG
dag = DAG(
    "ticket_urgency_model_retrain",
    default_args=default_args,
    schedule_interval=None,  # Manual trigger only (or trigger when drift detected)
    description="Retrain model with combined reference + new data",
)


# Single task: combine and retrain
retrain_task = PythonOperator(
    task_id="retrain_with_combined_data",
    python_callable=run_retrain_script,
    dag=dag,
)
