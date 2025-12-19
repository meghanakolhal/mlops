# MLOps Ticket Urgency Model - Deployment Roadmap

This document outlines the complete path from your current setup to a production-ready MLOps system for the Ticket Urgency Classification Model. This project demonstrates an end-to-end MLOps pipeline that automates model training, deployment, serving, and monitoring.

## 🎯 Project Overview

This project implements a complete MLOps pipeline for a **Ticket Urgency Classification Model** that predicts whether support tickets are urgent or non-urgent based on:
- **Text features**: Title + Description (using TF-IDF vectorization)
- **Categorical features**: Source (email/phone/web) and Customer Tier (premium/standard)

### What We're Achieving

1. **Automated Training Pipeline**: Daily model retraining via Airflow DAGs
2. **Experiment Tracking**: MLflow tracks all training runs, metrics, and hyperparameters
3. **Model Storage**: Trained models stored in Google Cloud Storage (GCS)
4. **Model Serving**: REST API deployed on Cloud Run for real-time predictions
5. **CI/CD Pipeline**: Automated deployment via GitHub Actions when code changes
6. **Model Monitoring**: Daily monitoring for API health, prediction quality, and data drift detection

### Project Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Local Development                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Airflow    │  │    MLflow    │  │   FastAPI    │     │
│  │  (Port 8085) │  │  (Port 5000) │  │  (Port 8000) │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Google Cloud Platform (GCP)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Cloud Run   │  │      GCS     │  │   Artifact   │     │
│  │  (API Serve) │  │ (Model Store)│  │   Registry   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions (CI/CD)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Auto-deploy on push to main branch                  │  │
│  │  Build → Push to Artifact Registry → Deploy Cloud Run│  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Current State ✅

- ✅ **Airflow DAG** for automated daily training
- ✅ **MLflow** for experiment tracking and metrics logging
- ✅ **GCS** for model storage (`gs://ml-model-bucket-22/ticket_urgency_model/`)
- ✅ **Docker Compose** for local development environment
- ✅ **FastAPI** service ready for deployment
- ✅ **GitHub Actions** workflow for CI/CD
- ✅ **Monitoring script** for model health and drift detection

## 🚀 Next Steps (Priority Order)

### Phase 1: Model Serving API (Week 1)

**Goal**: Deploy model as REST API on Cloud Run

**Tasks**:

1. **Test FastAPI service locally** (Local Testing):
   ```bash
   # Install dependencies
   cd api
   pip install -r requirements.txt
   
   # Set environment variables (optional, defaults are set in app.py)
   export GCS_BUCKET_NAME=ml-model-bucket-22
   export GOOGLE_APPLICATION_CREDENTIALS=../service-acc-key.json
   
   # Run FastAPI server
   uvicorn app:app --reload --port 8000
   
   # In another terminal, test the API
   curl http://localhost:8000/health
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Server down",
       "description": "Production server not responding",
       "source": "email",
       "customer_tier": "premium"
     }'
   ```

2. **Test Training Pipeline Locally** (Local Testing):
   ```bash
   # Start Docker Compose services
   docker compose up -d
   
   # Wait for services to be ready (check logs)
   docker compose logs -f airflow-scheduler
   
   # Run training script manually inside Airflow container
   docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"
   
   # Or trigger via Airflow UI: http://localhost:8085
   # Login: admin/admin
   # Find DAG: ticket_urgency_model_training
   # Click "Trigger DAG"
   ```

3. **Build and push Docker image to Artifact Registry** (For Manual Deployment Testing):
   ```bash
   # Authenticate to GCP
   gcloud auth login
   gcloud config set project ml-model-480910
   
   # Configure Docker for Artifact Registry
   gcloud auth configure-docker asia-south1-docker.pkg.dev
   
   # Build Docker image with branch name tag
   cd api
   BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD | tr '/' '-')
   IMAGE_URI="asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api"
   
   docker build -t ${IMAGE_URI}:${BRANCH_NAME} .
   docker tag ${IMAGE_URI}:${BRANCH_NAME} ${IMAGE_URI}:latest
   
   # Push to Artifact Registry
   docker push ${IMAGE_URI}:${BRANCH_NAME}
   docker push ${IMAGE_URI}:latest
   ```

4. **Deploy to Cloud Run** (Manual Deployment):
   ```bash
   # Deploy using the image from Artifact Registry
   BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD | tr '/' '-')
   IMAGE_URI="asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api:${BRANCH_NAME}"
   
   gcloud run deploy ticket-urgency-api \
     --image ${IMAGE_URI} \
     --platform managed \
     --region asia-south1 \
     --allow-unauthenticated \
     --memory 1Gi \
     --cpu 1 \
     --timeout 300 \
     --max-instances 10 \
     --set-env-vars GCS_BUCKET_NAME=ml-model-bucket-22 \
     --set-env-vars MODEL_GCS_PATH=ticket_urgency_model/ticket_urgency_model.pkl
   
   # Or use the deployment script
   ./scripts/deploy_to_cloudrun.sh
   ```

4. **Test deployed API**:
   ```bash
   # Get service URL
   SERVICE_URL=$(gcloud run services describe ticket-urgency-api \
     --region=asia-south1 --format='value(status.url)')
   
   # Test health
   curl $SERVICE_URL/health
   
   # Test prediction
   curl -X POST $SERVICE_URL/predict \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Server down",
       "description": "Production server not responding",
       "source": "email",
       "customer_tier": "premium"
     }'
   ```

**Deliverable**: Working REST API endpoint serving predictions

---

### Phase 2: CI/CD Pipeline (Week 1-2)

**Goal**: Automate deployment when code changes

**Tasks**:
1. **Set up GitHub Secrets**:
   - Go to your GitHub repository
   - Navigate to: **Settings** → **Secrets and variables** → **Actions**
   - Click **"New repository secret"**
   - Name: `GCP_SA_KEY`
   - Value: Copy the entire contents of your `service-acc-key.json` file
   - Click **"Add secret"**
   
   **Important**: Never commit `service-acc-key.json` to git (it's already in `.gitignore`)

2. **Test GitHub Actions workflow**:
   - Make changes to `api/` folder or `.github/workflows/deploy.yml`
   - Commit and push to `main` branch:
     ```bash
     git add .
     git commit -m "Update API for deployment"
     git push origin main
     ```
   - Go to GitHub → **Actions** tab
   - Watch the workflow run and check deployment status
   - The workflow will:
     - Build Docker image tagged with branch name (e.g., `main`)
     - Push to Artifact Registry: `asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api:main`
     - Deploy to Cloud Run automatically

3. **Image Versioning**:
   - Images are tagged with: branch name, `latest`, and git SHA
   - Each push creates a new image version in Artifact Registry
   - Cloud Run deploys using branch name tag

**Deliverable**: Automated deployment on git push

---

### Phase 3: Model Monitoring (Week 2)

**Goal**: Track model performance and detect drift

**Tasks**:
1. **Add monitoring DAG to Airflow**:
   ```python
   # dags/monitor_model.py
   monitor_task = PythonOperator(
       task_id='monitor_model',
       python_callable=run_monitoring,
       schedule_interval='@daily'
   )
   ```

2. **Set up Cloud Monitoring**:
   - Create custom metrics for prediction latency
   - Set up alerts for API errors
   - Track prediction distribution

3. **Implement drift detection**:
   - Use Evidently AI or custom statistical tests
   - Compare production data vs training data

**Deliverable**: Daily monitoring reports and alerts

---

### Phase 4: Model Versioning & A/B Testing (Week 3)

**Goal**: Safely deploy new model versions

**Tasks**:
1. **Integrate MLflow Model Registry**:
   - Register models after training
   - Promote models through stages (Staging → Production)

2. **Update API to use MLflow Model Registry**:
   - Load model by stage (e.g., "Production")
   - Support model versioning

3. **Add A/B testing**:
   - Route traffic between model versions
   - Compare metrics

**Deliverable**: Model registry with staged deployments

---

### Phase 5: Advanced Features (Week 4+)

**Goal**: Production-grade features

**Tasks**:
1. **Add authentication**:
   - Use Cloud Run authentication
   - API keys for external services

2. **Add request logging**:
   - Log all predictions to BigQuery
   - Track feature distributions

3. **Add batch prediction**:
   - Cloud Run job for batch processing
   - Or use Dataflow/Spark

4. **Performance optimization**:
   - Model caching
   - Request batching
   - Auto-scaling configuration

---

## 📋 JD Requirements Checklist

| Requirement | Status | Implementation |
|------------|--------|----------------|
| **Python scripting** | ✅ | All scripts in Python |
| **MLflow** | ✅ | Experiment tracking active |
| **Airflow** | ✅ | Training DAG working |
| **GCP & Python SDKs** | ✅ | Using GCS, Cloud Run |
| **REST API (Flask/FastAPI)** | 🚧 | FastAPI created, needs deployment |
| **CI/CD** | 🚧 | GitHub Actions workflow ready |
| **Model deployment** | 🚧 | Cloud Run deployment script ready |
| **Monitoring** | 🚧 | Monitoring script created |
| **Data drift detection** | 🚧 | Basic implementation in monitor script |
| **Version control (Git)** | ✅ | Using git |
| **ETL processes** | ✅ | Data preprocessing in train.py |
| **Production troubleshooting** | 🚧 | Logging and monitoring needed |

---

## 🛠️ Quick Start Commands

### Local Development & Testing

#### 1. Test Training Pipeline Locally
```bash
# Start all services (Airflow, MLflow, PostgreSQL)
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f airflow-scheduler

# Run training manually
docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"

# Access Airflow UI: http://localhost:8085 (admin/admin)
# Access MLflow UI: http://localhost:5000
```

#### 2. Test FastAPI Service Locally
```bash
# Install dependencies
cd api
pip install -r requirements.txt

# Set GCP credentials (if testing GCS model download)
export GOOGLE_APPLICATION_CREDENTIALS=../service-acc-key.json

# Run FastAPI server
uvicorn app:app --reload --port 8000

# Test endpoints (in another terminal)
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Server down",
    "description": "Production server not responding",
    "source": "email",
    "customer_tier": "premium"
  }'
```

#### 3. Test Monitoring Script Locally
```bash
# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS=service-acc-key.json
export GCS_BUCKET_NAME=ml-model-bucket-22
export API_URL=http://localhost:8000  # If testing against local API

# Run monitoring
python scripts/monitor_model.py
```

### Deployment

#### Manual Deployment (Using Script)
```bash
# Make script executable (Linux/Mac)
chmod +x scripts/deploy_to_cloudrun.sh

# Run deployment script
./scripts/deploy_to_cloudrun.sh

# Or on Windows (PowerShell)
bash scripts/deploy_to_cloudrun.sh
```

#### Automated Deployment (GitHub Actions)
```bash
# After setting up GitHub Secrets, just push to main
git add .
git commit -m "Update API"
git push origin main

# Check deployment status in GitHub Actions tab
```

### Monitoring
```bash
# Run monitoring script
python scripts/monitor_model.py

# Or add to Airflow DAG
```

---

## 📚 Learning Resources

1. **FastAPI**: https://fastapi.tiangolo.com/
2. **Cloud Run**: https://cloud.google.com/run/docs
3. **MLflow Model Registry**: https://mlflow.org/docs/latest/model-registry.html
4. **Evidently AI** (drift detection): https://www.evidentlyai.com/
5. **GitHub Actions**: https://docs.github.com/en/actions

---

## 🎓 Interview Talking Points

When discussing this project:

1. **End-to-end pipeline**: "I built a complete MLOps pipeline from training to deployment"
2. **Automation**: "Training runs daily via Airflow, models are automatically uploaded to GCS"
3. **Production deployment**: "Deployed model as REST API on Cloud Run with CI/CD"
4. **Monitoring**: "Implemented monitoring for model performance and data drift"
5. **Best practices**: "Used MLflow for experiment tracking, Docker for containerization, GCS for model storage"

---

## 🔄 Next Immediate Actions

1. **Today**: Test FastAPI service locally
2. **This week**: Deploy to Cloud Run and test
3. **Next week**: Set up CI/CD pipeline
4. **Following week**: Add monitoring and drift detection

Good luck! 🚀

