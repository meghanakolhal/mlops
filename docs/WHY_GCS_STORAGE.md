# Why Save Reports to GCS?

## 🎯 Quick Answer

**Yes, we save reports to GCS for permanent storage and sharing. Evidently AI doesn't have its own UI - it generates HTML reports that you view in a browser.**

## 📊 Where Reports Are Stored

### 1. **Airflow Logs** (Temporary)
- Location: `/opt/airflow/logs/` (or `./logs/` locally)
- Purpose: Task execution logs
- Duration: Can be cleared/deleted
- View: Airflow UI → Task → Log button
- Contains: Text output, print statements

### 2. **GCS Storage** (Permanent)
- Location: `gs://ml-model-bucket-22/monitoring/reports/`
- Purpose: Historical tracking, sharing, analysis
- Duration: Permanent (until you delete)
- View: Download HTML file → Open in browser
- Contains: Interactive HTML reports, JSON summaries

## 🔍 Why GCS Storage?

### 1. **Permanent Historical Tracking**
```
Airflow logs: Temporary, can be cleared
GCS reports: Permanent, historical analysis
```

**Use Case**: Compare drift reports from last month vs this month

### 2. **Share with Stakeholders**
```
Airflow logs: Only accessible to Airflow users
GCS reports: Download and share HTML files with anyone
```

**Use Case**: Send HTML report to data science team, product managers

### 3. **Evidently AI Has No Built-in UI**
```
Evidently AI = Library that generates HTML reports
No web UI = You need to store reports somewhere
```

**How it works:**
1. Evidently AI generates HTML file
2. We save it to GCS
3. Download from GCS
4. Open HTML file in browser → Interactive dashboard

### 4. **Programmatic Access**
```python
# Access JSON summaries programmatically
from google.cloud import storage
import json

client = storage.Client()
bucket = client.bucket("ml-model-bucket-22")
blob = bucket.blob("monitoring/summaries/summary_20251217.json")
summary = json.loads(blob.download_as_text())

# Use in alerts, dashboards, etc.
if summary['summary']['dataset_drift_detected']:
    send_alert("Drift detected!")
```

### 5. **Backup and Recovery**
```
Airflow logs: Lost if container deleted
GCS reports: Safe in cloud storage
```

## 📁 Report Structure

### HTML Reports (Visual Dashboards)
```
gs://bucket/monitoring/reports/drift_report_20251217_100514.html
```
- **Purpose**: Visual dashboards for stakeholders
- **View**: Download → Open in browser
- **Contains**: Interactive charts, drift visualizations, statistical tests

### JSON Summaries (Programmatic Access)
```
gs://bucket/monitoring/summaries/summary_20251217_100514.json
```
- **Purpose**: Automated alerts, dashboards, analysis
- **View**: Download → Parse JSON
- **Contains**: Drift scores, metrics, test results

## 🎨 How to View Reports

### Option 1: Download from GCS
```bash
# List all reports
gsutil ls gs://ml-model-bucket-22/monitoring/reports/

# Download a report
gsutil cp gs://ml-model-bucket-22/monitoring/reports/drift_report_*.html ./

# Open in browser
open drift_report_20251217_100514.html  # Mac
start drift_report_20251217_100514.html  # Windows
```

### Option 2: View in Airflow Logs
- Airflow UI → DAG → Task → Log
- See text output, but not interactive HTML

### Option 3: Programmatic Access
```python
# Download and parse JSON summary
from google.cloud import storage
import json

client = storage.Client()
bucket = client.bucket("ml-model-bucket-22")
blob = bucket.blob("monitoring/summaries/summary_20251217_100514.json")
summary = json.loads(blob.download_as_text())

print(f"Drift detected: {summary['summary']['dataset_drift_detected']}")
print(f"Drift score: {summary['summary']['dataset_drift_score']}")
```

## 🔄 Workflow

```
1. Monitoring DAG runs
   ↓
2. Evidently AI generates HTML report
   ↓
3. Report saved locally (temporary)
   ↓
4. Report uploaded to GCS (permanent)
   ↓
5. JSON summary also saved to GCS
   ↓
6. View HTML in browser OR access JSON programmatically
```

## 💡 Key Points

1. **Evidently AI = No UI**: It's a library, not a web service
2. **HTML Reports**: Interactive dashboards you view in browser
3. **GCS Storage**: Permanent storage for historical tracking
4. **Airflow Logs**: Temporary, for debugging
5. **JSON Summaries**: For automated alerts and dashboards

## 🎯 Interview Answer

**Q: "Why do you save reports to GCS instead of just viewing in Airflow?"**

**A:**
- "Evidently AI generates HTML reports that need to be viewed in a browser - it doesn't have its own UI"
- "GCS provides permanent storage for historical analysis and comparison"
- "HTML reports can be shared with stakeholders who don't have Airflow access"
- "JSON summaries enable programmatic access for automated alerts and dashboards"
- "Airflow logs are temporary and can be cleared, while GCS provides long-term storage"

---

**Summary**: GCS = Permanent storage + Sharing + Historical tracking. Evidently AI = HTML reports (no built-in UI).
