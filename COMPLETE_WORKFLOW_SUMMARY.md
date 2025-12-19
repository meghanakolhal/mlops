# Complete Workflow Summary - All Your Questions Answered

## 📋 Answers to Your Questions

### 1. **How Data Drift Works in Production**

**In Production:**
- **Reference Data** (`datasets/tickets.csv`): **Frozen snapshot** - never changes
  - This is your baseline for comparison
  - Used to detect if new data has drifted
  
- **New Production Data** (`datasets/new_tickets.csv`): **Accumulates over time**
  - New tickets arrive daily/weekly
  - Can append to same file OR create dated files
  - Used to compare against reference

**Comparison:**
- Monitoring compares **Reference** vs **New** → detects drift
- If drift detected → retrain model

---

### 2. **Why Combine and Retrain?**

**You're absolutely right!** We can combine in `upload_data_to_gcs.py`:

✅ **Enhanced `upload_data_to_gcs.py` now:**
1. Uploads reference data → `datasets/tickets.csv`
2. Uploads new data → `datasets/new_tickets.csv`
3. **Combines both** → `datasets/combined_tickets.csv` ← **For retraining!**

**Why combine?**
- Model learns from **both old and new patterns**
- Better performance on recent data
- Maintains knowledge from original training

---

### 3. **Cache Removal in API**

✅ **Added `/reload-model` endpoint** to API:

```bash
# After retraining, reload model without redeploying
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model
```

**What it does:**
- Clears in-memory model cache
- Removes cached file (`/tmp/model.pkl`)
- Downloads fresh model from GCS
- No need to redeploy!

---

## 🚀 Complete Workflow (Step-by-Step)

### Step 1: Upload Data (Combines Reference + New)

```bash
python scripts/upload_data_to_gcs.py
```

**What happens:**
1. ✅ Uploads `tickets.csv` → `datasets/tickets.csv` (reference)
2. ✅ Uploads `new_tickets.csv` → `datasets/new_tickets.csv` (new)
3. ✅ **Combines both** → `datasets/combined_tickets.csv` (for retraining)

**Output:**
```
Reference (frozen): gs://ml-model-bucket-22/datasets/tickets.csv
New production:     gs://ml-model-bucket-22/datasets/new_tickets.csv
Combined (retrain): gs://ml-model-bucket-22/datasets/combined_tickets.csv
```

---

### Step 2: Check Drift (Monitoring DAG)

**Airflow UI** → Trigger `ticket_urgency_model_monitoring` DAG

**What it does:**
- Compares `datasets/tickets.csv` (reference) vs `datasets/new_tickets.csv` (new)
- Detects if distributions changed
- Saves report to GCS

**Expected output:**
```
⚠️  Data drift detected!
{
  "source": {
    "drift_score": 0.45,
    ...
  }
}
```

---

### Step 3: Retrain Model (Uses Combined Data)

**Airflow UI** → Trigger `ticket_urgency_model_training` DAG

**What it does:**
- Loads `datasets/combined_tickets.csv` (reference + new)
- Trains new model
- Uploads to GCS: `ticket_urgency_model/ticket_urgency_model.pkl`

---

### Step 4: Reload Model in API (Clear Cache)

```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model
```

**Response:**
```json
{
  "status": "success",
  "message": "Model reloaded successfully from GCS",
  "model_loaded": true
}
```

---

### Step 5: Test New Model

```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Application running slow",
    "description": "Report export stuck at 80 percent for several minutes.",
    "source": "web",
    "customer_tier": "Gold"
  }'
```

---

## 📊 Data Structure Explained

```
GCS Bucket Structure:
├── datasets/
│   ├── tickets.csv              ← Reference (FROZEN - never changes)
│   ├── new_tickets.csv          ← New data (accumulates)
│   └── combined_tickets.csv     ← Reference + New (for retraining)
│
├── ticket_urgency_model/
│   └── ticket_urgency_model.pkl ← Trained model (updated after retraining)
│
└── monitoring/
    └── report_*.json            ← Drift detection reports
```

---

## 🔄 Why This Structure?

### Reference Data (Frozen)
- **Purpose**: Baseline for comparison
- **Never changes**: Always compare new data against original training data
- **Why**: See how much data has drifted since initial training

### New Data (Accumulates)
- **Purpose**: Recent production data
- **Grows over time**: New tickets added daily/weekly
- **Why**: Detect if current data patterns differ from training data

### Combined Data (For Retraining)
- **Purpose**: Training dataset for retraining
- **Contains**: Reference + New data
- **Why**: Model learns from both old and new patterns

---

## ✅ What I Changed

1. ✅ **Enhanced `upload_data_to_gcs.py`**:
   - Now combines reference + new data
   - Creates `combined_tickets.csv` automatically

2. ✅ **Updated `train.py`**:
   - Uses `combined_tickets.csv` for retraining (if available)
   - Falls back to reference data if combined doesn't exist

3. ✅ **Added `/reload-model` endpoint**:
   - Clears cache and reloads model from GCS
   - No need to redeploy after retraining

4. ✅ **Created `PRODUCTION_WORKFLOW.md`**:
   - Complete documentation of workflow

---

## 🎯 Your Workflow (Exactly What You Asked For)

```bash
# 1. Upload data (combines reference + new)
python scripts/upload_data_to_gcs.py

# 2. Run monitoring (checks drift)
# Airflow UI → ticket_urgency_model_monitoring DAG

# 3. Retrain model (uses combined data)
# Airflow UI → ticket_urgency_model_training DAG

# 4. Reload model in API (clear cache)
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model

# 5. Test with curl
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "description": "Test", "source": "web", "customer_tier": "Gold"}'
```

---

## 📝 Summary

✅ **Reference data** = Frozen baseline (never changes)  
✅ **New data** = Accumulates over time  
✅ **Combined data** = Reference + New (created automatically)  
✅ **Monitoring** = Compares Reference vs New  
✅ **Retraining** = Uses Combined data  
✅ **Reload** = Updates API cache without redeploy  

**Everything is set up exactly as you wanted!** 🎉
