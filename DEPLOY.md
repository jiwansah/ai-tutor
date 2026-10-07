# Production Deployment Guide

Deploy AI Tutor to a Linux server (Ubuntu 22.04) with HTTPS in 15 minutes.

---

## Prerequisites

- Ubuntu 22.04 VPS (4 vCPU, 8 GB RAM, 80 GB SSD minimum)
- Domain name (e.g. `tutor.yourschool.com`)
- OpenAI API key **OR** Ollama on the server (for local LLM)

For Ollama on server: 16 GB RAM recommended for `gpt-oss:20b`, 4 GB for `llama3.2`.

---

## Step 1 — Provision the server

```bash
ssh root@YOUR_SERVER_IP

apt update && apt upgrade -y
Capt install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx git ufw

systemctl enable --now docker
```

-[B--

## Step 2 — Create a non-root user

C```ash
adduser tutor
usermod -aG docker tutor
su - tutor
```

---

## Step 3 — Configure the firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## Step 4 — Clone the project

```bash
git clone https://github.com/jiwansah/ai-tutor.git
cd ai-tutor
```

---

## Step 5 — Install Ollama (optional — skip if using OpenAI)

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama

# Make Ollama listen on all interfaces so Docker can reach it
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<EOF
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
sudo systemctl daemon-reload
sudo systemctl restart ollama

# Pull models
ollama pull llama3.2
ollama pull nomic-embed-text
```

---

## Step 6 — Configure `.env` for production

```bash
cp .env.example .env
nano .env
```

Set the following:

```env
ENV=production
DEBUG=false

SECRET_KEY=<paste output of: openssl rand -hex 32>

DATABASE_URL=postgresql+asyncpg://tutor:<STRONG_PW>@postgres:5432/tutor
POSTGRES_PASSWORD=<STRONG_PW>

REDIS_URL=redis://redis:6379/0

# --- Option A: Local Ollama ---
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama
LLM_MODEL_MEDIUM=llama3.2

# --- Option B: OpenAI ---
# LLM_PROVIDER=openai
# LLM_BASE_URL=
# LLM_API_KEY=sk-your-real-key
# LLM_MODEL_MEDIUM=gpt-4o-mini

EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://host.docker.internal:11434
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768

CORS_ORIGINS=["https://tutor.yourschool.com"]
```

---

## Step 7 — Add production override

Create `docker-compose.prod.yml`:

```yaml
services:
  postgres:
    restart: always
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  redis:
    restart: always

  backend:
    restart: always
    environment:
      ENV: production
      DEBUG: "false"
    ports:
      - "127.0.0.1:8000:8000"    # only reachable via nginx

  frontend:
    restart: always
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: https://tutor.yourschool.com/api/v1
```

---

## Step 8 — Build and start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Wait for healthy
sleep 15
docker compose ps
```

---

## Step 9 — Run migrations + seed admin

```bash
docker compose exec backend alembic upgrade head

# Create admin account
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourschool.com","password":"CHANGE_ME_NOW","full_name":"Admin","role":"admin"}'
```

---

## Step 10 — Configure nginx

```bash
sudo nano /etc/nginx/sites-available/ai-tutor
```

Paste:

```nginx
server {
    listen 80;
    server_name tutor.yourschool.com;

    client_max_body_size 20M;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/ai-tutor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 11 — Enable HTTPS

```bash
sudo certbot --nginx -d tutor.yourschool.com
```

Certbot auto-configures HTTPS and installs auto-renewal.

Verify:

```bash
sudo certbot renew --dry-run
```

---

## Step 12 — Verify

```bash
# Health
curl https://tutor.yourschool.com/api/v1/../health

# Open in browser
open https://tutor.yourschool.com
```

---

## Day-2 Operations

### Update to a new version

```bash
cd ~/ai-tutor
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose exec backend alembic upgrade head
```

### Backup database (daily cron)

```bash
mkdir -p ~/backups
cat > ~/backup.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y-%m-%d)
docker compose -f /home/tutor/ai-tutor/docker-compose.yml exec -T postgres \
  pg_dump -U tutor tutor | gzip > /home/tutor/backups/tutor-$DATE.sql.gz
find /home/tutor/backups -name "tutor-*.sql.gz" -mtime +30 -delete
EOF
chmod +x ~/backup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 3 * * * /home/tutor/backup.sh") | crontab -
```

### Restore from backup

```bash
gunzip -c ~/backups/tutor-2026-10-01.sql.gz | \
  docker compose exec -T postgres psql -U tutor tutor
```

### Monitor logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
journalctl -u nginx -f
```

### Restart after reboot

Add to `~/.bashrc` or set up systemd:

```bash
sudo tee /etc/systemd/system/ai-tutor.service > /dev/null <<EOF
[Unit]
Description=AI Tutor
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/tutor/ai-tutor
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml down
User=tutor
Group=tutor

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable ai-tutor
```

---

## Security Checklist

- [ ] `SECRET_KEY` is 64+ random chars, never in git
- [ ] Postgres port **not** exposed publicly (only internal)
- [ ] Redis port **not** exposed publicly
- [ ] Backend / frontend only bound to `127.0.0.1`
- [ ] HTTPS enforced (HTTP redirects)
- [ ] CORS restricted to your domain
- [ ] Rate limiting enabled
- [ ] Daily DB backups running
- [ ] `DEBUG=false` in production
- [ ] Admin password changed from default
- [ ] Firewall allows only SSH + HTTP + HTTPS
- [ ] Parental consent flow in place (for minors)
- [ ] Audit logs enabled

---

## Performance Tuning

For >100 concurrent students:

```bash
# Increase backend workers
docker compose exec backend uvicorn app.main:app --workers 4

# Or scale in docker-compose.prod.yml:
services:
  backend:
    deploy:
      replicas: 3
```

Add a Redis cache layer for common retrievals:

```python
# In rag_service.py
cached = await redis.get(f"rag:{query_hash}")
if cached:
    return json.loads(cached)
```

Consider moving embeddings to a dedicated service (BGE or OpenAI) if you outgrow Ollama throughput.

---

## Cost Estimate (1000 active students)

| Component | Monthly |
|---|---|
| VPS (4 vCPU, 8 GB) | $40 |
| Domain | $1 |
| SSL (Let's Encrypt) | $0 |
| Ollama (self-hosted) | $0 |
| **Total** | **~$41/month** |

With OpenAI `gpt-4o-mini` instead of Ollama, add ~$360/month for 1000 students averaging 20 questions/day.

---

## Support

For issues: open a GitHub issue at https://github.com/jiwansah/ai-tutor/issues
