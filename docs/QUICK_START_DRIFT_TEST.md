# Quick Start: Test Data Drift Detection

## 🎯 What We're Testing

1. ✅ Upload training data to GCS
2. ✅ Upload new data (with different distribution) to GCS  
3. ✅ Train model (loads from GCS)
4. ✅ Run monitoring → **Detect drift!**
5. ✅ Evaluate model on new data
6. ✅ Retrain model with combined data

---

## ⚡ Quick Commands

### 1. Upload Data to GCS (One-Time)

```bash
# Option A: Using Python script
cd c:\prepare\mlops-ticket-urgency\airflow
python scripts/upload_data_to_gcs.py

# Option B: Using gsutil
gsutil cp data/raw/tickets.csv gs://ml-model-bucket-22/datasets/tickets.csv
gsutil cp data/raw/new_tickets.csv gs://ml-model-bucket-22/datasets/new_tickets.csv
```

### 2. Train Model

**Airflow UI:**
- Go to http://localhost:8085
- Trigger DAG: `ticket_urgency_model_training`
- Check logs: Should show "✅ Loaded X rows from GCS"

### 3. Run Monitoring (Detect Drift)

**Airflow UI:**
- Trigger DAG: `ticket_urgency_model_monitoring`
- Check logs: Should show "⚠️ Data drift detected!"

### 4. Evaluate Model on New Data

```bash
cd c:\prepare\mlops-ticket-urgency\airflow
python scripts/evaluate_on_new_data.py
```

---

## 📊 Expected Results

### Drift Detection:
```
⚠️  Data drift detected!
{
  "source": {
    "drift_score": 0.45,  # High drift!
    ...
  },
  "customer_tier": {
    "drift_score": 0.25,  # Moderate drift
    ...
  }
}
```

### Model Performance:
- May show lower accuracy/precision on new data
- This indicates model needs retraining!

---

## 🔍 What's Different in New Data?

**Reference Data (`tickets.csv`):**
- Balanced distribution across sources

**New Data (`new_tickets.csv`):**
- **60% web tickets** (vs ~30% in reference)
- **35% phone tickets** (vs ~10% in reference)  
- **5% email tickets** (vs ~40% in reference)
- **More Bronze customers**

**Result:** Significant drift detected! ✅

---

## ✅ Next Steps After Drift Detected

1. **Retrain model** with combined data (reference + new)
2. **Compare performance** before/after retraining
3. **Deploy new model** to Cloud Run
4. **Monitor** to ensure performance improves

---

**Ready to test!** Start with uploading data to GCS ✅
