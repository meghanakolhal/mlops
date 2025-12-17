# Test API Endpoints - Curl Commands

## 🌐 Your API URL
```
https://ticket-urgency-api-7j3n5753uq-el.a.run.app
```

---

## 1. Test Health Endpoint (GET)

```bash
curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "bucket": "ml-model-bucket-22",
  "model_path": "ticket_urgency_model/ticket_urgency_model.pkl"
}
```

---

## 2. Test Prediction Endpoint (POST)

### Basic Test
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Server down\", \"description\": \"Production server is not responding\", \"source\": \"email\", \"customer_tier\": \"premium\"}"
```

### Formatted (Easier to Read)
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Server down",
    "description": "Production server is not responding",
    "source": "email",
    "customer_tier": "premium"
  }'
```

**Expected Response:**
```json
{
  "prediction": "urgent",
  "confidence": 0.85,
  "model_version": "ticket_urgency_model/ticket_urgency_model.pkl"
}
```

---

## 3. Test Different Scenarios

### Urgent Ticket (Premium Customer)
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Critical system failure",
    "description": "Database is down and affecting all users",
    "source": "phone",
    "customer_tier": "premium"
  }'
```

### Non-Urgent Ticket
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Feature request",
    "description": "Can we add dark mode to the app?",
    "source": "web",
    "customer_tier": "standard"
  }'
```

### Email Source Ticket
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Password reset needed",
    "description": "I forgot my password and need to reset it",
    "source": "email",
    "customer_tier": "standard"
  }'
```

---

## 4. Test Root Endpoint

```bash
curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/
```

**Expected Response:**
```json
{
  "message": "Ticket Urgency Prediction API",
  "endpoints": {
    "health": "/health",
    "predict": "/predict",
    "docs": "/docs"
  }
}
```

---

## 5. View API Documentation

Open in browser:
```
https://ticket-urgency-api-7j3n5753uq-el.a.run.app/docs
```

Or test with curl:
```bash
curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/docs
```

---

## 6. PowerShell Commands (Windows)

### Health Check
```powershell
Invoke-RestMethod -Uri "https://ticket-urgency-api-7j3n5753uq-el.a.run.app/health" -Method Get
```

### Prediction
```powershell
$body = @{
    title = "Server down"
    description = "Production server is not responding"
    source = "email"
    customer_tier = "premium"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict" -Method Post -Body $body -ContentType "application/json"
```

---

## 7. Python Test Script

```python
import requests

API_URL = "https://ticket-urgency-api-7j3n5753uq-el.a.run.app"

# Test health
response = requests.get(f"{API_URL}/health")
print("Health Check:", response.json())

# Test prediction
data = {
    "title": "Server down",
    "description": "Production server is not responding",
    "source": "email",
    "customer_tier": "premium"
}
response = requests.post(f"{API_URL}/predict", json=data)
print("Prediction:", response.json())
```

---

## 8. Valid Field Values

### `source` field:
- `"email"`
- `"phone"`
- `"web"`

### `customer_tier` field:
- `"premium"`
- `"standard"`

### `title` and `description`:
- Any text strings

---

## 9. Error Handling

If you get an error, check:

1. **Model not loaded**:
   ```json
   {
     "detail": "Model loading failed: ..."
   }
   ```
   → Model file might not exist in GCS

2. **Invalid input**:
   ```json
   {
     "detail": [
       {
         "loc": ["body", "source"],
         "msg": "field required"
       }
     ]
   }
   ```
   → Missing required fields

3. **500 Internal Server Error**:
   → Check Cloud Run logs for details

---

## Quick Copy-Paste Commands

### Health Check:
```bash
curl https://ticket-urgency-api-7j3n5753uq-el.a.run.app/health
```

### Prediction (One-liner):
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict -H "Content-Type: application/json" -d "{\"title\": \"Server down\", \"description\": \"Production server is not responding\", \"source\": \"email\", \"customer_tier\": \"premium\"}"
```

### Prediction (Multi-line, easier):
```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"title": "Server down", "description": "Production server is not responding", "source": "email", "customer_tier": "premium"}'
```



```bash
curl -X POST https://ticket-urgency-api-7j3n5753uq-el.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Application running slow",
    "description": "Report export stuck at 80 percent for several minutes.",
    "source": "web",
    "customer_tier": "Gold"
  }'
```  