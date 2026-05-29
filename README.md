# UniResolve

Unified Customer Complaint Communication Dashboard for Idea 2.0 Hackathon PS5.

## Demo Setup

```bash
cp backend/.env.example .env
docker-compose up --build
```

- Frontend dashboard: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Default demo API key: `dev-secret-key`

Run seed data before demo:

```bash
cd backend
python -m app.seed
cd ..
docker-compose up --build
```

## Manual Backend

```bash
cd backend
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

## Security

- API key protection on POST/action endpoints via `X-Api-Key`.
- `POST /complaints/ingest` rate limited to 60 requests/minute/IP.
- CORS origins restricted by `ALLOWED_ORIGINS`.
- Complaint text validation, channel allowlist, PII masking, and `.env` ignored.

## PS5 Feature Checklist

- [x] Unified omnichannel complaint ingestion.
- [x] PII masking before AI processing.
- [x] AI triage: category, severity, sentiment, key issue.
- [x] Duplicate detection and systemic alerts.
- [x] SLA tracking, breach detection, and escalation.
- [x] Agent 360-degree dashboard with draft response workflow.
- [x] SQLite persistence for demo reliability.
- [x] Root cause analysis endpoint.
- [x] Regulatory report JSON/CSV endpoint.
- [x] Trend analysis endpoint with AI summary fallback.

## Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/complaints/ingest` | Ingest and triage complaint |
| GET | `/complaints` | List complaints |
| GET | `/complaints/stats` | Dashboard metrics |
| GET | `/complaints/alerts` | Systemic complaint alerts |
| GET | `/complaints/sla-breached` | Breached SLA queue |
| POST | `/complaints/{id}/action` | Approve, escalate, or reject |
| POST | `/complaints/{id}/escalate` | Manual escalation |
| GET | `/complaints/root-cause` | AI root cause analysis |
| GET | `/complaints/reports/regulatory` | Regulatory report |
| GET | `/complaints/trends` | Trend analysis |
