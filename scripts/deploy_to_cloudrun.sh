#!/bin/bash
# Deploy FastAPI model service to Cloud Run
# Usage: ./scripts/deploy_to_cloudrun.sh
# Alternative to GitHub Actions (manual deployment)

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"ml-model-480910"}
REGION=${GCP_REGION:-"asia-south1"}
SERVICE_NAME="ticket-urgency-api"
ARTIFACT_REGISTRY_REPO=${ARTIFACT_REGISTRY_REPO:-"ticket-urgency-repo"}
ARTIFACT_REGISTRY_LOCATION=${ARTIFACT_REGISTRY_LOCATION:-"asia-south1"}
BUCKET_NAME=${GCS_BUCKET_NAME:-"ml-model-bucket-22"}

# Get current branch name or use 'local' as default
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "local")
BRANCH_NAME=${BRANCH_NAME//\//-}  # Replace / with - for valid tag names

# Build image URI for Artifact Registry
IMAGE_URI="${ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${SERVICE_NAME}"

echo "🚀 Deploying to Cloud Run..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Branch: ${BRANCH_NAME}"
echo "Image: ${IMAGE_URI}:${BRANCH_NAME}"

# Build Docker image
echo "📦 Building Docker image..."
cd api
docker build -t ${IMAGE_URI}:${BRANCH_NAME} .
docker tag ${IMAGE_URI}:${BRANCH_NAME} ${IMAGE_URI}:latest

# Configure Docker for Artifact Registry
echo "🔐 Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev

# Push to Artifact Registry
echo "📤 Pushing image to Artifact Registry..."
docker push ${IMAGE_URI}:${BRANCH_NAME}
docker push ${IMAGE_URI}:latest

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_URI}:${BRANCH_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars GCS_BUCKET_NAME=${BUCKET_NAME} \
  --set-env-vars MODEL_GCS_PATH=ticket_urgency_model/ticket_urgency_model.pkl \
  --service-account=${SERVICE_ACCOUNT_EMAIL:-""}

echo "✅ Deployment complete!"
echo "Get service URL with: gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)'"

