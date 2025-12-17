# MLOps Ticket Urgency Model Training Pipeline

End-to-end MLOps pipeline for training and deploying a ticket urgency classification model.

## 🏗️ Architecture

- **Airflow**: Orchestrates daily model training workflows
- **MLflow**: Tracks experiments, metrics, and model versions
- **Google Cloud Storage (GCS)**: Stores trained models
- **Docker Compose**: Local development environment

## 📁 Project Structure

Top-level layout (inside `airflow/`):

```
.
├── dags/                         # Airflow DAG definitions
│   └── train_model.py            # Training DAG (calls scripts.train.main)
├── scripts/                      # Training / deployment / monitoring scripts
│   ├── train.py                  # Main training script (logs to MLflow, uploads model to GCS)
│   ├── preprocess.py             # (Reserved for additional preprocessing logic)
│   ├── deploy_to_cloudrun.sh     # Manual deploy of FastAPI service to Cloud Run
│   └── monitor_model.py          # Monitoring script (API health + basic data drift)
├── api/                          # Model serving API (Cloud Run)
│   ├── app.py                    # FastAPI app loading model from GCS
│   ├── Dockerfile                # API container image (uvicorn + FastAPI)
│   └── requirements.txt          # API dependencies (FastAPI, sklearn, etc.)
├── data/                         # Local data (used by training / monitoring)
│   └── raw/
│       └── tickets.csv           # Labeled tickets used for training
├── .github/
│   └── workflows/
│       └── deploy.yml            # GitHub Actions CI/CD to build & deploy API to Cloud Run
├── Dockerfile                    # Airflow image (scheduler + webserver)
├── docker-compose.yaml           # Local stack (Airflow + PostgreSQL + MLflow)
├── fernet.py                     # Local Fernet key helper (for Airflow if needed)
├── README.md                     # Project overview (this file)
├── DEPLOYMENT_ROADMAP.md         # End-to-end deployment & roadmap
├── TEST_API.md                   # Examples for testing API endpoints
├── GITHUB_SETUP_GUIDE.md         # How to configure GitHub Secrets & CI/CD
├── QUICK_START.md                # Short quick-start and common commands
├── SETUP_MAIN_BRANCH.md          # Notes on using main branch + CI
├── DEBUG_CLOUD_RUN.md            # Notes for debugging Cloud Run issues
├── FIX_ASGI_ERROR.md             # Why we use uvicorn (FastAPI ASGI)
├── FIX_PERMISSIONS.md            # Cloud Run & IAM permission fixes
└── FIX_VERSION_MISMATCH.md       # scikit-learn version mismatch explanation
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Google Cloud account with service account key
- GCS bucket for model storage

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/meghanakolhal/mlops.git
   cd mlops
   ```

2. **Place your service account key**:
   - Copy your GCP service account JSON key to `service-acc-key.json` in the root directory

3. **Start the services**:
   ```bash
   docker compose up -d --build
   ```

4. **Access Airflow UI**:
   - Open http://localhost:8085
   - Login: `admin` / `admin`

5. **Access MLflow UI**:
   - Open http://localhost:5000

### Running Training

**Option 1: Via Airflow UI**
- Trigger the `ticket_urgency_model_training` DAG from the Airflow UI

**Option 2: Manual execution**
```bash
docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"
```

## 📊 Model Details

- **Algorithm**: Logistic Regression with TF-IDF + OneHotEncoder
- **Features**: 
  - Text: Title + Description (TF-IDF)
  - Categorical: Source, Customer Tier
- **Target**: Urgency classification (urgent/non-urgent)
- **Metrics Tracked**: Accuracy, Precision, Recall, F1-score

## 🔄 Workflow

1. **Data Loading**: Reads from `data/raw/tickets.csv`
2. **Preprocessing**: Combines title + description, handles categorical features
3. **Training**: Trains logistic regression model
4. **Evaluation**: Computes metrics on train/validation/test sets
5. **Model Storage**: 
   - Saves locally to `models/ticket_urgency_model.pkl`
   - Uploads to GCS: `gs://ml-model-bucket-22/ticket_urgency_model/ticket_urgency_model.pkl`
6. **Tracking**: Logs metrics and parameters to MLflow

## 🔧 Configuration

### Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCP service account key
- `MLFLOW_TRACKING_URI`: MLflow server URL (default: `http://mlflow:5000/`)
- `GCS_BUCKET_NAME`: GCS bucket name (default: `ml-model-bucket-22`)

### GCS Configuration

Update bucket name in `scripts/train.py`:
```python
bucket_name = 'ml-model-bucket-22'  # Your bucket name
```

## 📝 Notes

- Models are automatically uploaded to GCS after training
- MLflow tracks all experiments and metrics
- Airflow runs training daily (configurable schedule)
- Service account key is required for GCS access

## 🔐 Security

- **Never commit** `service-acc-key.json` to git (already in `.gitignore`)
- Use environment variables for sensitive configuration in production
- Rotate service account keys regularly

## 📚 Next Steps

- Model serving API (FastAPI/Flask)
- CI/CD pipeline for automated deployments
- Model monitoring and drift detection
- A/B testing framework

See `DEPLOYMENT_ROADMAP.md` for detailed deployment guide.

## 👤 Author

**Meghana Kolhal**
- GitHub: [@meghanakolhal](https://github.com/meghanakolhal)

## 📄 License

This project is part of an MLOps portfolio demonstration.

## Reloading Model After Retraining

After retraining the model, reload it in the API without redeploying:

**Windows (PowerShell/Git Bash):**
```bash
curl.exe -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model -H "Content-Length: 0"
```

**Linux/Mac:**
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/reload-model -H "Content-Length: 0"
```

**Note:** Cloud Run requires a `Content-Length` header for POST requests. The `-H "Content-Length: 0"` flag satisfies this requirement.