# UniResolve 🏦


---

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
docker-compose up --build
```
- **Frontend Dashboard:** http://localhost:3000
- **Backend API Docs:** http://localhost:8000/docs

---

### Option 2: Manual Setup

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
# Open index.html directly in browser, OR:
npx serve .                     # serves at http://localhost:5000
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              DATA INGESTION LAYER                        │
│  Email / Social / Call / Branch / Web / App             │
│  FastAPI Gateway → PII Masking (SpaCy NER) → Redis      │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│              AI TRIAGE PIPELINE                          │
│  FLAN-T5-Base → Category / Severity / Sentiment          │
│  Key Issue Extraction → Draft Response Generation        │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│           SEMANTIC CLUSTERING (FAISS)                    │
│  Sentence-BERT → Vector Embeddings → FAISS Index         │
│  Duplicate Detection → Systemic Alert if cluster ≥ 5    │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│         AGENT DASHBOARD (Human-in-the-Loop)              │
│  Next.js / HTML → View triage → Approve / Escalate       │
│  AI draft shown as "suggestion" — agent validates        │
└─────────────────────────────────────────────────────────┘
```

## 📂 Project Structure
```
uniresolve/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── complaints.py      # REST endpoints
│   │   ├── models/
│   │   │   └── complaint.py       # Pydantic schemas
│   │   ├── services/
│   │   │   ├── pii_scrubber.py   # PII masking
│   │   │   ├── triage.py         # FLAN-T5 NLP
│   │   │   ├── clustering.py     # FAISS dedup
│   │   │   └── store.py          # In-memory DB
│   │   └── main.py               # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── index.html                 # Agent dashboard
└── docker-compose.yml
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/complaints/ingest` | Ingest new complaint |
| GET | `/complaints` | List all (with filters) |
| GET | `/complaints/{id}` | Complaint detail |
| POST | `/complaints/{id}/action` | Approve/Escalate/Reject |
| GET | `/complaints/stats` | Dashboard statistics |
| GET | `/complaints/alerts` | Active systemic alerts |

## 🛠️ Tech Stack
- **Backend:** FastAPI + Uvicorn + Redis
- **AI/NLP:** FLAN-T5-Base, Sentence-BERT (all-MiniLM-L6-v2)
- **Vector DB:** FAISS (FlatIP index)
- **PII Masking:** Regex + SpaCy NER
- **Frontend:** HTML5 + Chart.js
- **Container:** Docker + Docker Compose
- **Database:** PostgreSQL (prod) / In-memory (demo)

## 👥 Team Checkmates
| Member | Expertise |
|--------|-----------|
| Krisha Shah | AI/ML, Python |
| Janhavi Doijad | Full Stack & Database |
| Jhotika Raja | Backend & DBMS |
| Disha Gupta | Full Stack & Quantum Physics |
