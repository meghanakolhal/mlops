# Complete Data Drift Testing Workflow

## 🎯 Goal
Test the complete data drift detection workflow:
1. Upload training data to GCS
2. Train model (loads from GCS)
3. Upload new production data (with different distribution)
4. Run monitoring to detect drift
5. Retrain model with new data
6. Compare model performance

---

## 📋 Step-by-Step Guide

### Step 1: Upload Data to GCS (One-Time Setup)

**Option A: Using Python Script (Recommended)**
```bash
# From project root
cd c:\prepare\mlops-ticket-urgency\airflow
python scripts/upload_data_to_gcs.py
```

**Option B: Using gsutil (Manual)**
```bash
# Upload training data
gsutil cp data/raw/tickets.csv gs://ml-model-bucket-22/datasets/tickets.csv

# Upload new production data (for drift testing)
gsutil cp data/raw/new_tickets.csv gs://ml-model-bucket-22/datasets/new_tickets.csv
```

**What this does:**
- Uploads `tickets.csv` → `gs://ml-model-bucket-22/datasets/tickets.csv` (reference data)
- Uploads `new_tickets.csv` → `gs://ml-model-bucket-22/datasets/new_tickets.csv` (new data with drift)

---

### Step 2: Train Model (Loads from GCS)

1. **Go to Airflow UI**: http://localhost:8085
2. **Trigger DAG**: `ticket_urgency_model_training`
3. **Check logs**: Should show "✅ Loaded X rows from GCS"
4. **Model uploaded**: `gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl`

---

### Step 3: Check Data Distributions (Understand the Drift)

**Reference Data (tickets.csv):**
- `source`: Mix of web, email, chat, monitoring
- `customer_tier`: Mix of Gold, Silver, Bronze

**New Data (new_tickets.csv):**
- **More `web` tickets** (60% vs ~30% in reference)
- **More `phone` tickets** (35% vs ~10% in reference)
- **Less `email` tickets** (5% vs ~40% in reference)
- **More `Bronze` customers** (shift in customer tier distribution)

**This will trigger DRIFT DETECTION!** ✅

---

### Step 4: Run Monitoring DAG (Detect Drift)

1. **Go to Airflow UI**: http://localhost:8085
2. **Trigger DAG**: `ticket_urgency_model_monitoring`
3. **Check logs**: Should show:
   ```
   ⚠️  Data drift detected!
   {
     "source": {
       "drift_score": 0.45,  # High drift!
       "reference_dist": {...},
       "new_dist": {...}
     },
     "customer_tier": {
       "drift_score": 0.25,  # Moderate drift
       ...
     }
   }
   ```
4. **Report saved**: `gs://ml-model-bucket-22/monitoring/report_YYYYMMDD_HHMMSS.json`

---

### Step 5: Test Model Performance on New Data

Create a script to evaluate model on new data:

```python
# scripts/evaluate_on_new_data.py
import pandas as pd
import joblib
from google.cloud import storage
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os

# Load model from GCS
BUCKET_NAME = "ml-model-bucket-22"
MODEL_PATH = "ticket_urgency_model/ticket_urgency_model.pkl"
NEW_DATA_PATH = "datasets/new_tickets.csv"

# Download model
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)
blob = bucket.blob(MODEL_PATH)
blob.download_to_filename("/tmp/model.pkl")
model = joblib.load("/tmp/model.pkl")

# Load new data
blob = bucket.blob(NEW_DATA_PATH)
blob.download_to_filename("/tmp/new_data.csv")
df = pd.read_csv("/tmp/new_data.csv")

# Prepare features
df["text"] = df["title"] + " " + df["description"]
X = df[["text", "source", "customer_tier"]]
y = df["label_urgency"]

# Predict
y_pred = model.predict(X)

# Evaluate
print("Model Performance on New Data:")
print(f"Accuracy: {accuracy_score(y, y_pred):.4f}")
print(f"Precision: {precision_score(y, y_pred, pos_label='urgent'):.4f}")
print(f"Recall: {recall_score(y, y_pred, pos_label='urgent'):.4f}")
print(f"F1: {f1_score(y, y_pred, pos_label='urgent'):.4f}")
```

---

### Step 6: Retrain Model with Combined Data

**Option A: Manual Retrain**
1. Combine reference + new data
2. Upload combined data to GCS
3. Trigger training DAG

**Option B: Update Training Script** (Future)
- Modify `train.py` to:
  - Load reference data: `datasets/tickets.csv`
  - Load new data: `datasets/new_tickets.csv`
  - Combine them
  - Train on combined dataset

---

## 📊 Expected Results

### Before Drift Detection:
- **Reference data**: Balanced distribution
- **Model trained**: On balanced data
- **Performance**: Good on reference data

### After New Data Arrives:
- **New data**: Different distribution (more web/phone, less email)
- **Drift detected**: Yes! (drift_score > 0.1)
- **Model performance**: May degrade on new data patterns

### After Retraining:
- **Combined data**: Reference + new data
- **Model retrained**: On updated distribution
- **Performance**: Better on new data patterns

---

## 🔍 Understanding the Drift

### Why Drift Matters:

**Example Scenario:**
- **Training**: 40% email tickets, 30% web tickets
- **Production**: 5% email tickets, 60% web tickets
- **Problem**: Model learned patterns from email tickets, but now sees mostly web tickets
- **Result**: Model accuracy drops on new data

### What the Code Does:

```python
# In check_data_drift():
# 1. Calculate distribution in reference data
ref_dist = reference_data["source"].value_counts(normalize=True)
# Example: email=0.40, web=0.30, phone=0.20, chat=0.10

# 2. Calculate distribution in new data
new_dist = new_data["source"].value_counts(normalize=True)
# Example: email=0.05, web=0.60, phone=0.30, chat=0.05

# 3. Calculate difference
diff = abs(ref_dist - new_dist.reindex(ref_dist.index, fill_value=0)).sum()
# diff = |0.40-0.05| + |0.30-0.60| + |0.20-0.30| + |0.10-0.05|
# diff = 0.35 + 0.30 + 0.10 + 0.05 = 0.80

# 4. If diff > 0.1 (threshold) → DRIFT DETECTED!
# 0.80 > 0.1 → ✅ DRIFT DETECTED!
```

---

## ✅ Quick Test Checklist

- [ ] Upload training data to GCS: `datasets/tickets.csv`
- [ ] Upload new data to GCS: `datasets/new_tickets.csv`
- [ ] Train model (loads from GCS)
- [ ] Run monitoring DAG (detects drift)
- [ ] Check monitoring report in GCS
- [ ] Evaluate model on new data
- [ ] Retrain model with combined data
- [ ] Compare performance before/after retraining

---

## 🚀 Next Steps After Testing

1. **Automate**: Create DAG that auto-triggers training when drift detected
2. **Alerting**: Send alerts when drift exceeds threshold
3. **Versioning**: Track model versions and performance over time
4. **A/B Testing**: Compare old vs new model performance

---

**Ready to test!** Start with Step 1: Upload data to GCS ✅
