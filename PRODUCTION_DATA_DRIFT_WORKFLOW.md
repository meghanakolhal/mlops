# Production Data Drift Workflow - Complete Guide

## 🎯 How Data Drift Works in Production

### Data Organization in GCS

```
gs://ml-model-bucket-22/
├── datasets/
│   ├── tickets.csv              # Reference data (original training data)
│   ├── new_tickets.csv           # New production data (arrives daily/weekly)
│   └── combined_tickets.csv      # Reference + new (after retraining)
├── ticket_urgency_model/
│   └── ticket_urgency_model.pkl  # Current production model
└── monitoring/
    └── report_YYYYMMDD_HHMMSS.json  # Daily monitoring reports
```

### Key Concepts

1. **Reference Data** (`datasets/tickets.csv`):
   - Original training data
   - Used as baseline for comparison
   - **Never changes** (or only updates when you explicitly retrain)

2. **New Production Data** (`datasets/new_tickets.csv`):
   - New tickets arriving in production
   - Uploaded periodically (daily/weekly)
   - Compared against reference data to detect drift

3. **Combined Data** (`datasets/combined_tickets.csv`):
   - Reference + new data combined
   - Created when retraining after drift detected
   - Can become new reference for next retrain cycle

---

## 🔄 Complete Production Workflow

### Step 1: Initial Setup (One-Time)

```bash
# Upload reference training data
gsutil cp data/raw/tickets.csv gs://ml-model-bucket-22/datasets/tickets.csv

# Train initial model
# (Trigger training DAG in Airflow)
# Model saved to: ticket_urgency_model/ticket_urgency_model.pkl
```

### Step 2: Daily Monitoring (Automated)

**Airflow DAG runs daily:**
1. Checks API health
2. Tests prediction endpoint
3. Loads reference data: `datasets/tickets.csv`
4. Loads new data: `datasets/new_tickets.csv` (if exists)
5. Compares distributions → **Detects drift**
6. Saves report to `monitoring/report_*.json`

**If drift detected:**
- Alert sent (email/Slack)
- Trigger retraining workflow

### Step 3: When New Data Arrives

**Option A: Manual Upload**
```bash
# Collect new production tickets
# Upload to GCS
gsutil cp new_tickets.csv gs://ml-model-bucket-22/datasets/new_tickets.csv
```

**Option B: Automated Collection** (Future)
- API logs all predictions to BigQuery
- Daily job extracts new tickets from BigQuery
- Uploads to GCS automatically

### Step 4: Retrain After Drift Detected

**Manual Retrain:**
```bash
# Run combine and retrain script
python scripts/combine_and_retrain.py
```

**Or trigger via Airflow DAG** (we'll create this next)

### Step 5: Deploy New Model

**Option A: Reload API Cache**
```bash
# Call reload endpoint
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model
```

**Option B: Redeploy API** (Recommended)
- Push changes to main branch
- GitHub Actions rebuilds and redeploys
- New containers automatically load new model

---

## 📊 Data Organization Strategy

### Strategy 1: Keep Reference Separate (Recommended)

```
datasets/
├── tickets.csv              # Original reference (never changes)
├── new_tickets_20251217.csv # Daily new data (dated)
├── new_tickets_20251218.csv
└── combined_tickets.csv     # Latest combined (for retraining)
```

**Pros:**
- Can compare any day's data to reference
- Historical tracking
- Can retrain on different date ranges

### Strategy 2: Append to Single File

```
datasets/
├── tickets.csv              # Reference (original)
└── production_tickets.csv    # All new data appended here
```

**Pros:**
- Simpler
- One file to check

**Cons:**
- Harder to track daily changes
- File grows large

---

## 🔧 API Cache Management

### Current Behavior

1. **On Startup**: Downloads model from GCS → caches in `/tmp/model.pkl`
2. **On Request**: Uses cached model (fast!)
3. **Problem**: New model uploaded to GCS → API still uses old cached model

### Solution Implemented

**Automatic Version Checking:**
- API checks model's `updated` timestamp in GCS
- If timestamp changed → automatically reloads model
- No manual intervention needed!

**Manual Reload Endpoint:**
- `/reload-model` endpoint to force reload
- Useful for immediate updates

---

## 🚀 Complete Workflow Example

### Day 1: Initial Training
```
1. Upload reference data → datasets/tickets.csv
2. Train model → ticket_urgency_model/ticket_urgency_model.pkl
3. Deploy API → API loads model
```

### Day 2-6: Normal Operation
```
1. New tickets arrive → stored in production system
2. Daily monitoring runs → compares reference vs (empty) new data
3. No drift detected → continue using current model
```

### Day 7: New Data Arrives
```
1. Upload new tickets → datasets/new_tickets.csv
2. Daily monitoring runs → DRIFT DETECTED!
3. Alert triggered → "Data drift detected, retraining needed"
```

### Day 7 (Afternoon): Retrain
```
1. Run combine_and_retrain.py:
   - Combines reference + new data
   - Trains new model
   - Uploads to GCS (overwrites old model)
2. Model version changes (new timestamp)
3. API automatically detects change → reloads model
   OR
   Call /reload-model endpoint
```

### Day 8+: Continue Monitoring
```
1. Reference data stays same (datasets/tickets.csv)
2. New data accumulates (datasets/new_tickets.csv)
3. Monitor continues comparing reference vs new
```

---

## 📝 Key Points

### 1. Reference Data Management

**Question:** "Will they maintain one data just to compare?"

**Answer:** Yes! Two approaches:

**Approach A: Fixed Reference** (Recommended)
- `datasets/tickets.csv` = Original training data (never changes)
- Always compare new data against this fixed reference
- Easy to understand drift over time

**Approach B: Rolling Reference**
- After retraining, update reference to combined data
- Compare new data against "last retrained" data
- More complex but adapts faster

### 2. Data Folder Organization

**Single folder is fine!** Structure:
```
datasets/
├── tickets.csv           # Reference (baseline)
├── new_tickets.csv       # Current new data
└── combined_tickets.csv # Combined (for retraining)
```

### 3. Cache Clearing

**Automatic:** API checks model version on each request
- If GCS model updated → automatically reloads
- No manual cache clearing needed!

**Manual:** Use `/reload-model` endpoint if needed

---

## ✅ Next Steps

1. ✅ **API cache fixed** - Auto-reloads when model changes
2. ✅ **Combine script created** - `scripts/combine_and_retrain.py`
3. ⏭️ **Create retrain DAG** - Auto-trigger when drift detected
4. ⏭️ **Upload new data** - Test drift detection
5. ⏭️ **Test complete workflow** - End-to-end

---

**Ready to test!** Upload new data and see drift detection work! ✅
