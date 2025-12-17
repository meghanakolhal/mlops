# Data Drift Workflow - Explained Simply

## 📋 Answers to Your Questions

### 1. **Is it using GCS or local data?**

**BEFORE (Old Code):**
- ❌ `train.py` → Used `data/raw/tickets.csv` (local)
- ❌ `monitor_model.py` → Used `data/raw/tickets.csv` (local)

**AFTER (Updated Code):**
- ✅ `train.py` → **Loads from GCS**: `gs://ml-model-bucket-22/datasets/tickets.csv`
- ✅ `monitor_model.py` → **Loads reference data from GCS**: `gs://ml-model-bucket-22/datasets/tickets.csv`
- ✅ Falls back to local file if GCS fails (for development)

---

### 2. **Why API health check failed?**

The timeout was **5 seconds**, which is too short. Cloud Run can take longer to respond, especially on cold starts.

**Fixed:** Increased timeout to **15 seconds** in `check_api_health()`.

---

### 3. **What payload is used for prediction? Why 0.55 confidence?**

**BEFORE:** Used hardcoded test data:
```python
{
    "title": "Server down",
    "description": "Production server is not responding",
    "source": "email",
    "customer_tier": "premium"
}
```

**AFTER:** Uses realistic test data similar to your training data:
```python
{
    "title": "Application running slow",
    "description": "Report export stuck at 80 percent for several minutes.",
    "source": "web",
    "customer_tier": "Gold"
}
```

**Why 0.55 confidence?**
- The old test data (`"premium"` customer tier) might not match your training data well
- Your training data uses `"Gold"`, `"Silver"`, `"Bronze"` (not `"premium"`)
- When the model sees unfamiliar combinations, it gives low confidence (~0.5 = unsure)

---

### 4. **Data Drift Workflow - How It Works**

Here's the complete workflow:

#### **Step 1: Initial Training**
```
1. Upload training data to GCS:
   gs://ml-model-bucket-22/datasets/tickets.csv

2. Run training DAG:
   - Loads data from GCS: datasets/tickets.csv
   - Trains model
   - Uploads model to GCS: ticket_urgency_model/ticket_urgency_model.pkl
```

#### **Step 2: Deploy Model**
```
3. Model is deployed to Cloud Run (via GitHub Actions)
   - API loads model from GCS on startup
```

#### **Step 3: Collect New Production Data**
```
4. As tickets come in, collect them:
   - Store in GCS: gs://ml-model-bucket-22/datasets/new_tickets.csv
   - Or: gs://ml-model-bucket-22/datasets/production_tickets_YYYYMMDD.csv
```

#### **Step 4: Check for Drift**
```
5. Run monitoring DAG (daily):
   - Loads REFERENCE data: datasets/tickets.csv (original training data)
   - Loads NEW data: datasets/new_tickets.csv (recent production data)
   - Compares distributions:
     * source (email/web/phone) distribution
     * customer_tier (Gold/Silver/Bronze) distribution
   - If distributions changed significantly → DRIFT DETECTED!
```

#### **Step 5: Retrain if Drift Detected**
```
6. If drift detected:
   - Option A: Manually trigger training DAG
   - Option B: Auto-trigger training (future enhancement)
   - New model trained on updated data
   - New model uploaded to GCS
   - Redeploy API to use new model
```

---

## 🔍 How Data Drift Detection Works (Simple Explanation)

### What is "Drift"?

**Drift** = When new production data looks **different** from training data.

### Example:

**Training Data (Reference):**
- 50% tickets from `email`
- 30% tickets from `web`
- 20% tickets from `phone`

**New Production Data:**
- 20% tickets from `email`  ← Changed!
- 60% tickets from `web`    ← Changed!
- 20% tickets from `phone`

**Result:** Drift detected! The distribution changed significantly.

### Why This Matters:

If your model was trained on mostly `email` tickets, but now you're getting mostly `web` tickets, the model might not work as well.

---

## 📊 Current Code Logic

```python
def check_data_drift(reference_data, new_data):
    # For each column (source, customer_tier):
    # 1. Calculate distribution in reference data
    #    Example: email=50%, web=30%, phone=20%
    # 2. Calculate distribution in new data
    #    Example: email=20%, web=60%, phone=20%
    # 3. Calculate difference: |50%-20%| + |30%-60%| + |20%-20%| = 60%
    # 4. If difference > 10% (threshold) → DRIFT DETECTED
```

---

## 🚀 Next Steps to Complete the Workflow

### 1. Upload Training Data to GCS

```bash
# Upload your current tickets.csv to GCS
gsutil cp data/raw/tickets.csv gs://ml-model-bucket-22/datasets/tickets.csv
```

### 2. Test Training with GCS Data

```bash
# Run training DAG - it will now load from GCS
# Check Airflow UI → ticket_urgency_model_training DAG
```

### 3. When New Data Arrives

```bash
# Upload new production data
gsutil cp new_tickets.csv gs://ml-model-bucket-22/datasets/new_tickets.csv

# Or append to existing file
# (You might want to create a script for this)
```

### 4. Run Monitoring

```bash
# Trigger monitoring DAG manually
# It will compare:
# - Reference: datasets/tickets.csv
# - New: datasets/new_tickets.csv
```

### 5. Future: Auto-trigger Training on New Data

We can add a DAG that:
- Watches for new files in `gs://ml-model-bucket-22/datasets/`
- Automatically triggers training when new data arrives
- Then triggers monitoring

---

## ✅ Summary

1. ✅ **Training now loads from GCS**: `datasets/tickets.csv`
2. ✅ **Monitoring loads reference from GCS**: `datasets/tickets.csv`
3. ✅ **Monitoring compares with new data**: `datasets/new_tickets.csv` (when available)
4. ✅ **API health timeout increased**: 15 seconds
5. ✅ **Better test data**: Uses realistic examples from training data

**Next:** Upload your data to GCS and test!
