"""
Airflow DAG for model monitoring using Evidently AI.

This DAG runs comprehensive monitoring including:
- API health checks
- Prediction testing
- Data drift detection (statistical tests)
- Data quality monitoring
- HTML report generation
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
import os


def run_evidently_monitoring():
    """
    Run the Evidently AI monitoring script's main() so that:
    - All monitoring logs appear in the Airflow task log
    - Any error in monitoring causes the task to fail
    """
    # Ensure /opt/airflow is on sys.path so we can import scripts.monitor_model_evidently
    airflow_root = "/opt/airflow"
    if airflow_root not in sys.path:
        sys.path.insert(0, airflow_root)

    # Configure default credentials for GCS inside the Airflow container
    default_key_path = os.path.join(airflow_root, "service-acc-key.json")
    if os.path.isfile(default_key_path):
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", default_key_path)

    # Point monitoring script at the deployed Cloud Run API
    os.environ.setdefault(
        "API_URL",
        "https://ticket-urgency-api-7j3n5753uq-el.a.run.app",
    )

    from scripts.monitor_model_evidently import main

    main()


# Default arguments for the monitoring DAG
default_args = {
    "owner": "airflow",
    "retries": 1,
    "start_date": datetime(2025, 12, 16),
}


# Define the DAG
dag = DAG(
    "ticket_urgency_model_monitoring_evidently",
    default_args=default_args,
    description="Model monitoring with Evidently AI - data drift detection, quality checks, and HTML reports",
    schedule_interval="@daily",  # Run daily; you can trigger manually from UI
    catchup=False,
)


# Single task: run the Evidently AI monitoring script
monitor_task = PythonOperator(
    task_id="monitor_with_evidently",
    python_callable=run_evidently_monitoring,
    dag=dag,
)
