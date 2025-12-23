FROM apache/airflow:2.9.3-python3.11

USER airflow
COPY service-acc-key.json /opt/airflow/.google/credentials.json

ENV GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/.google/credentials.json


# Install necessary Python packages for your project (including GCS and MLflow)
# Note: Evidently AI 0.4.15 requires pydantic<2.0.0
# Force reinstall pydantic 1.x before installing Evidently (pydantic-core will be auto-installed)
RUN pip uninstall -y pydantic pydantic-core 2>/dev/null || true && \
    pip install --no-cache-dir \
    "pydantic==1.10.13" && \
    pip install --no-cache-dir \
    scikit-learn \
    pandas \
    numpy \
    mlflow \
    google-cloud-storage \
    requests \
    "evidently==0.4.15"  # Install Google Cloud Storage client, Evidently AI for monitoring

USER airflow
