from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
import os


def run_monitoring_script():
    """
    Run the monitoring script's main() so that:
    - All monitoring logs appear in the Airflow task log
    - Any error in monitoring causes the task to fail
    """
    # Ensure /opt/airflow is on sys.path so we can import scripts.monitor_model
    airflow_root = "/opt/airflow"
    if airflow_root not in sys.path:
        sys.path.insert(0, airflow_root)

    # Configure default credentials for GCS inside the Airflow container
    # This mirrors how training uses service-acc-key.json from the project root.
    default_key_path = os.path.join(airflow_root, "service-acc-key.json")
    if os.path.isfile(default_key_path):
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", default_key_path)

    # Point monitoring script at the deployed Cloud Run API
    # (override from Airflow UI / env if needed)
    os.environ.setdefault(
        "API_URL",
        "https://ticket-urgency-api-7j3n5753uq-el.a.run.app",
    )

    from scripts.monitor_model import main

    main()


# Default arguments for the monitoring DAG
default_args = {
    "owner": "airflow",
    "retries": 1,
    "start_date": datetime(2025, 12, 16),  # Adjust as needed
}


# Define the DAG
dag = DAG(
    "ticket_urgency_model_monitoring",
    default_args=default_args,
    schedule_interval="@daily",  # Run daily; you can trigger manually from UI
)


# Single task: run the monitoring script
monitor_task = PythonOperator(
    task_id="monitor_ticket_urgency_model",
    python_callable=run_monitoring_script,
    dag=dag,
)

