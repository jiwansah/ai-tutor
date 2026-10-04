# 1. Copy env
cp .env.example .env
# Edit .env with your keys

# 2. Start everything
docker compose up --build

# 3. Create first migration (dev)
docker compose exec backend alembic revision --autogenerate -m "initial"
docker compose exec backend alembic upgrade head

# 4. Seed a school + class + subject + book + chapter + section
# (via ingest API or a seed script)

# 5. Open
# Frontend: http://localhost:3000
# Backend docs: http://localhost:8000/docs (if DEBUG=true)
