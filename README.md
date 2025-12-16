# MLOps Ticket Urgency Model Training Pipeline

End-to-end MLOps pipeline for training and deploying a ticket urgency classification model.

## 🏗️ Architecture

- **Airflow**: Orchestrates daily model training workflows
- **MLflow**: Tracks experiments, metrics, and model versions
- **Google Cloud Storage (GCS)**: Stores trained models
- **Docker Compose**: Local development environment

## 📁 Project Structure

```
.
├── dags/                    # Airflow DAG definitions
│   └── train_model.py      # Training DAG
├── scripts/                 # Training and preprocessing scripts
│   ├── train.py            # Main training script
│   └── preprocess.py       # Data preprocessing
├── data/                    # Data directory
│   ├── raw/                # Raw data files
│   └── processed/          # Processed data files
├── models/                  # Trained models (local)
├── Dockerfile              # Airflow container image
└── docker-compose.yaml     # Local development setup
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

