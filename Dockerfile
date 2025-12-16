FROM apache/airflow:2.9.3-python3.11

USER airflow
COPY service-acc-key.json /opt/airflow/.google/credentials.json

ENV GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/.google/credentials.json


# Install necessary Python packages for your project (including GCS and MLflow)
RUN pip install --no-cache-dir \
    scikit-learn \
    pandas \
    numpy \
    mlflow \
    google-cloud-storage  # Install Google Cloud Storage client

USER airflow
