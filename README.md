# AI Tutor

> A curriculum-grounded, adaptive AI tutor for school students (Classes 1–12).
> Built with FastAPI, Next.js, PostgreSQL + pgvector, and Ollama — 100% local, $0 per query.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

---

## What it does

Unlike a chatbot, this is a **real tutor**:

- **Knows the curriculum** — school → class → subject → book → chapter → section → concept
- **Knows the student** — mastery tracking, misconceptions, prerequisite gaps
- **Verifies math** — SymPy independently checks every equation
- **Teaches in 8 modes** — Teacher, Socratic, Hint, Practice, Doubt, Revision, Exam, Quiz
- **Remembers the conversation** — 8-turn context per session
- **Streams responses** — ChatGPT-style, token by token
- **Cites sources** — every answer includes chapter / section / page
- **Runs locally** — Ollama, no external API keys, no per-query cost

---

## Features

| Feature | Description |
|---|---|
| Curriculum DB | Structured school / class / subject / book / chapter / section tree |
| Concept graph | Prerequisites + misconceptions between learning objectives |
| RAG retrieval | Vector search over textbook chunks (pgvector) |
| Adaptive teaching | Routes student to prerequisites when gaps detected |
| SymPy verification | Independent math validation with green ✓ badge |
| 8 teaching modes | Teacher, Socratic, Hint, Practice, Doubt, Revision, Exam, Quiz |
| Streaming | Server-Sent Events (SSE) for real-time output |
| Teacher UI | Full web interface to build curriculum without code |
| Role-based access | student · teacher · parent · admin |
| 100% local | Ollama for LLM + embeddings. No OpenAI required. |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Student / Teacher UI                     │
│                    (Next.js 14 · React · Tailwind)            │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                       FastAPI Backend                         │
│                                                               │
│  Auth · Curriculum · Concepts · Tutor · Ingest · Teacher API  │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │ Diagnostic │  │   RAG      │  │   SymPy    │              │
│  │  Engine    │  │  Retriever │  │  Verifier  │              │
│  └────────────┘  └────────────┘  └────────────┘              │
│                                                               │
│  ┌────────────────────────────────────────────┐               │
│  │   Ollama (LLM: gpt-oss · Embed: nomic)     │               │
│  └────────────────────────────────────────────┘               │
└──────────┬───────────────────────┬───────────────────────────┘
           │                       │
    ┌──────▼──────┐         ┌──────▼──────┐
    │  PostgreSQL │         │    Redis    │
    │  + pgvector │         │             │
    └─────────────┘         └─────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.115 · SQLAlchemy 2.0 (async) · Alembic |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| LLM | Ollama (`gpt-oss:20b` / `llama3.2`) |
| Embeddings | Ollama (`nomic-embed-text`, 768-dim) |
| Math | SymPy 1.13 |
| Frontend | Next.js 14 · React 18 · TypeScript · Tailwind CSS |
| State | Zustand · TanStack Query |
| Auth | JWT (access + refresh) · bcrypt |
| Deployment | Docker · Docker Compose |

---

## Quick Start

### Prerequisites

- Docker Desktop
- Ollama installed and running ([download](https://ollama.com/download))

### 1. Clone and configure

```bash
git clone https://github.com/jiwansah/ai-tutor.git
cd ai-tutor

cp .env.example .env
# Edit .env — set SECRET_KEY (openssl rand -hex 32)
```

### 2. Pull models

```bash
ollama pull gpt-oss:20b        # ~13 GB, requires 16 GB free RAM
# or, for smaller machines:
ollama pull llama3.2            # ~2 GB

ollama pull nomic-embed-text    # ~275 MB, for embeddings
```

### 3. Start the stack

```bash
docker compose up --build -d
sleep 10
docker compose ps
```

All four containers should show **Up**.

### 4. Run migrations

```bash
docker compose exec backend alembic upgrade head
```

### 5. Create your first accounts

```bash
# Teacher
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"teacher@demo.com","password":"teacher123","full_name":"Demo Teacher","role":"teacher"}'

# Student
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"student@demo.com","password":"student123","full_name":"Demo Student","role":"student"}'
```

### 6. Open the app

| URL | Purpose |
|---|---|
| http://localhost:3000 | Student tutor |
| http://localhost:3000/teacher | Teacher dashboard |
| http://localhost:8000/docs | API docs (if `DEBUG=true`) |
| http://localhost:8000/health | Health check |

---

## First-time setup

1. Log in as `teacher@demo.com` → **Teacher Dashboard**
2. **Curriculum** → create School → Class → Subject → Book → Chapter → Section
3. Paste textbook text into the section → auto-embedded and searchable
4. **Concepts** → create concepts and link prerequisites
5. **Graph** → visual map of the concept DAG
6. Log in as `student@demo.com` → ask a question in the tutor

---

## Project Structure

```
ai-tutor/
├── backend/
│   ├── app/
│   │   ├── api/           # HTTP routes (v1)
│   │   ├── core/          # security, config
│   │   ├── db/            # SQLAlchemy models
│   │   ├── repositories/  # data access
│   │   ├── services/      # business logic
│   │   ├── prompts/       # LLM prompts per mode
│   │   └── main.py
│   ├── alembic/           # migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js routes
│   │   ├── components/    # React components
│   │   ├── hooks/         # custom hooks
│   │   └── lib/           # API client, store
│   └── Dockerfile
├── infra/
│   └── postgres/          # init SQL
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Teaching Modes

| Mode | Purpose |
|---|---|
| **Teacher** | Full explanation with worked example |
| **Socratic** | Guided questions, no direct answers |
| **Hint** | Graduated hints — one at a time |
| **Practice** | Generate Easy / Medium / Hard problems |
| **Doubt** | Direct, brief answer with citation |
| **Revision** | Quick recall of weak areas |
| **Exam** | Strict timed-assessment style |
| **Quiz** | 3 multiple-choice questions |

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| POST | `/api/v1/tutor/ask` | Ask tutor (JSON) |
| POST | `/api/v1/tutor/ask/stream` | Ask tutor (SSE stream) |
| POST | `/api/v1/tutor/answer` | Submit student answer |
| GET | `/api/v1/concepts/` | List concepts |
| GET | `/api/v1/concepts/diagnostic/{key}` | Prerequisite check |
| GET | `/api/v1/teacher/schools` | List schools (teacher) |
| POST | `/api/v1/teacher/sections/{id}/ingest` | Ingest content |
| GET | `/api/v1/teacher/graph` | Concept graph |
| GET | `/api/v1/dashboard/me/progress` | Student progress |

Full OpenAPI spec at `/docs` when `DEBUG=true`.

---

## Configuration

Key environment variables (`.env`):

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | 64-char random (required) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Postgres connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `LLM_BASE_URL` | `http://host.docker.internal:11434/v1` | Ollama or OpenAI URL |
| `LLM_API_KEY` | `ollama` | `ollama` for local, `sk-...` for OpenAI |
| `LLM_MODEL_MEDIUM` | `gpt-oss:20b` | Main model |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `EMBEDDING_DIM` | `768` | Vector dimension |

**Switching to OpenAI:** set `LLM_BASE_URL=` (empty), `LLM_API_KEY=sk-...`, `LLM_MODEL_MEDIUM=gpt-4o-mini`, then `docker compose restart backend`.

---

## Common Commands

```bash
docker compose up -d                    # Start
docker compose down                     # Stop (keeps data)
docker compose down -v                  # Stop + wipe data (careful!)
docker compose logs -f backend          # Live backend logs
docker compose build backend            # Rebuild after code change
docker compose exec backend bash        # Shell into backend
docker compose exec postgres psql -U tutor -d tutor   # DB shell
```

---

## Database Migrations

```bash
# Generate migration after changing models
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec backend alembic upgrade head

# View current revision
docker compose exec backend alembic current

# Rollback one migration
docker compose exec backend alembic downgrade -1
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend crashes on startup | `docker compose logs backend --tail=50` |
| `psycopg2 is not async` | Ensure `DATABASE_URL` starts with `postgresql+asyncpg://` |
| `email-validator is not installed` | Add `email-validator` to `pyproject.toml`, rebuild |
| `pgvector` NameError in migration | Add `import pgvector.sqlalchemy` to `script.py.mako` |
| `expected 768 dimensions, not 384` | `ALTER TABLE content_chunks ALTER COLUMN embedding TYPE vector(768);` |
| Ollama not reachable | Set `OLLAMA_HOST=0.0.0.0:11434` and restart Ollama |
| Port 5432 already in use | Change to `"5433:5432"` in `docker-compose.yml` |

---

## Roadmap

- [x] Curriculum DB + RAG with real embeddings
- [x] Socratic mode + multi-turn teaching
- [x] SymPy math verification
- [x] Streaming responses
- [x] Concept graph + prerequisite routing
- [x] Teacher authoring UI
- [ ] Voice tutor (Whisper + TTS)
- [ ] Handwriting OCR
- [ ] Parent dashboard
- [ ] Multilingual support (Hindi, Tamil, Telugu)
- [ ] Spaced repetition scheduling
- [ ] Mobile app (React Native)

---

## Contributing

Pull requests welcome. For major changes, open an issue first.

```bash
git checkout -b feature/your-feature
# make changes
git commit -m "feat: your feature"
git push origin feature/your-feature
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgements

Built with FastAPI, Next.js, pgvector, SymPy, and Ollama.