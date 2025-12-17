# Quick Start Guide - Testing & Deployment

## 🎯 Quick Answers

### GCR vs Artifact Registry?
- **GCR (Google Container Registry)** = Older service (deprecated)
- **Artifact Registry** = Newer, recommended service ✅
- **We're using**: Artifact Registry (`ticket-urgency-repo`)

### What Changed?
1. ✅ GitHub Actions workflow now uses **Artifact Registry** (not GCR)
2. ✅ Images are tagged with **branch names** (e.g., `main`, `feature-branch`)
3. ✅ Updated deployment scripts to use Artifact Registry
4. ✅ Added comprehensive testing guides

---

## 🚀 Quick Testing Steps

### 1. Test Training Locally
```bash
docker compose up -d
docker compose exec airflow-scheduler bash -lc "MLFLOW_TRACKING_URI=http://mlflow:5000/ python /opt/airflow/scripts/train.py"
```

### 2. Test API Locally
```bash
cd api
pip install -r requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS=../service-acc-key.json
uvicorn app:app --reload --port 8000

# Test in another terminal
curl http://localhost:8000/health
```

### 3. Add GitHub Secret
1. Go to: GitHub Repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"**
3. Name: `GCP_SA_KEY`
4. Value: Copy entire contents of `service-acc-key.json`
5. Click **"Add secret"**

### 4. Push to Main & Test Workflow
```bash
git add .
git commit -m "Setup CI/CD with Artifact Registry"
git push origin main

# Check GitHub Actions tab for deployment status
```

---

## 📋 File Changes Summary

| File | What Changed |
|------|--------------|
| `.github/workflows/deploy.yml` | ✅ Uses Artifact Registry, tags with branch names |
| `scripts/deploy_to_cloudrun.sh` | ✅ Uses Artifact Registry, auto-detects branch |
| `DEPLOYMENT_ROADMAP.md` | ✅ Project-specific, clear local testing steps |
| `GITHUB_SETUP_GUIDE.md` | ✅ NEW: Complete setup guide |

---

## 🔍 Verify Everything Works

```bash
# 1. Check Artifact Registry images
gcloud artifacts docker images list \
  asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api

# 2. Check Cloud Run service
gcloud run services describe ticket-urgency-api --region=asia-south1

# 3. Test deployed API
SERVICE_URL=$(gcloud run services describe ticket-urgency-api \
  --region=asia-south1 --format='value(status.url)')
curl ${SERVICE_URL}/health
```

---

## 📚 Detailed Guides

- **GitHub Setup**: See `GITHUB_SETUP_GUIDE.md`
- **Deployment Roadmap**: See `DEPLOYMENT_ROADMAP.md`
- **Project Overview**: See `README.md`

---

## ⚠️ Important Notes

1. **Never commit** `service-acc-key.json` to git (already in `.gitignore`)
2. **Branch names** are automatically used as image tags
3. **Artifact Registry** location: `asia-south1-docker.pkg.dev`
4. **Repository name**: `ticket-urgency-repo`
5. **Image format**: `asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api:<branch-name>`
