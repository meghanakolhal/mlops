# Fix: Scikit-learn Version Mismatch Error

## 🔴 Error You're Seeing

```
ERROR:app:Prediction failed: 'ColumnTransformer' object has no attribute '_name_to_fitted_passthrough'
```

And warning:
```
InconsistentVersionWarning: Trying to unpickle estimator Pipeline from version 1.8.0 when using version 1.3.2
```

## ✅ Root Cause

**Version Mismatch**: 
- Model was **trained** with `scikit-learn 1.8.0`
- API is using `scikit-learn 1.3.2`
- The model file format changed between versions, causing incompatibility

## ✅ Solution Applied

Updated `api/requirements.txt` to use compatible scikit-learn version:

**Before:**
```
scikit-learn==1.3.2
```

**After:**
```
scikit-learn>=1.8.0
```

## 🚀 Next Steps

1. **Commit and push the fix**:
   ```bash
   git add api/requirements.txt
   git commit -m "Fix: Update scikit-learn version to match training environment (1.8.0+)"
   git push origin main
   ```

2. **Wait for GitHub Actions** to rebuild and redeploy (2-3 minutes)

3. **Test the prediction endpoint**:
   ```bash
   curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
     -H "Content-Type: application/json" \
     -d '{"title": "Server down", "description": "Production server is not responding", "source": "email", "customer_tier": "premium"}'
   ```

## 📝 Why This Happened

- Scikit-learn models are **version-sensitive**
- When you train with one version, you should use the **same or compatible version** for inference
- The `ColumnTransformer` internal structure changed between 1.3.2 and 1.8.0
- Using `>=1.8.0` ensures compatibility with models trained on 1.8.0+

## 🔧 Alternative: Retrain with Matching Version

If you prefer to keep the API on 1.3.2, you would need to:
1. Update training environment to use scikit-learn 1.3.2
2. Retrain the model
3. Upload new model to GCS

But updating the API version is easier and recommended.

## ✅ After Fix

The prediction endpoint should work correctly:
```json
{
  "prediction": "urgent",
  "confidence": 0.85,
  "model_version": "ticket_urgency_model/ticket_urgency_model.pkl"
}
```

---

**Push the fix and test again!** ✅
