# MLOps Ticket Urgency Model - Complete Setup Guide

End-to-end MLOps pipeline for training and deploying a ticket urgency classification model with automated CI/CD, monitoring, and data drift detection.

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [GCP Setup](#gcp-setup)
5. [Local Development Setup](#local-development-setup)
6. [Running Airflow & MLflow](#running-airflow--mlflow)
7. [Running DAGs](#running-dags)
8. [GitHub Actions CI/CD Setup](#github-actions-cicd-setup)
9. [Testing the Workflow](#testing-the-workflow)
10. [Troubleshooting](#troubleshooting)

---

## 📁 Project Structure

```
.
├── dags/                         # Airflow DAG definitions
│   ├── train_model.py            # Training DAG (PythonOperator + BashOperator examples)
│   └── monitor_model.py          # Monitoring DAG (data drift detection)
│
├── scripts/                      # Training / deployment / monitoring scripts
│   ├── train.py                  # Main training script (loads from GCS, trains, uploads model)
│   ├── monitor_model.py          # Monitoring script (API health, drift detection)
│   ├── upload_data_to_gcs.py     # Data upload utility (reference + new + combined)
│   ├── evaluate_on_new_data.py   # Model evaluation on new production data
│   ├── preprocess.py             # (Reserved for additional preprocessing)
│   └── deploy_to_cloudrun.sh     # Manual deployment script (alternative to CI/CD)
│
├── models/                       # Local model storage (created after training)
│   └── ticket_urgency_model.pkl  # Trained model file (saved locally, also uploaded to GCS)
│
├── logs/                         # Airflow task execution logs
│   └── dag_id=*/task_id=*/       # Logs organized by DAG and task
│
├── mlflow/                       # MLflow backend storage
│   └── mlflow.db                 # SQLite database for MLflow tracking
│
├── mlruns/                       # MLflow experiment runs
│   └── 1/                        # Experiment runs organized by experiment ID
│
├── api/                          # Model serving API (deployed to Cloud Run)
│   ├── app.py                    # FastAPI application (predict, health, reload-model endpoints)
│   ├── Dockerfile                # API container image definition
│   └── requirements.txt          # API dependencies (FastAPI, scikit-learn, etc.)
│
├── data/                         # Local data files
│   └── raw/
│       ├── tickets.csv           # Training/reference data (500 rows)
│       └── new_tickets.csv      # New production data (for drift testing)
│
├── docs/                         # Documentation files (all .md guides)
│   └── ...                       # Detailed guides (see docs/ folder for full list)
│
├── .github/
│   └── workflows/
│       └── deploy.yml            # CI/CD workflow (builds & deploys API to Cloud Run)
│
├── docker-compose.yaml           # Local development stack (Airflow + PostgreSQL + MLflow)
├── Dockerfile                    # Airflow image definition (installs Python packages)
├── fernet.py                     # Fernet key helper (for Airflow encryption)
├── service-acc-key.json          # GCP service account key (NOT in git - .gitignore)
└── README.md                     # This file - complete setup guide
```

### Key Directories Explained

- **`dags/`**: Airflow workflow definitions. Each `.py` file becomes a DAG in Airflow UI.
- **`scripts/`**: Python scripts executed by DAGs. Contains training, monitoring, and utility scripts.
- **`api/`**: FastAPI service code. Deployed to Cloud Run via GitHub Actions.
- **`data/`**: Local training data. Can be uploaded to GCS using `upload_data_to_gcs.py`.
- **`docs/`**: All documentation files organized in one place.
- **`.github/workflows/`**: GitHub Actions CI/CD pipeline definition.

---

## 🎯 Project Overview

This project implements a complete MLOps pipeline that:

- **Trains** a ticket urgency classification model using Airflow DAGs
- **Tracks** experiments and metrics using MLflow
- **Stores** models in Google Cloud Storage (GCS)
- **Serves** predictions via FastAPI on Cloud Run
- **Monitors** model health and detects data drift
- **Deploys** automatically via GitHub Actions CI/CD

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Local Development                         │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │   Airflow    │  │    MLflow    │                        │
│  │  (Port 8085) │  │  (Port 5000) │                        │
│  └──────┬───────┘  └──────┬───────┘                        │
│         │                  │                                 │
│         └──────────────────┴──────────────────┐            │
└─────────────────────────────────────────────────┼────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Google Cloud Platform (GCP)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Cloud Run   │  │      GCS     │  │   Artifact   │     │
│  │  (API Serve) │  │ (Model Store)│  │   Registry   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions (CI/CD)                          │
│  Auto-deploy on push to main branch                          │
│  Build → Push to Artifact Registry → Deploy Cloud Run        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Prerequisites

Before starting, ensure you have:

- **Docker** and **Docker Compose** installed
- **Google Cloud Platform (GCP)** account
- **GitHub** account
- **Git** installed
- **Python 3.11+** (for local testing, optional)

---

## ☁️ GCP Setup

### Step 1: Create GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: `ml-model-480910` (or your preferred name)
4. Note your **Project ID** (you'll need this later)

### Step 2: Enable Required APIs

Enable these APIs in your GCP project:

```bash
# Install gcloud CLI if not installed
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set your project
gcloud config set project ml-model-480910

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable storage.googleapis.com
```

### Step 3: Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **"Create Service Account"**
3. Name: `airflow-sa`
4. Click **"Create and Continue"**
5. Add these roles:
   - **Artifact Registry Writer**
   - **Cloud Run Admin**
   - **Storage Admin**
   - **Service Account User** (important for Cloud Run deployment)
6. Click **"Done"**

### Step 4: Create Service Account Key

1. Click on the service account you just created (`airflow-sa`)
2. Go to **"Keys"** tab
3. Click **"Add Key"** → **"Create new key"**
4. Select **JSON** format
5. Click **"Create"**
6. **Save the downloaded file** as `service-acc-key.json` in your project root directory

**⚠️ Important**: Never commit this file to git! It's already in `.gitignore`.

### Step 5: Create GCS Bucket

```bash
# Create bucket for storing models and data
gsutil mb -p ml-model-480910 -l asia-south1 gs://ml-model-bucket-22

# Verify bucket created
gsutil ls gs://ml-model-bucket-22
```

### Step 6: Create Artifact Registry Repository

```bash
# Create Docker repository for storing container images
gcloud artifacts repositories create ticket-urgency-repo \
  --repository-format=docker \
  --location=asia-south1 \
  --description="Docker repository for ticket urgency API"

# Verify repository created
gcloud artifacts repositories list --location=asia-south1
```

---

## 💻 Local Development Setup

### Step 1: Clone Repository

   ```bash
   git clone https://github.com/meghanakolhal/mlops.git
cd mlops/airflow
```

### Step 2: Place Service Account Key

Copy your `service-acc-key.json` file to the project root:

```bash
# Windows PowerShell
Copy-Item C:\path\to\service-acc-key.json .\service-acc-key.json

# Linux/Mac
cp /path/to/service-acc-key.json ./service-acc-key.json
```

**Verify**: The file should be at `c:\prepare\mlops-ticket-urgency\airflow\service-acc-key.json`

### Step 3: Verify Docker Setup

```bash
# Check Docker is running
docker --version
docker compose --version

# Test Docker Compose
docker compose config
```

---

## 🚀 Running Airflow & MLflow

### Step 1: Start Services

   ```bash
# Start all services (postgres, airflow, mlflow)
   docker compose up -d --build

# Check services are running
docker compose ps
```

You should see:
- `airflow-postgres` - Database
- `airflow-init` - Initialization (runs once, then exits)
- `airflow-webserver` - Web UI
- `airflow-scheduler` - Task scheduler
- `mlflow` - MLflow tracking server

### Step 2: Wait for Initialization

Wait 1-2 minutes for services to initialize. Check logs:

```bash
# Check initialization logs
docker compose logs airflow-init

# Check webserver logs
docker compose logs airflow-webserver

# Check scheduler logs
docker compose logs airflow-scheduler
```

### Step 3: Access Airflow UI

1. Open browser: **http://localhost:8085**
2. Login credentials:
   - **Username**: `admin`
   - **Password**: `admin`

### Step 4: Access MLflow UI

1. Open browser: **http://localhost:5000**
2. No login required (local development)

### Step 5: Verify Services

**Check Airflow:**
- Go to http://localhost:8085
- You should see DAGs: `ticket_urgency_model_training` and `ticket_urgency_model_monitoring`

**Check MLflow:**
- Go to http://localhost:5000
- You should see experiment: `ticket_urgency_experiment`

---

## 📊 Running DAGs

### Option 1: Via Airflow UI (Recommended)

1. **Open Airflow UI**: http://localhost:8085
2. **Find your DAG**: `ticket_urgency_model_training`
3. **Toggle ON** the DAG (switch on the left)
4. **Click "Trigger DAG"** button (play icon)
5. **Click on the DAG name** to see task details
6. **Click on a task** → **"Log"** button to view logs

### Option 2: Manual Execution (Testing)

```bash
# Run training script directly
docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"

# Run monitoring script directly
docker compose exec airflow-scheduler bash -lc "python /opt/airflow/scripts/monitor_model.py"
```

### Viewing Logs

**In Airflow UI:**
1. Click on DAG → Click on task → Click **"Log"** button
2. Logs show in real-time

**Via Command Line:**
```bash
# View scheduler logs
docker compose logs -f airflow-scheduler

# View specific task logs (after DAG run)
# Logs are saved to: ./logs/dag_id=<dag_name>/task_id=<task_name>/
```

### Understanding Task Status

- **Success** (green) ✅ - Task completed successfully
- **Failed** (red) ❌ - Task encountered an error (check logs)
- **Running** (yellow) ⏳ - Task is currently executing
- **Queued** (gray) ⏸️ - Task waiting to run

---

## 🔄 GitHub Actions CI/CD Setup

### Step 1: Add GitHub Secret

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. **Name**: `GCP_SA_KEY` (exactly as shown, case-sensitive)
5. **Secret**: Open your `service-acc-key.json` file and copy the **entire JSON content**
   ```json
   {
     "type": "service_account",
     "project_id": "ml-model-480910",
     "private_key_id": "...",
     "private_key": "...",
     ...
   }
   ```
6. Paste entire JSON into Secret field
7. Click **"Add secret"**

**Verify**: You should see `GCP_SA_KEY` listed (value will be masked as `••••••••`)

### Step 2: Verify Workflow File

The workflow file is at `.github/workflows/deploy.yml`. It should:

- Trigger on push to `main` branch
- Build Docker image
- Push to Artifact Registry
- Deploy to Cloud Run

### Step 3: Push to Main Branch

```bash
# Check current branch
git branch

# If not on main, switch to main
git checkout main

# Stage changes
git add .

# Commit
git commit -m "Setup CI/CD pipeline"

# Push to trigger workflow
git push origin main
```

### Step 4: Monitor GitHub Actions

1. Go to GitHub repository → **Actions** tab
2. Find workflow: **"Deploy Model API to Cloud Run"**
3. Click on the workflow run to see detailed logs
4. Wait for completion (usually 3-5 minutes)

**Workflow Steps:**
- ✅ Checkout code
- ✅ Authenticate to Google Cloud
- ✅ Build Docker image
- ✅ Push to Artifact Registry
- ✅ Deploy to Cloud Run
- ✅ Get service URL

### Step 5: Verify Deployment

```bash
# Get service URL
gcloud run services describe ticket-urgency-api \
  --region=asia-south1 \
  --format='value(status.url)'

# Test health endpoint
curl https://<your-service-url>/health

# Test prediction endpoint
curl -X POST https://<your-service-url>/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Server down",
    "description": "Production server not responding",
    "source": "email",
    "customer_tier": "premium"
  }'
```

### Manual Workflow Trigger

You can manually trigger the workflow:

1. Go to **Actions** tab
2. Click **"Deploy Model API to Cloud Run"**
3. Click **"Run workflow"** button (top right)
4. Select branch and click **"Run workflow"**

---

## 🧪 Testing the Workflow

### 1. Test Training Pipeline

```bash
# Start services
docker compose up -d

# Trigger training DAG via UI or run manually:
docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"

# Verify model uploaded to GCS
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/
```

### 2. Test API Locally

```bash
cd api

# Install dependencies
pip install -r requirements.txt

# Set credentials (Windows PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="..\service-acc-key.json"

# Set credentials (Linux/Mac)
export GOOGLE_APPLICATION_CREDENTIALS=../service-acc-key.json

# Run FastAPI server
uvicorn app:app --reload --port 8000

# Test in another terminal
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "description": "Test", "source": "web", "customer_tier": "Gold"}'
```

### 3. Test Monitoring DAG

1. Upload data to GCS:
   ```bash
   python scripts/upload_data_to_gcs.py
   ```

2. Trigger monitoring DAG in Airflow UI

3. Check logs for drift detection results

### 4. Test Model Reload

After retraining, reload model without redeploying:

```bash
# Windows
curl.exe -X POST https://<your-service-url>/reload-model -H "Content-Length: 0"

# Linux/Mac
curl -X POST https://<your-service-url>/reload-model -H "Content-Length: 0"
```

---


## 🔧 Troubleshooting

### Issue: Airflow UI not accessible

**Solution:**
```bash
# Check if containers are running
docker compose ps

# Check webserver logs
docker compose logs airflow-webserver

# Restart services
docker compose restart airflow-webserver
```

### Issue: DAG not appearing in Airflow UI

**Solution:**
```bash
# Check DAG file syntax
python -c "from airflow import DAG; import sys; sys.path.insert(0, 'dags'); exec(open('dags/train_model.py').read())"

# Check scheduler logs for errors
docker compose logs airflow-scheduler | grep ERROR

# Restart scheduler
docker compose restart airflow-scheduler
```

### Issue: Model not loading from GCS

**Solution:**
- Verify `service-acc-key.json` exists in project root
- Check service account has **Storage Admin** role
- Verify model exists: `gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/`
- Check Cloud Run logs for detailed errors

### Issue: GitHub Actions fails

**Common causes:**
1. **Secret not set**: Verify `GCP_SA_KEY` exists in GitHub Secrets
2. **Permission denied**: Ensure service account has all required roles
3. **Image not found**: Check Artifact Registry repository exists

**Debug:**
```bash
# Check workflow logs in GitHub Actions tab
# Verify service account permissions in GCP Console
# Test locally first before pushing
```

### Issue: Cloud Run deployment fails

**Solution:**
```bash
# Check Cloud Run logs
gcloud run services logs read ticket-urgency-api \
  --region=asia-south1 \
  --limit=50

# Verify image exists in Artifact Registry
gcloud artifacts docker images list \
  asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api
```

### Issue: MLflow not tracking experiments

**Solution:**
- Verify MLflow container is running: `docker compose ps mlflow`
- Check MLflow logs: `docker compose logs mlflow`
- Verify MLFLOW_TRACKING_URI is set: `http://mlflow:5000/`

---

## 📚 Additional Documentation

For detailed guides, see the `docs/` folder:

- **`docs/DEPLOYMENT_ROADMAP.md`** - Complete deployment roadmap
- **`docs/GITHUB_SETUP_GUIDE.md`** - Detailed GitHub Actions setup
- **`docs/PRODUCTION_WORKFLOW.md`** - Production workflow guide
- **`docs/COMPLETE_WORKFLOW_SUMMARY.md`** - Workflow summary

---

## ✅ Quick Checklist

Before running the workflow, ensure:

- [ ] Docker and Docker Compose installed
- [ ] GCP project created
- [ ] Service account created with required roles
- [ ] Service account key (`service-acc-key.json`) in project root
- [ ] GCS bucket created
- [ ] Artifact Registry repository created
- [ ] GitHub Secret `GCP_SA_KEY` added
- [ ] Docker services running (`docker compose up -d`)
- [ ] Airflow UI accessible (http://localhost:8085)
- [ ] MLflow UI accessible (http://localhost:5000)

---

## 🎓 Key Concepts

### Airflow DAGs
- **DAG**: Directed Acyclic Graph - defines workflow
- **Task**: Individual unit of work
- **PythonOperator**: Runs Python functions
- **BashOperator**: Runs shell commands
- **Dependencies**: Define task execution order

### MLflow
- **Experiment**: Container for related runs
- **Run**: Single training execution
- **Metrics**: Performance measurements (accuracy, F1, etc.)
- **Parameters**: Hyperparameters used for training

### GCP Services
- **Cloud Storage (GCS)**: Stores models and data
- **Cloud Run**: Serverless container platform for API
- **Artifact Registry**: Stores Docker images
- **Service Account**: Authentication for GCP services

---

## 👤 Author

**Meghana Kolhal**
- GitHub: [@meghanakolhal](https://github.com/meghanakolhal)

---

## 📄 License

This project is part of an MLOps portfolio demonstration.

---

## 🔗 Useful Commands Reference

```bash
# Docker Compose
docker compose up -d              # Start services
docker compose down               # Stop services
docker compose logs -f <service>  # View logs
docker compose restart <service>  # Restart service

# Airflow
docker compose exec airflow-scheduler bash  # Access scheduler container
docker compose exec airflow-webserver bash  # Access webserver container

# GCP
gcloud auth login                 # Authenticate
gcloud config set project <ID>   # Set project
gsutil ls gs://<bucket>          # List bucket contents
gcloud run services list          # List Cloud Run services

# Git
git status                        # Check changes
git add .                         # Stage changes
git commit -m "message"           # Commit
git push origin main              # Push to main
```

---

**Need help?** Check the `docs/` folder for detailed guides on specific topics.
