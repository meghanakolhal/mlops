# Fix: Model Not Loading in Cloud Run API

## 🔴 Issue

From monitoring logs:
```
✅ API is healthy
   Model loaded: False  ← Problem!
❌ Prediction test failed: {'error': 'Status 500'}
```

## 🔍 Root Cause

The API's `/health` endpoint shows `model_loaded: False`, which means:
1. Model file might not exist in GCS at expected path, OR
2. API can't download model from GCS (permissions issue), OR
3. Model failed to load on startup (error during download/load)

## ✅ Solution Steps

### Step 1: Verify Model Exists in GCS

```bash
# Check if model file exists
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl

# If it doesn't exist, you need to train the model first
# Trigger training DAG in Airflow UI
```

### Step 2: Check Cloud Run Logs for Model Loading Errors

```bash
# View recent Cloud Run logs
gcloud run services logs read ticket-urgency-api \
  --region=asia-south1 \
  --limit=50

# Look for errors like:
# - "Model file not found"
# - "Permission denied"
# - "Failed to download model"
```

### Step 3: Verify Service Account Permissions

The Cloud Run service needs permission to read from GCS:

```bash
# Check if service account has Storage Object Viewer role
gcloud projects get-iam-policy ml-model-480910 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:airflow-sa@ml-model-480910.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

If missing, add it:
```bash
gcloud projects add-iam-policy-binding ml-model-480910 \
  --member="serviceAccount:airflow-sa@ml-model-480910.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

### Step 4: Redeploy API After Fixing Permissions

After adding permissions, redeploy:
- Push changes to main branch (triggers GitHub Actions), OR
- Manually redeploy: `./scripts/deploy_to_cloudrun.sh`

### Step 5: Test Again

```bash
# Test health endpoint
curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/health

# Should show:
# {
#   "status": "healthy",
#   "model_loaded": true,  ← Should be true now!
#   ...
# }
```

---

## 📋 Quick Checklist

- [ ] Model file exists in GCS: `gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl`
- [ ] Service account has `roles/storage.objectViewer` permission
- [ ] Cloud Run service account is set correctly
- [ ] Check Cloud Run logs for specific errors
- [ ] Redeploy API after fixing issues

---

## 🔧 Common Fixes

### Fix 1: Model File Doesn't Exist
**Solution:** Train the model first (trigger training DAG)

### Fix 2: Permission Denied
**Solution:** Add Storage Object Viewer role to service account

### Fix 3: Model Path Mismatch
**Solution:** Verify `MODEL_GCS_PATH` in `api/app.py` matches GCS path

---

**After fixing, run monitoring DAG again!** ✅
