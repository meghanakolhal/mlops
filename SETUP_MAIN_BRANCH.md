# Setting Up Main Branch and Testing Workflow

## Current Situation

- ✅ You're on `training-pipeline` branch
- ✅ Workflow file is syntactically correct
- ⚠️ Workflow triggers only on `main` branch pushes
- ✅ You can also manually trigger via `workflow_dispatch`

---

## Option 1: Switch to Main Branch and Push (Recommended)

### Step 1: Check Current Status
```powershell
# Check current branch
git branch

# Check what files are untracked
git status
```

### Step 2: Switch to Main Branch
```powershell
# Switch to main branch
git checkout main

# If main doesn't exist locally but exists on remote
git checkout -b main origin/main

# Or create main from current branch
git checkout -b main
```

### Step 3: Add All New Files
```powershell
# Add all untracked files
git add .github/
git add api/
git add scripts/deploy_to_cloudrun.sh
git add scripts/monitor_model.py
git add DEPLOYMENT_ROADMAP.md
git add GITHUB_SETUP_GUIDE.md
git add QUICK_START.md

# Or add everything at once
git add .
```

### Step 4: Commit Changes
```powershell
git commit -m "Add CI/CD workflow with Artifact Registry, API service, and deployment scripts"
```

### Step 5: Push to Main
```powershell
# First time pushing main branch
git push -u origin main

# Subsequent pushes
git push origin main
```

### Step 6: Monitor GitHub Actions
1. Go to your GitHub repository
2. Click **Actions** tab
3. Watch the workflow run: "Deploy Model API to Cloud Run"
4. Check for any errors in the logs

---

## Option 2: Test Workflow Manually (Without Switching Branches)

You can manually trigger the workflow from any branch:

1. Go to GitHub → **Actions** tab
2. Click on **"Deploy Model API to Cloud Run"** workflow
3. Click **"Run workflow"** button (top right)
4. Select your branch (`training-pipeline`)
5. Click **"Run workflow"**

This will trigger the workflow even though you're not on `main` branch.

---

## Common Issues & Solutions

### Issue 1: "Workflow not triggering"
**Cause**: Workflow only triggers on `main` branch pushes  
**Solution**: 
- Push to `main` branch, OR
- Use manual trigger (`workflow_dispatch`)

### Issue 2: "Secret GCP_SA_KEY not found"
**Cause**: GitHub Secret not set  
**Solution**: 
- Go to Settings → Secrets → Actions
- Add `GCP_SA_KEY` with your service account JSON

### Issue 3: "Permission denied" when pushing to Artifact Registry
**Cause**: Service account lacks permissions  
**Solution**: Ensure service account has:
- Artifact Registry Writer
- Cloud Run Admin
- Service Account User

### Issue 4: "Image not found" during Cloud Run deployment
**Cause**: Image wasn't pushed successfully  
**Solution**: 
- Check Artifact Registry: `gcloud artifacts docker images list asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api`
- Verify image exists before deployment

---

## Quick Test Commands

### Before Pushing - Validate Locally
```powershell
# Test YAML syntax
python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"

# Check git status
git status

# Verify you're ready to commit
git diff --cached
```

### After Pushing - Verify Deployment
```powershell
# Check if workflow ran
# Go to GitHub Actions tab

# Check Artifact Registry images
gcloud artifacts docker images list asia-south1-docker.pkg.dev/ml-model-480910/ticket-urgency-repo/ticket-urgency-api

# Check Cloud Run service
gcloud run services describe ticket-urgency-api --region=asia-south1

# Get service URL
gcloud run services describe ticket-urgency-api --region=asia-south1 --format='value(status.url)'
```

---

## Recommended Workflow

1. ✅ **Test locally first** (training, API, Docker build)
2. ✅ **Add GitHub Secret** (`GCP_SA_KEY`)
3. ✅ **Switch to main branch**
4. ✅ **Commit and push**
5. ✅ **Monitor GitHub Actions**
6. ✅ **Verify deployment**

---

## Next Steps After Successful Deployment

1. Test the deployed API endpoint
2. Verify model loads from GCS
3. Test prediction endpoint
4. Set up monitoring DAG in Airflow
5. Create feature branches and test branch tagging
