# Fix Cloud Run Deployment Permission Error

## 🔴 Error You're Seeing

```
PERMISSION_DENIED: Permission 'iam.serviceaccounts.actAs' denied on service account 
760518165160-compute@developer.gserviceaccount.com
```

## ✅ Solution: Add "Service Account User" Role

Your service account needs the **"Service Account User"** role to deploy to Cloud Run.

### Option 1: Add Role via GCP Console (Easiest)

1. Go to [GCP Console → IAM & Admin → IAM](https://console.cloud.google.com/iam-admin/iam)
2. Find your service account: `airflow-sa@ml-model-480910.iam.gserviceaccount.com`
3. Click the **pencil icon** (Edit) next to it
4. Click **"+ ADD ANOTHER ROLE"**
5. Search for and select: **"Service Account User"**
6. Click **"SAVE"**

### Option 2: Add Role via gcloud CLI

```bash
# Set your project
gcloud config set project ml-model-480910

# Grant Service Account User role
gcloud projects add-iam-policy-binding ml-model-480910 \
  --member="serviceAccount:airflow-sa@ml-model-480910.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### Option 3: Use a Specific Service Account (Alternative)

Instead of using the default Compute Engine service account, you can specify your own service account in the Cloud Run deployment command.

---

## 📋 Complete List of Required Roles

Your service account (`airflow-sa@ml-model-480910.iam.gserviceaccount.com`) needs:

1. ✅ **Artifact Registry Writer** - To push Docker images
2. ✅ **Cloud Run Admin** - To deploy Cloud Run services
3. ✅ **Storage Admin** - To access GCS bucket (for model files)
4. ❌ **Service Account User** - **MISSING!** This is what's causing the error

---

## 🔑 Important: Does the Key File Change?

**NO!** The service account JSON key file (`service-acc-key.json`) does **NOT change** when you update IAM roles.

- **Key file** = Your credentials (like a password)
- **IAM roles** = Permissions (checked by GCP when you use the key)

You can keep using the same key file. Just update the roles in GCP Console.

---

## 🚀 After Adding the Role

1. **Wait 1-2 minutes** for IAM changes to propagate
2. **Re-run the GitHub Actions workflow** (or push a new commit)
3. The deployment should now succeed

---

## 🧪 Verify Permissions

```bash
# Check current roles for your service account
gcloud projects get-iam-policy ml-model-480910 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:airflow-sa@ml-model-480910.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

You should see:
- `roles/artifactregistry.writer`
- `roles/run.admin`
- `roles/storage.admin`
- `roles/iam.serviceAccountUser` ← **This one was missing!**

---

## 🔧 Alternative: Specify Service Account in Deployment

If you want to avoid the "actAs" permission, you can modify the workflow to use your service account directly:

```yaml
- name: Deploy to Cloud Run
  run: |
    IMAGE_URI="..."
    gcloud run deploy ${{ env.SERVICE_NAME }} \
      --image ${IMAGE_URI} \
      --service-account=airflow-sa@ml-model-480910.iam.gserviceaccount.com \
      --platform managed \
      --region ${{ env.REGION }} \
      ...
```

But the easier solution is to just add the "Service Account User" role.

---

## ✅ Quick Fix Summary

1. Go to GCP Console → IAM
2. Find `airflow-sa@ml-model-480910.iam.gserviceaccount.com`
3. Add role: **"Service Account User"**
4. Wait 1-2 minutes
5. Re-run GitHub Actions workflow
6. ✅ Deployment should work!
