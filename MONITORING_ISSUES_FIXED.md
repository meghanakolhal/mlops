# Monitoring Issues - Analysis & Fixes

## 🔍 Issues Found in Your Monitoring Logs

### Issue 1: API Shows `Model loaded: False`
**Problem:** API health check returns `model_loaded: False`  
**Cause:** Model might not be loading on API startup, or model file doesn't exist in GCS  
**Fix:** Check if model exists in GCS and verify API startup logs

### Issue 2: Prediction Test Fails (Status 500)
**Problem:** Prediction endpoint returns 500 error  
**Cause:** Model is not loaded (`model_loaded: False`)  
**Fix:** Once model loads correctly, prediction will work

### Issue 3: New Data Not Found
**Problem:** `gs://ml-model-bucket-22/datasets/new_tickets.csv` doesn't exist  
**Status:** ✅ **This is EXPECTED** - you haven't uploaded it yet!  
**Fix:** Upload new_tickets.csv to GCS (see Step 1 below)

---

## ✅ What's Working Correctly

1. ✅ **Reference data loads from GCS**: `datasets/tickets.csv` ✅
2. ✅ **Drift detection logic**: Works correctly (compares distributions)
3. ✅ **Monitoring report uploads**: Saves to GCS successfully
4. ✅ **API health check**: Connects successfully (just model not loaded)

---

## 📋 About "Commenting Out Code"

**IMPORTANT:** There is **NO automatic CSV upload code** to comment out!

The only uploads in your codebase are:
1. **Model upload** (`train.py`) → ✅ **Keep this** (uploads trained model)
2. **Monitoring report upload** (`monitor_model.py`) → ✅ **Keep this** (saves reports)

**CSV data uploads are MANUAL** - you run the script once:
```bash
python scripts/upload_data_to_gcs.py
```

This is **intentional** - you control when to upload data, not automatic.

---

## 🔧 Fixes Needed

### Fix 1: Upload New Data to GCS

```bash
# Upload new_tickets.csv to GCS
cd c:\prepare\mlops-ticket-urgency\airflow
python scripts/upload_data_to_gcs.py

# Or manually:
gsutil cp data/raw/new_tickets.csv gs://ml-model-bucket-22/datasets/new_tickets.csv
```

### Fix 2: Check Why API Model Not Loading

**Check Cloud Run logs:**
```bash
gcloud run services logs read ticket-urgency-api \
  --region=asia-south1 \
  --limit=50
```

**Check if model exists in GCS:**
```bash
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/
```

**Possible causes:**
- Model file doesn't exist in GCS
- API startup failed to download model
- GCS permissions issue

### Fix 3: Verify Model Was Uploaded After Training

After training DAG completes, verify:
```bash
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl
```

---

## 🚀 Complete Workflow (Step-by-Step)

### Step 1: Upload Data Files (One-Time)
```bash
python scripts/upload_data_to_gcs.py
```

This uploads:
- `tickets.csv` → `gs://ml-model-bucket-22/datasets/tickets.csv` ✅ (Already done)
- `new_tickets.csv` → `gs://ml-model-bucket-22/datasets/new_tickets.csv` ❌ (Need to do)

### Step 2: Train Model
- Airflow UI → Trigger `ticket_urgency_model_training`
- Should load from GCS: `datasets/tickets.csv` ✅
- Model uploaded to: `ticket_urgency_model/ticket_urgency_model.pkl` ✅

### Step 3: Verify Model in GCS
```bash
gsutil ls gs://ml-model-bucket-22/ticket_urgency_model/
```

### Step 4: Check API Model Loading
```bash
# Check Cloud Run logs for model loading errors
gcloud run services logs read ticket-urgency-api --region=asia-south1 --limit=50

# Test API health
curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/health
```

**Expected:** `"model_loaded": true`

### Step 5: Upload New Data (For Drift Testing)
```bash
gsutil cp data/raw/new_tickets.csv gs://ml-model-bucket-22/datasets/new_tickets.csv
```

### Step 6: Run Monitoring
- Airflow UI → Trigger `ticket_urgency_model_monitoring`
- Should now:
  - ✅ Load reference data from GCS
  - ✅ Load new data from GCS
  - ✅ Detect drift (different distributions)
  - ✅ Save report to GCS

---

## 📊 Expected Monitoring Output (After Fixes)

```
🔍 Model Monitoring - 2025-12-17 10:32:13
==================================================

1. Checking API health...
✅ API is healthy
   Model loaded: true  ← Should be TRUE

2. Testing prediction endpoint...
✅ Prediction successful
   Prediction: urgent
   Confidence: 0.85

3. Checking for data drift...
Loading reference data from: gs://ml-model-bucket-22/datasets/tickets.csv
✅ Loaded 500 rows from GCS
Loading new/production data from: gs://ml-model-bucket-22/datasets/new_tickets.csv
✅ Found new data with 20 rows
⚠️  Data drift detected!  ← Should detect drift now
{
  "source": {
    "drift_score": 0.45,
    ...
  }
}

📊 Monitoring report saved to: gs://ml-model-bucket-22/monitoring/report_...json
✅ Monitoring complete
```

---

## ✅ Action Items

1. **Upload new_tickets.csv to GCS** (if you want to test drift)
2. **Check why API model not loading** (check Cloud Run logs)
3. **Verify model exists in GCS** after training
4. **Re-run monitoring** after uploading new data

---

**The monitoring script logic is correct!** The issues are:
- New data file doesn't exist yet (expected)
- API model not loading (need to investigate)
