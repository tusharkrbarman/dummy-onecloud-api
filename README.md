# Dummy OneCloud API

Standalone FastAPI service that simulates a OneCloud-style hardware reservation API for CI validation workflows.

## Endpoints

```text
GET  /health
GET  /machines
GET  /machines/{machine_id}
GET  /reservations
POST /reservations
GET  /reservations/{reservation_id}
POST /machines/{machine_id}/deploy-image
GET  /deployments
GET  /deployments/{deployment_id}/status
POST /reservations/{reservation_id}/release
```

The API maintains in-memory state while the service is running:

- Creating a reservation changes the machine from `available` to `reserved`.
- Image deployment is allowed only after the machine is reserved.
- Deployment status moves from `IN_PROGRESS` to `READY` after polling.
- Releasing a reservation changes the machine back to `available`.

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
