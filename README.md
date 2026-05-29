# UniResolve

Unified Customer Complaint Communication Dashboard built for **Idea 2.0 Hackathon - PS5**.

UniResolve brings customer complaints from multiple channels into one agent dashboard, masks sensitive PII, triages each complaint with AI, detects duplicate/systemic issues, tracks SLA risk, supports escalation, and generates analytics/reporting for compliance review.

## Why This Matters

Financial institutions receive complaints through email, web forms, social media, IVR/call center, branches, and mobile apps. Teams often lose time switching tools, manually redacting PII, assigning severity, finding repeated complaints, and preparing compliance reports.

UniResolve solves this with a single demo-ready workflow:

1. Ingest complaint from any supported channel.
2. Mask PII before AI processing.
3. Classify category, severity, sentiment, and key issue.
4. Generate an empathetic draft response.
5. Detect duplicates and systemic complaint clusters.
6. Track SLA deadline, at-risk status, breach, and escalation.
7. Give agents a 360-degree complaint view.
8. Export regulatory and trend reports.

## Demo Setup

### Docker Compose

```bash
cp backend/.env.example .env
docker-compose up --build
```

Open:

- Frontend dashboard: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Backend healthcheck: http://localhost:8000/health

Default local API key:

```text
dev-secret-key
```

The frontend sends this key for protected demo actions.

### Seed Data Before Demo

Run this once so the dashboard has realistic complaint records:

```bash
cd backend
python -m app.seed
cd ..
docker-compose up --build
```

The seed script creates 20 complaints across all 6 channels, multiple categories, severity levels, statuses, SLA states, and duplicate/systemic clusters.

### Manual Backend Run

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Then open `frontend/index.html` directly or serve it:

```bash
cd frontend
npx serve . -l 3000
```

## Environment Variables

All new secrets/config values live in `backend/.env.example`; do not commit a real `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `API_KEY` | `dev-secret-key` | Required in `X-Api-Key` for POST/action endpoints |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5000` | CORS allowlist |
| `ANTHROPIC_API_KEY` | empty | Enables Claude draft/root-cause/trend generation |
| `REDIS_URL` | `redis://localhost:6379` | Kept for Docker compatibility |
| `SIMILARITY_THRESHOLD` | `0.80` | Semantic duplicate threshold reference |
| `MAX_CLUSTER_DISTANCE` | `0.25` | Cluster distance reference |

## Architecture

```text
Frontend Dashboard
  |
  | HTTP / JSON
  v
FastAPI Backend
  |
  |-- API key auth + rate limiting
  |-- PII scrubber
  |-- FLAN-T5/rule fallback triage
  |-- Claude draft/analytics fallback
  |-- FAISS/SentenceTransformer duplicate detection fallback
  |-- SLA escalation monitor
  v
SQLite complaint store
```

## Repository Structure

```text
Uniresolve/
  backend/
    app/
      api/
        complaints.py          # REST endpoints
      models/
        complaint.py           # Pydantic schemas
      services/
        pii_scrubber.py        # PII masking
        triage.py              # FLAN-T5/rule triage + Claude draft fallback
        clustering.py          # FAISS duplicate/systemic detection fallback
        store.py               # SQLite persistence
      config.py                # Env config + SLA hours
      security.py              # API key dependency
      seed.py                  # Demo data generator
      main.py                  # FastAPI app + startup SLA monitor
    requirements.txt
    Dockerfile
  frontend/
    index.html                 # Agent dashboard
  docker-compose.yml
  README.md
```

## Backend Features

- API key authentication for protected POST/action routes.
- Rate limiting on `POST /complaints/ingest` at 60 requests/minute/IP.
- CORS allowlist via environment variable.
- Complaint text validation with 5000 character max and whitespace stripping.
- Channel allowlist: `email`, `web`, `social`, `ivr`, `branch`, `app`.
- Optional `channel_metadata` for channel-specific details.
- SQLite persistence at `backend/complaints.db`.
- SLA deadlines by severity:
  - critical: 2 hours
  - high: 8 hours
  - medium: 24 hours
  - low: 72 hours
- Background SLA breach monitor.
- Manual escalation endpoint.
- Claude-powered draft response, root-cause analysis, and trend summary when `ANTHROPIC_API_KEY` is set.
- Graceful fallbacks when ML/API dependencies are unavailable.

## Frontend Features

- Unified agent dashboard.
- Metric cards: Total, Pending, Resolved, Escalated, SLA Breached, Systemic Alerts.
- SLA badges:
  - green: hours left
  - amber: at risk
  - red: SLA breached
- Systemic alert banner for duplicate clusters.
- Complaint 360-degree modal:
  - masked/unmasked authorised toggle
  - triage result
  - editable AI draft
  - copy draft button
  - SLA countdown
  - approve/escalate/reject actions
  - communication/audit timeline
- Chart.js charts for trend, category, severity, and sparkline analytics.

## API Endpoints

Open dashboard endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service metadata |
| GET | `/health` | Healthcheck |
| GET | `/complaints` | List complaints |
| GET | `/complaints/{id}` | Complaint detail |
| GET | `/complaints/stats` | Dashboard metrics |
| GET | `/complaints/alerts` | Active systemic alerts |
| GET | `/complaints/sla-breached` | SLA breached complaints |
| GET | `/complaints/root-cause?category=&days=7` | Root cause analytics |
| GET | `/complaints/reports/regulatory?from_date=&to_date=&format=json` | JSON/CSV regulatory report |
| GET | `/complaints/trends?group_by=category&window=7d` | Trend data and summary |

Protected endpoints requiring `X-Api-Key`:

| Method | Endpoint | Description |
|---|---|---|
| POST | `/complaints/ingest` | Ingest, mask, triage, cluster, and store complaint |
| POST | `/complaints/{id}/action` | Approve, escalate, or reject |
| POST | `/complaints/{id}/escalate` | Manual escalation with agent note/reason |
| POST | `/complaints/{id}/reply` | Add agent reply/message |

Example protected request:

```bash
curl -X POST http://localhost:8000/complaints/ingest \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: dev-secret-key" \
  -d "{\"channel\":\"web\",\"complaint_text\":\"My loan EMI was debited twice.\"}"
```

## Regulatory Report

JSON:

```bash
curl "http://localhost:8000/complaints/reports/regulatory?format=json"
```

CSV:

```bash
curl -OJ "http://localhost:8000/complaints/reports/regulatory?format=csv"
```

Report includes:

- report period
- total complaints
- counts by channel/category/severity
- resolution stats
- SLA compliance
- top recurring issues

## Security

- `.env` and `*.db` are gitignored.
- No real secrets are committed.
- API key authentication protects write/action routes.
- CORS is configurable and not wildcard by default.
- Rate limiting reduces ingest abuse.
- PII is masked before AI triage.
- Frontend only shows unmasked text behind an authorised-view toggle for demo.

## Cloud Deployment Notes

The project is Docker-friendly and cloud-ready for a hackathon deployment.

Recommended fast deployment path:

1. Use Docker Compose or deploy backend/frontend as separate services.
2. Set env vars in the cloud provider:
   - `API_KEY`
   - `ANTHROPIC_API_KEY`
   - `ALLOWED_ORIGINS`
3. Point `ALLOWED_ORIGINS` to the deployed frontend URL.
4. Attach persistent storage if keeping SQLite.
5. For stronger production architecture, replace SQLite with Postgres.

SQLite is perfect for demo speed, but cloud platforms with ephemeral filesystems need a persistent volume or managed database.

## PS5 Feature Checklist

- [x] Unified omnichannel complaint ingestion
- [x] PII masking before AI processing
- [x] AI triage: category, severity, sentiment, key issue
- [x] Draft response generation
- [x] Duplicate detection and systemic alerting
- [x] SLA tracking and breach escalation
- [x] Agent 360-degree complaint view
- [x] Human-in-the-loop approve/escalate/reject flow
- [x] Root cause analysis
- [x] Regulatory reporting with CSV export
- [x] Trend analysis with summary
- [x] Docker Compose setup
- [x] Seed data for live demo

## Verification Performed

- Backend import smoke test passed.
- Uvicorn `/health` smoke test passed.
- `/complaints/stats` returned seeded dashboard metrics.
- Protected ingest endpoint returned `401` without API key and `200` with `X-Api-Key`.

## Team

Team Checkmates:

- Krisha Shah
- Janhavi Doijad
- Jhotika Raja
- Disha Gupta
