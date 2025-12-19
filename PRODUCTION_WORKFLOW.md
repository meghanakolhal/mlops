# Production Data Drift & Retraining Workflow

## 🎯 How Data Drift Works in Production

### Data Structure in GCS

```
gs://ml-model-bucket-22/
├── datasets/
│   ├── tickets.csv              # Reference data (FROZEN snapshot from training)
│   ├── new_tickets.csv          # New production data (accumulates over time)
│   └── combined_tickets.csv    # Reference + New (for retraining)
├── ticket_urgency_model/
│   └── ticket_urgency_model.pkl # Trained model
└── monitoring/
    └── report_YYYYMMDD_HHMMSS.json  # Monitoring reports
```

### Key Concepts

1. **Reference Data (`tickets.csv`)**: 
   - **Frozen snapshot** of data used for initial training
   - **Never changes** - this is your baseline
   - Used to compare against new data for drift detection

2. **New Production Data (`new_tickets.csv`)**:
   - **Accumulates** over time as new tickets come in
   - Can be appended daily/weekly/monthly
   - Used to detect if data distribution changed

3. **Combined Data (`combined_tickets.csv`)**:
   - Reference + New data combined
   - Used for **retraining** the model
   - Ensures model learns from both old and new patterns

---

## 🔄 Complete Workflow

### Step 1: Initial Setup (One-Time)

```bash
# Upload reference data (frozen snapshot)
python scripts/upload_data_to_gcs.py
# This uploads:
# - datasets/tickets.csv (reference)
# - datasets/new_tickets.csv (new)
# - datasets/combined_tickets.csv (combined)
```

### Step 2: Train Initial Model

```bash
# Trigger training DAG
# Uses: datasets/tickets.csv (or combined_tickets.csv if available)
# Output: ticket_urgency_model/ticket_urgency_model.pkl
```

### Step 3: Deploy Model

```bash
# GitHub Actions auto-deploys to Cloud Run
# Or manually: ./scripts/deploy_to_cloudrun.sh
```

### Step 4: Collect New Production Data

**In Production:**
- New tickets arrive daily
- Append to `datasets/new_tickets.csv` in GCS
- Or create daily files: `datasets/production/20251217.csv`

**For Testing:**
```bash
# Upload new data
python scripts/upload_data_to_gcs.py
# This will:
# 1. Upload reference (if not exists)
# 2. Upload new data
# 3. Combine reference + new → combined_tickets.csv
```

### Step 5: Monitor for Drift

```bash
# Trigger monitoring DAG
# Compares:
# - Reference: datasets/tickets.csv
# - New: datasets/new_tickets.csv
# Result: Detects if distributions changed
```

### Step 6: Retrain Model (If Drift Detected)

```bash
# Trigger training DAG
# Now uses: datasets/combined_tickets.csv (reference + new)
# Output: New model uploaded to GCS
```

### Step 7: Reload Model in API

```bash
# Option A: Redeploy API (automatic via GitHub Actions)
git push origin main

# Option B: Use reload endpoint (if new model uploaded)
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model
```

### Step 8: Test New Model

```bash
# Test prediction
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"title": "Server down", "description": "Production server not responding", "source": "email", "customer_tier": "premium"}'
```

---

## 📋 Why This Structure?

### Why Keep Reference Data Separate?

- **Baseline comparison**: Always compare new data against original training data
- **Drift detection**: See how much data has changed since training
- **Reproducibility**: Can always retrain from same baseline

### Why Combine for Retraining?

- **Learn new patterns**: Model adapts to recent data patterns
- **Maintain old patterns**: Still remembers original training patterns
- **Better performance**: Model works well on both old and new data

### Why Cache Model in API?

- **Performance**: Loading from disk is faster than downloading from GCS every request
- **Cost**: Fewer GCS API calls
- **Reliability**: Works even if GCS is temporarily unavailable

### Why Need Reload Endpoint?

- **Update without redeploy**: Don't need to rebuild Docker image
- **Quick model refresh**: After retraining, just reload
- **Testing**: Easy to test new models

---

## 🚀 Quick Test Workflow

### 1. Upload Data (Combines Reference + New)

```bash
python scripts/upload_data_to_gcs.py
```

**Output:**
- ✅ Reference: `datasets/tickets.csv`
- ✅ New: `datasets/new_tickets.csv`
- ✅ Combined: `datasets/combined_tickets.csv`

### 2. Check Drift

```bash
# Trigger monitoring DAG
# Compares reference vs new → detects drift
```

### 3. Retrain (Uses Combined Data)

```bash
# Trigger training DAG
# Uses: datasets/combined_tickets.csv
# Output: New model in GCS
```

### 4. Reload Model in API

```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model
```

### 5. Test

```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"title": "Application running slow", "description": "Report export stuck", "source": "web", "customer_tier": "Gold"}'
```

---

## 🔍 Understanding the Flow

```
┌─────────────────┐
│ Reference Data  │ (datasets/tickets.csv)
│ (Frozen)        │ ← Never changes, baseline for comparison
└────────┬────────┘
         │
         │ Compare
         ▼
┌─────────────────┐
│ New Data        │ (datasets/new_tickets.csv)
│ (Accumulates)   │ ← Grows over time
└────────┬────────┘
         │
         │ Combine
         ▼
┌─────────────────┐
│ Combined Data   │ (datasets/combined_tickets.csv)
│ (For Retrain)   │ ← Reference + New
└────────┬────────┘
         │
         │ Train
         ▼
┌─────────────────┐
│ New Model       │ (ticket_urgency_model/ticket_urgency_model.pkl)
│ (In GCS)        │ ← Uploaded after training
└────────┬────────┘
         │
         │ Reload
         ▼
┌─────────────────┐
│ API Model      │ (In-memory cache)
│ (Serving)      │ ← Reloaded via /reload-model endpoint
└─────────────────┘
```

---

## ✅ Summary

1. **Reference data** = Frozen baseline (never changes)
2. **New data** = Accumulates over time
3. **Combined data** = Reference + New (for retraining)
4. **Monitoring** = Compares Reference vs New (detects drift)
5. **Retraining** = Uses Combined data (learns from both)
6. **Reload** = Updates API cache without redeploy

**This is the standard production workflow!** ✅
