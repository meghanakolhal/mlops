# Dockerfile for Cloud Run deployment
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Set environment variables
ENV PORT=8080
ENV GCS_BUCKET_NAME=ml-model-bucket-22
ENV MODEL_GCS_PATH=ticket_urgency_model/ticket_urgency_model.pkl

# Expose port
EXPOSE 8080

# Run the application using uvicorn (ASGI server for FastAPI)
CMD exec uvicorn app:app --host 0.0.0.0 --port $PORT

