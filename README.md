# AI Tutor

Monorepo for the AI Tutor project.

## Structure
- `backend/` — FastAPI backend
- `frontend/` — UI
- `docs/` — notes and design docs

## Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload

## Frontend setup
cd frontend
npm install
npm run dev
