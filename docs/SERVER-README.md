# Heimdall Server — Quick Reference

## 🖥️ Server Details

| | Value |
|---|---|
| **Server** | Dell PowerEdge R620 |
| **OS** | Ubuntu Desktop 26.04 LTS |
| **Hostname** | heimdall-server |
| **Username** | heimdall |

---

## 🌐 IP Addresses

| Service | IP | Access |
|---------|-----|--------|
| **iDRAC** (remote management) | `192.168.18.120` | Browser: http://192.168.18.120 |
| **Server SSH (LAN)** | `192.168.18.187` | `ssh heimdall@192.168.18.187` |
| **Server SSH (Tailscale)** | `100.113.79.103` | `ssh heimdall@100.113.79.103` |
| **Heimdall Dashboard (Tailscale)** | `100.113.79.103:8000` | http://100.113.79.103:8000/dashboard |

**iDRAC Login:** root / calvin

---

## 🔌 How to Connect

### SSH (main way)
```bash
ssh heimdall@192.168.18.187
```

### iDRAC Web (remote console, power control)
- URL: http://192.168.18.120
- Username: `root`
- Password: `calvin`

---

## 🌡️ Fan Control (R620 is loud!)

### Check Temperatures
```bash
sudo ipmitool sdr type temperature
```

### Set Fan Speed (manual)
```bash
# Disable auto control
sudo ipmitool raw 0x30 0x30 0x01 0x00

# Set speed (hex value)
sudo ipmitool raw 0x30 0x30 0x02 0xff 0x1E  # 30%
sudo ipmitool raw 0x30 0x30 0x02 0xff 0x28  # 40%
```

### Back to Auto (if temps rise)
```bash
sudo ipmitool raw 0x30 0x30 0x01 0x01
```

---

## 🧰 Essential Commands

| Task | Command |
|------|---------|
| Task manager | `htop` |
| Check IP | `ip addr` |
| Update system | `sudo apt update && sudo apt upgrade -y` |
| Check disk | `df -h` |
| Check memory | `free -h` |
| Reboot | `sudo reboot` |
| Shutdown | `sudo shutdown now` |

---

## 🐳 Docker Services

```bash
# Check running containers
docker ps

# Start all services
cd /opt/heimdall && docker compose up -d

# Check logs
docker compose logs -f
```

| Container | Image | Port | Status |
|---|---|---|---|
| `heimdall-postgres` | pgvector/pgvector:pg15 | 5432 | ✅ Running |
| `heimdall-ollama` | ollama/ollama:latest | 11434 | ✅ Running |
| `heimdall-redis` | redis:7-alpine | 6379 | ✅ Running |
| `heimdall-langfuse` | langfuse/langfuse:latest | 3001 | ⚠️ Restarting |

---

## 🤖 Heimdall API

```bash
# Start the API (port 8000)
cd /opt/heimdall && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000

# Dashboard UI
http://192.168.18.187:8000/dashboard

# API docs (Swagger)
http://192.168.18.187:8000/docs

# Health check
curl http://localhost:8000/health
```

### Available Models
| Model | Provider | Speed | Cost |
|---|---|---|---|
| `qwen3:1.7b` | Ollama (local) | ~12 tok/s | Free |
| `qwen3:8b` | Ollama (local) | ~4.6 tok/s | Free |
| `deepseek-flash` | DeepSeek API | ~1s | $0.14/M tokens |
| `deepseek-pro` | DeepSeek API | ~2s | $1.74/M tokens |
| `groq-llama4-scout` | Groq API | <1s | Free |
| `groq-llama3-70b` | Groq API | <1s | Free |

---

## 🧠 Vector Store (pgvector)

```bash
# Tables
vector_memory, vector_notes, vector_chat_summaries, vector_code_chunks

# Vector Explorer UI (port 7860)
http://192.168.18.187:7860
cd /opt/heimdall && source venv/bin/activate && uvicorn vector_explorer:app --host 0.0.0.0 --port 7860
```

---

## 📋 Current Status (May 10, 2026)

1. ✅ Ubuntu installed, SSH working
2. ✅ Docker Compose running (Postgres, Ollama, Redis)
3. ✅ Ollama with `qwen3:1.7b`, `qwen3:8b`, `nomic-embed-text`
4. ✅ PostgreSQL + pgvector (4 vector tables)
5. ✅ Heimdall FastAPI — `/chat`, `/memory`, `/health`, `/models`, `/dashboard`
6. ✅ Multi-provider LLM: Ollama + DeepSeek + Groq
7. ⬜ Markdown rendering in chat UI
8. ⬜ Tailscale remote access
9. ⬜ Paperless-ngx (optional)

See `PROGRESS.md` for full task breakdown.

---

## 🔧 Boot Keys (if needed)

| Key | Function |
|-----|----------|
| **F2** | BIOS Setup |
| **Ctrl+E** | iDRAC Setup |
| **F11** | Boot Manager |
| **F12** | One-time Boot Menu |

---

*Created: May 2026 | Heimdall Server is LIVE* 🚀
