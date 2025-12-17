# Fix: FastAPI ASGI Error in Cloud Run

## 🔴 Error You're Seeing

```
TypeError: FastAPI.__call__() missing 1 required positional argument: 'send'
```

## ✅ Root Cause

**FastAPI is an ASGI framework**, but the Dockerfile was trying to run it with **gunicorn as WSGI**. This causes a compatibility error.

- **WSGI** = Older Python web standard (for Flask, Django)
- **ASGI** = Newer async standard (for FastAPI, Starlette)
- **FastAPI requires ASGI server** (like uvicorn)

## ✅ Solution Applied

Changed the Dockerfile CMD from:
```dockerfile
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

To:
```dockerfile
CMD exec uvicorn app:app --host 0.0.0.0 --port $PORT
```

## 🚀 Next Steps

1. **Commit the fix**:
   ```bash
   git add api/Dockerfile
   git commit -m "Fix: Use uvicorn instead of gunicorn for FastAPI ASGI compatibility"
   git push origin main
   ```

2. **Wait for GitHub Actions** to rebuild and redeploy

3. **Test the endpoint**:
   ```bash
   curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/health
   ```

## 📝 Why This Happened

- Gunicorn is great for WSGI apps (Flask, Django)
- FastAPI uses ASGI and needs uvicorn (or gunicorn with uvicorn workers)
- For simplicity, uvicorn directly is the best choice for FastAPI

## 🔧 Alternative: Use Gunicorn with Uvicorn Workers

If you prefer gunicorn for production features, you can use:

```dockerfile
CMD exec gunicorn app:app --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker
```

But uvicorn directly is simpler and works perfectly for Cloud Run.

---

**After pushing the fix, your API should work!** ✅
