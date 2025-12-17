# Debugging Cloud Run Internal Server Error

## 🔴 Issue: Internal Server Error on `/health` endpoint

Your API is deployed but returning 500 errors. Let's debug this step by step.

---

## Step 1: Check Cloud Run Logs

The logs will tell us exactly what's wrong:

```bash
# View recent logs
gcloud run services logs read ticket-urgency-api \
  --region=asia-south1 \
  --limit=50

# Follow logs in real-time
gcloud run services logs tail ticket-urgency-api \
  --region=asia-south1
```

**Common errors you might see:**
- `Model file not found in GCS`
- `Permission denied accessing GCS bucket`
- `Failed to download model`
- `Model loading failed`

---

## Step 2: Verify Model Exists in GCS

The API tries to download the model from GCS on startup. Check if it exists:

```bash
# List files in the bucket
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/

# Check if model file exists
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl

# If file doesn't exist, you need to train the model first
```

---

## Step 3: Verify Service Account Permissions

The Cloud Run service needs permission to read from GCS:

```bash
# Check if service account can access GCS
gsutil ls gs://ml-model-bucket-22/ \
  --impersonate-service-account=airflow-sa@ml-model-480910.iam.gserviceaccount.com
```

**If this fails**, grant Storage Object Viewer role:

```bash
gcloud projects add-iam-policy-binding ml-model-480910 \
  --member="serviceAccount:airflow-sa@ml-model-480910.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

---

## Step 4: Check Environment Variables

Verify the environment variables are set correctly in Cloud Run:

```bash
# Check current configuration
gcloud run services describe ticket-urgency-api \
  --region=asia-south1 \
  --format="yaml(spec.template.spec.containers[0].env)"
```

You should see:
- `GCS_BUCKET_NAME=ml-model-bucket-22`
- `MODEL_GCS_PATH=ticket_urgency_model/ticket_urgency_model.pkl`

---

## Step 5: Test Model Download Locally

Test if the model can be downloaded with your service account:

```bash
# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=service-acc-key.json

# Try downloading the model
python -c "
from google.cloud import storage
import os

bucket_name = 'ml-model-bucket-22'
model_path = 'ticket_urgency_model/ticket_urgency_model.pkl'

client = storage.Client()
bucket = client.bucket(bucket_name)
blob = bucket.blob(model_path)

if blob.exists():
    print('✅ Model file exists')
    print(f'Size: {blob.size} bytes')
else:
    print('❌ Model file NOT found')
    print(f'Expected: gs://{bucket_name}/{model_path}')
"
```

---

## Step 6: Common Fixes

### Fix 1: Model Doesn't Exist - Train the Model First

If the model file doesn't exist in GCS, you need to train it first:

```bash
# Start Docker Compose
docker compose up -d

# Run training
docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"

# Verify model was uploaded
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl
```

### Fix 2: Add Storage Object Viewer Role

If the service account can't read from GCS:

```bash
gcloud projects add-iam-policy-binding ml-model-480910 \
  --member="serviceAccount:airflow-sa@ml-model-480910.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

### Fix 3: Update Cloud Run Service Account

Make sure Cloud Run is using the correct service account:

```bash
gcloud run services update ticket-urgency-api \
  --region=asia-south1 \
  --service-account=airflow-sa@ml-model-480910.iam.gserviceaccount.com
```

---

## Step 7: Test Health Endpoint After Fixes

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe ticket-urgency-api \
  --region=asia-south1 \
  --format='value(status.url)')

# Test health endpoint
curl ${SERVICE_URL}/health

# Expected response:
# {
#   "status": "healthy",
#   "model_loaded": true,
#   "bucket": "ml-model-bucket-22",
#   "model_path": "ticket_urgency_model/ticket_urgency_model.pkl"
# }
```

---

## Quick Diagnostic Script

Run this to check everything at once:

```bash
#!/bin/bash
echo "🔍 Checking Cloud Run Service..."

# 1. Check service status
echo "1. Service Status:"
gcloud run services describe ticket-urgency-api \
  --region=asia-south1 \
  --format="value(status.conditions[0].status)"

# 2. Check environment variables
echo "2. Environment Variables:"
gcloud run services describe ticket-urgency-api \
  --region=asia-south1 \
  --format="value(spec.template.spec.containers[0].env)"

# 3. Check if model exists
echo "3. Model File in GCS:"
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl 2>&1

# 4. Check recent logs
echo "4. Recent Logs (last 10 lines):"
gcloud run services logs read ticket-urgency-api \
  --region=asia-south1 \
  --limit=10

# 5. Test endpoint
echo "5. Testing /health endpoint:"
SERVICE_URL=$(gcloud run services describe ticket-urgency-api \
  --region=asia-south1 \
  --format='value(status.url)')
curl -s ${SERVICE_URL}/health | python -m json.tool
```

---

## Most Likely Causes

1. **Model file doesn't exist** (90% of cases)
   - Solution: Train the model first

2. **Service account lacks GCS read permission**
   - Solution: Add `roles/storage.objectViewer`

3. **Wrong bucket name or path**
   - Solution: Verify environment variables

4. **Service account not set on Cloud Run**
   - Solution: Update Cloud Run service account

---

## Next Steps

1. **Check logs first** - This will tell you exactly what's wrong
2. **Verify model exists** - Most common issue
3. **Check permissions** - Service account needs GCS access
4. **Re-deploy if needed** - After fixing issues

Let me know what the logs show and I'll help you fix it!
