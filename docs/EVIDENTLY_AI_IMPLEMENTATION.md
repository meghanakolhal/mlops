# Evidently AI Implementation Guide

## 🎯 Overview

This document explains the production-grade Evidently AI monitoring implementation for the MLOps pipeline.

## 📚 What You Need to Know for Your Interview

### Key Concepts:

1. **Data Drift**: When production data distribution differs from training data
2. **Statistical Tests**: KS test (numeric), Chi-square (categorical)
3. **Monitoring Pipeline**: Automated checks → Reports → Alerts
4. **Production Standards**: Statistical significance, visualization, automation

## 🔍 Understanding Evidently AI

### Why Evidently AI?

**Before (Simple Approach):**
```python
# Manual comparison - not production-ready
diff = abs(ref_dist - new_dist).sum()
if diff > 0.1:  # Arbitrary threshold
    drift_detected = True
```

**Problems:**
- No statistical significance
- Manual threshold setting
- No visualization
- Limited to categorical features

**After (Evidently AI):**
```python
# Statistical tests + visualization
from evidently.report import Report
from evidently.metrics import DataDriftTable

report = Report(metrics=[DataDriftTable()])
report.run(reference_data=ref, current_data=new)
report.save_html("report.html")  # Interactive dashboard
```

**Benefits:**
- ✅ Statistical significance testing (p-values)
- ✅ Automatic threshold detection
- ✅ Interactive HTML reports
- ✅ Works with all data types
- ✅ Industry-standard tool

## 📊 What Evidently AI Monitors

### 1. Data Drift Detection

**Column Drift:**
- Per-feature distribution comparison
- Statistical tests (KS, Chi-square)
- Drift score (0-1, higher = more drift)

**Dataset Drift:**
- Overall dataset comparison
- Number of drifted columns
- Share of drifted columns

### 2. Data Quality

- Missing values
- Duplicate rows
- Data type mismatches
- Outliers

### 3. Statistical Tests

- **Kolmogorov-Smirnov (KS) Test**: For numeric features
- **Chi-square Test**: For categorical features
- **P-values**: Statistical significance (< 0.05 = significant drift)

## 🏗️ Implementation Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Monitoring Workflow                          │
│                                                          │
│  1. Load Reference Data (training baseline)             │
│     ↓                                                    │
│  2. Load Current Data (production data)                 │
│     ↓                                                    │
│  3. Evidently AI Analysis                               │
│     ├── DataDriftTable()                                │
│     ├── DatasetDriftMetric()                            │
│     └── DataQualityTable()                             │
│     ↓                                                    │
│  4. Generate HTML Report (interactive dashboard)        │
│     ↓                                                    │
│  5. Run Test Suite (automated checks)                   │
│     ↓                                                    │
│  6. Upload Reports to GCS                               │
│     ├── HTML report (visualization)                     │
│     └── JSON summary (programmatic access)              │
│     ↓                                                    │
│  7. Alert if Drift Detected                             │
└─────────────────────────────────────────────────────────┘
```

## 📁 File Structure

```
scripts/
├── monitor_model.py              # Original simple monitoring
└── monitor_model_evidently.py   # NEW: Evidently AI monitoring

dags/
├── monitor_model.py              # Original DAG
└── monitor_model_evidently.py    # NEW: Evidently AI DAG

reports/                          # Local HTML reports (gitignored)
└── drift_report_*.html

GCS Structure:
gs://ml-model-bucket-22/
├── monitoring/
│   ├── reports/                  # HTML reports
│   │   └── drift_report_20251217_100514.html
│   └── summaries/                # JSON summaries
│       └── summary_20251217_100514.json
```

## 🔧 Code Explanation

### Key Components:

#### 1. **Report Generation**
```python
report = Report(metrics=[
    DataDriftTable(),        # Detailed drift for all columns
    DatasetDriftMetric(),    # Overall drift score
    DataQualityTable(),      # Data quality checks
])
report.run(reference_data=ref, current_data=new)
```

#### 2. **Test Suite**
```python
test_suite = TestSuite(tests=[
    TestNumberOfDriftedColumns(),      # How many columns drifted?
    TestShareOfDriftedColumns(),       # What percentage drifted?
    TestColumnDrift(column_name="source"),  # Specific column check
])
test_suite.run(reference_data=ref, current_data=new)
```

#### 3. **Report Storage**
```python
# Save HTML report
report.save_html("drift_report.html")

# Upload to GCS
blob.upload_from_filename("drift_report.html")
```

## 📈 Metrics Explained

### Dataset Drift Score
- **Range**: 0.0 to 1.0
- **Meaning**: 
  - 0.0 = No drift (identical distributions)
  - 1.0 = Complete drift (completely different)
  - > 0.5 = Significant drift detected

### Number of Drifted Columns
- Count of columns with statistically significant drift
- Based on p-value < 0.05 threshold

### Share of Drifted Columns
- Percentage of columns that drifted
- Example: 2 out of 4 columns = 50%

## 🎨 HTML Report Features

Evidently AI generates interactive HTML reports with:

1. **Dashboard Overview**
   - Dataset drift score
   - Number of drifted columns
   - Overall status

2. **Column-Level Analysis**
   - Per-column drift detection
   - Distribution comparisons (histograms)
   - Statistical test results (p-values)

3. **Data Quality Metrics**
   - Missing values
   - Duplicates
   - Data types

4. **Visualizations**
   - Distribution plots
   - Comparison charts
   - Exportable graphics

## 🚀 Running the Monitoring

### Option 1: Via Airflow UI
1. Open Airflow UI: `http://localhost:8085`
2. Find DAG: `ticket_urgency_model_monitoring_evidently`
3. Toggle ON
4. Click "Trigger DAG"
5. View logs and results

### Option 2: Manual Execution
```bash
docker compose exec airflow-scheduler bash -lc \
  "python /opt/airflow/scripts/monitor_model_evidently.py"
```

## 📊 Viewing Reports

### HTML Reports (GCS)
```bash
# List all reports
gsutil ls gs://ml-model-bucket-22/monitoring/reports/

# Download a report
gsutil cp gs://ml-model-bucket-22/monitoring/reports/drift_report_*.html ./
# Open in browser
```

### JSON Summaries (Programmatic Access)
```python
from google.cloud import storage
import json

client = storage.Client()
bucket = client.bucket("ml-model-bucket-22")
blob = bucket.blob("monitoring/summaries/summary_20251217_100514.json")
summary = json.loads(blob.download_as_text())

print(f"Drift detected: {summary['summary']['dataset_drift_detected']}")
print(f"Drift score: {summary['summary']['dataset_drift_score']}")
```

## 🎯 Interview Talking Points

### When Asked About Monitoring:

1. **"How do you monitor models in production?"**
   - "We use Evidently AI for statistical data drift detection"
   - "Daily monitoring compares production data against training baseline"
   - "Statistical tests (KS, Chi-square) detect significant changes"
   - "HTML reports provide visual dashboards for stakeholders"

2. **"What metrics do you track?"**
   - "Dataset drift score (0-1 scale)"
   - "Number and percentage of drifted columns"
   - "Data quality metrics (missing values, duplicates)"
   - "Statistical significance (p-values)"

3. **"How do you handle drift detection?"**
   - "Automated daily checks via Airflow"
   - "Reports stored in GCS for historical analysis"
   - "Alerts trigger when drift exceeds thresholds"
   - "Retraining pipeline triggered on significant drift"

4. **"Why Evidently AI over custom solutions?"**
   - "Industry-standard tool with statistical rigor"
   - "Interactive visualizations for stakeholders"
   - "Comprehensive test suite"
   - "Production-ready and battle-tested"

## 🔄 Workflow Integration

```
Daily Monitoring Flow:
1. Airflow triggers monitoring DAG
2. Load reference data (training baseline)
3. Load current production data
4. Evidently AI analysis
5. Generate HTML report
6. Upload to GCS
7. If drift detected → Alert → Trigger retraining
```

## 📝 Key Takeaways

1. **Evidently AI** = Production-grade monitoring tool
2. **Statistical Tests** = Proper drift detection (not arbitrary thresholds)
3. **HTML Reports** = Visual dashboards for stakeholders
4. **Automation** = Daily checks via Airflow
5. **Storage** = GCS for historical tracking

## 🎓 Learning Resources

- Evidently AI Docs: https://docs.evidentlyai.com/
- Statistical Tests: https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test
- MLOps Monitoring Best Practices: Industry standards

---

**Next Steps**: Run the monitoring DAG and explore the HTML reports!
