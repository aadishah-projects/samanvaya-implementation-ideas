# Samanvaya

Samanvaya is a health insurance financial reconciliation dashboard for Nepal.

## What is included

- FastAPI backend with SQLite storage
- React + Tailwind CSS frontend
- Reconciliation engine using Pandas + RapidFuzz
- Synthetic generator for 500-record demo data
- Dashboard, uploads, claims table, detail view, and SMS mock

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api` requests to `http://127.0.0.1:8000`.
