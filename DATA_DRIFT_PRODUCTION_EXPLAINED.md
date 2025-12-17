# Production Data Drift - Complete Explanation

## 🎯 Your Questions Answered

### 1. "How does data drift work in production?"

**Simple Answer:**
- You keep **one reference dataset** (original training data)
- New production data arrives daily/weekly
- Compare new data **distribution** vs reference distribution
- If distributions differ significantly → **DRIFT DETECTED!**

### 2. "Data will be added to one folder only, right?"

**Answer:** Yes! Recommended structure:

```
gs://ml-model-bucket-22/datasets/
├── tickets.csv           # Reference data (baseline - never changes)
├── new_tickets.csv       # New production data (updated daily/weekly)
└── combined_tickets.csv # Reference + new (created during retraining)
```

**Why separate files?**
- `tickets.csv` = **Fixed reference** (always compare against this)
- `new_tickets.csv` = **Current new data** (changes over time)
- `combined_tickets.csv` = **For retraining** (reference + new combined)

### 3. "Will they maintain one data just to compare?"

**Answer:** Yes! Two approaches:

**Approach A: Fixed Reference** (Recommended ✅)
- Keep `tickets.csv` as **permanent baseline**
- Always compare new data against this fixed reference
- Easy to track: "How much has data changed since original training?"

**Approach B: Rolling Reference**
- After retraining, update reference to latest combined data
- Compare new data against "last retrained" data
- More complex but adapts faster

**We're using Approach A** - fixed reference!

---

## 🔄 Complete Production Workflow

### Step 1: Initial Setup
```
1. Upload reference data → datasets/tickets.csv
2. Train model → ticket_urgency_model/ticket_urgency_model.pkl
3. Deploy API → API loads model
```

### Step 2: Daily Monitoring (Automated)
```
1. Monitoring DAG runs daily
2. Loads reference: datasets/tickets.csv
3. Loads new data: datasets/new_tickets.csv (if exists)
4. Compares distributions:
   - source (email/web/phone) distribution
   - customer_tier (Gold/Silver/Bronze) distribution
5. If difference > 10% → DRIFT DETECTED!
6. Saves report to monitoring/report_*.json
```

### Step 3: When New Data Arrives
```
1. Collect new production tickets
2. Upload to GCS: datasets/new_tickets.csv
   (Can append or replace - your choice)
```

### Step 4: Retrain After Drift
```
1. Run combine_and_retrain.py:
   - Loads reference: datasets/tickets.csv
   - Loads new: datasets/new_tickets.csv
   - Combines them
   - Trains new model
   - Uploads to GCS (overwrites old model)
2. Model file updated → timestamp changes
3. API detects change → auto-reloads model ✅
```

### Step 5: API Cache Management

**Problem:** API caches model in memory and `/tmp/model.pkl`

**Solution Implemented:**
- API checks model's **updated timestamp** in GCS
- If timestamp changed → **automatically reloads**
- No manual cache clearing needed!

**Manual Option:**
- Call `/reload-model` endpoint to force reload

---

## 📊 Data Organization Strategy

### Recommended Structure:

```
gs://ml-model-bucket-22/
├── datasets/
│   ├── tickets.csv              # Reference (baseline - fixed)
│   ├── new_tickets.csv           # New production data (updated)
│   └── combined_tickets.csv      # Combined (for retraining)
├── ticket_urgency_model/
│   └── ticket_urgency_model.pkl  # Current model (updated on retrain)
└── monitoring/
    └── report_*.json            # Daily monitoring reports
```

### Why This Structure?

1. **`tickets.csv`** (Reference):
   - Original training data
   - **Never changes** (or only when you explicitly update baseline)
   - Used for drift comparison

2. **`new_tickets.csv`** (New Data):
   - Current production tickets
   - Updated daily/weekly
   - Compared against reference

3. **`combined_tickets.csv`** (Combined):
   - Created during retraining
   - Reference + new data
   - Used for training new model

---

## 🔧 API Cache Clearing - How It Works

### Before (Problem):
```
1. Model cached in memory: model = <loaded_model>
2. Model cached on disk: /tmp/model.pkl
3. New model uploaded to GCS
4. API still uses old cached model ❌
```

### After (Solution):
```
1. API checks model version (updated timestamp) on each request
2. If GCS model updated → timestamp changed
3. API detects change → clears cache → reloads model ✅
4. New model automatically used!
```

### Code Logic:

```python
# In download_model_from_gcs():
# 1. Get model version from GCS (updated timestamp)
gcs_version = blob.updated.isoformat()

# 2. Compare with cached version
if cached_version != gcs_version:
    # Model changed! Reload
    model = None  # Clear memory
    os.remove(MODEL_CACHE_PATH)  # Clear disk cache
    download_from_gcs()  # Download new model
```

---

## 🚀 Complete Testing Workflow

### 1. Upload New Data
```bash
# Upload new tickets with different distribution
gsutil cp data/raw/new_tickets.csv gs://ml-model-bucket-22/datasets/new_tickets.csv
```

### 2. Run Monitoring
```
Airflow UI → Trigger monitoring DAG
→ Should detect drift!
```

### 3. Retrain Model
```bash
# Option A: Via Airflow DAG
Airflow UI → Trigger retrain_model DAG

# Option B: Manual script
python scripts/combine_and_retrain.py
```

### 4. Verify API Reloads
```bash
# Check health - should show new model_version
curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/health

# Or force reload
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model
```

---

## ✅ Summary

1. ✅ **Reference data**: `datasets/tickets.csv` (fixed baseline)
2. ✅ **New data**: `datasets/new_tickets.csv` (updated regularly)
3. ✅ **Drift detection**: Compares reference vs new distributions
4. ✅ **Retraining**: Combines reference + new → trains → uploads model
5. ✅ **API cache**: Auto-reloads when model version changes
6. ✅ **Manual reload**: `/reload-model` endpoint available

**Everything is set up!** Ready to test the complete workflow! 🚀
