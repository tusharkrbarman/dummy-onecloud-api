# Dummy OneCloud API

Standalone FastAPI service that simulates a OneCloud-style hardware reservation API for CI validation workflows.

## Endpoints

```text
GET  /health
GET  /machines
POST /reservations
POST /machines/{machine_id}/deploy-image
GET  /deployments/{deployment_id}/status
POST /reservations/{reservation_id}/release
```

## Local Run

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
```

## Render

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```
