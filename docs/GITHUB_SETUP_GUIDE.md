# GitHub Secrets Setup & Testing Guide

This guide walks you through setting up GitHub Secrets and testing the CI/CD workflow.

## 📋 Prerequisites

- GitHub repository created
- GCP project with Artifact Registry repository: `ticket-urgency-repo`
- Service account JSON key file: `service-acc-key.json`
- GCP project ID: `ml-model-480910`

---

## 🔐 Step 1: Add Service Account Key to GitHub Secrets

### Option A: Using GitHub Web UI (Recommended)

1. **Open your GitHub repository** in a web browser

2. **Navigate to Secrets**:
   - Click on **Settings** (top menu bar)
   - In the left sidebar, click **Secrets and variables** → **Actions**

3. **Add the Secret**:
   - Click **"New repository secret"** button
   - **Name**: `GCP_SA_KEY` (exactly as shown, case-sensitive)
   - **Secret**: Open your `service-acc-key.json` file and copy the **entire contents**
     ```json
     {
       "type": "service_account",
       "project_id": "ml-model-480910",
       "private_key_id": "...",
       "private_key": "...",
       ...
     }
     ```
   - Paste the entire JSON content into the Secret field
   - Click **"Add secret"**

4. **Verify**:
   - You should see `GCP_SA_KEY` listed in your secrets
   - The value will be masked (shown as `••••••••`)

### Option B: Using GitHub CLI (Alternative)

```bash
# Install GitHub CLI if not installed
# Windows: winget install GitHub.cli
# Mac: brew install gh
# Linux: See https://cli.github.com/

# Authenticate
gh auth login

# Add secret from file
gh secret set GCP_SA_KEY < service-acc-key.json
```

---

## 🧪 Step 2: Test Locally Before Pushing

### 2.1 Test Training Pipeline

```bash
# Start Docker Compose services
docker compose up -d

# Wait for services to initialize (check logs)
docker compose logs -f airflow-scheduler

# Run training script manually
docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"

# Verify model was uploaded to GCS
# Check: gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl
```

### 2.2 Test FastAPI Service Locally

```bash
# Navigate to api directory
cd api

# Install dependencies
pip install -r requirements.txt

# Set GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS=../service-acc-key.json
# Windows PowerShell:
# $env:GOOGLE_APPLICATION_CREDENTIALS="..\service-acc-key.json"

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

### 2.3 Test Docker Build Locally

```bash
# Authenticate to GCP
gcloud auth login
gcloud config set project ml-model-480910

# Configure Docker for Artifact Registry
gcloud auth configure-docker asia-south1-docker.pkg.dev

# Build Docker image
cd api
BRANCH_NAME="local-test"
IMAGE_URI="asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api"

docker build -t ${IMAGE_URI}:${BRANCH_NAME} .
docker tag ${IMAGE_URI}:${BRANCH_NAME} ${IMAGE_URI}:latest

# Test the image locally
docker run -p 8080:8080 \
  -e GCS_BUCKET_NAME=ml-model-bucket-22 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/key.json \
  -v $(pwd)/../service-acc-key.json:/tmp/key.json \
  ${IMAGE_URI}:${BRANCH_NAME}

# Test in another terminal
curl http://localhost:8080/health
```

---

## 🚀 Step 3: Push to Main Branch and Test Workflow

### 3.1 Prepare Your Changes

```bash
# Check current branch
git branch

# If not on main, switch to main
git checkout main

# Or create main branch if it doesn't exist
git checkout -b main

# Stage all changes
git add .

# Check what will be committed
git status

# Commit changes
git commit -m "Add CI/CD workflow with Artifact Registry and branch tagging"

# Verify you're ready to push
git log --oneline -5
```

### 3.2 Push to GitHub

```bash
# If this is your first push to main
git push -u origin main

# For subsequent pushes
git push origin main
```

### 3.3 Monitor GitHub Actions Workflow

1. **Go to GitHub Repository** → **Actions** tab
2. **Find the workflow run**:
   - Look for "Deploy Model API to Cloud Run" workflow
   - Status will be: ⏳ Running → ✅ Success or ❌ Failed
3. **Click on the workflow run** to see detailed logs:
   - Checkout code
   - Authenticate to Google Cloud
   - Build Docker image
   - Push to Artifact Registry
   - Deploy to Cloud Run
   - Get service URL

### 3.4 Verify Deployment

```bash
# Get the service URL from GitHub Actions output
# Or run:
gcloud run services describe ticket-urgency-api \
  --region=asia-south1 \
  --format='value(status.url)'

# Test the deployed API
SERVICE_URL="<URL_FROM_ABOVE>"
curl ${SERVICE_URL}/health

curl -X POST ${SERVICE_URL}/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Server down",
    "description": "Production server not responding",
    "source": "email",
    "customer_tier": "premium"
  }'
```

---

## 🔍 Troubleshooting

### Issue: GitHub Actions fails with "Authentication failed"

**Solution**:
- Verify `GCP_SA_KEY` secret is set correctly
- Check that the JSON content is complete (no truncation)
- Ensure service account has required permissions:
  - Artifact Registry Writer
  - Cloud Run Admin
  - Service Account User

### Issue: Docker push fails with "permission denied"

**Solution**:
```bash
# Verify Docker authentication
gcloud auth configure-docker asia-south1-docker.pkg.dev

# Check Artifact Registry repository exists
gcloud artifacts repositories describe ticket-urgency-repo \
  --location=asia-south1 \
  --repository-format=docker
```

### Issue: Cloud Run deployment fails

**Solution**:
- Check that the image exists in Artifact Registry
- Verify service account has Cloud Run Admin role
- Check Cloud Run logs:
  ```bash
  gcloud run services logs read ticket-urgency-api \
    --region=asia-south1 \
    --limit=50
  ```

### Issue: API returns 500 error

**Solution**:
- Check if model exists in GCS: `gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl`
- Verify GCS_BUCKET_NAME environment variable is set
- Check Cloud Run logs for detailed error messages

---

## ✅ Verification Checklist

- [ ] GitHub Secret `GCP_SA_KEY` is set
- [ ] Training pipeline runs successfully locally
- [ ] FastAPI service runs and responds locally
- [ ] Docker image builds successfully
- [ ] Changes committed and pushed to `main` branch
- [ ] GitHub Actions workflow completes successfully
- [ ] Image appears in Artifact Registry with branch tag
- [ ] Cloud Run service is deployed and accessible
- [ ] API health endpoint returns 200
- [ ] API prediction endpoint works correctly

---

## 📝 Next Steps

After successful deployment:

1. **Set up monitoring**: Integrate `monitor_model.py` into Airflow DAG
2. **Add more branches**: Create feature branches and test branch tagging
3. **Set up alerts**: Configure Cloud Monitoring alerts for API errors
4. **Add authentication**: Secure the API with Cloud Run authentication
5. **Scale up**: Adjust Cloud Run configuration based on traffic

---

## 🔗 Useful Commands Reference

```bash
# View GitHub Actions logs
gh run list
gh run view <run-id>

# Check Artifact Registry images
gcloud artifacts docker images list \
  asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api

# View Cloud Run service details
gcloud run services describe ticket-urgency-api --region=asia-south1

# View Cloud Run logs
gcloud run services logs read ticket-urgency-api --region=asia-south1 --limit=100

# Delete old images from Artifact Registry
gcloud artifacts docker images delete \
  asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api:TAG_NAME
```
