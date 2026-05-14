# Heimdall — Personal AI System
### Development Planning Document
*Revised Architecture: May 2026*
*Retrieval Engine: pgvector (PostgreSQL) — LanceDB removed due to AVX2 incompatibility on R620*

---

> **How to use this document**
> Every task is 30–60 minutes. Each ends with a structured checkpoint block. Work in order within each phase. Don't move on until the checkpoint passes. Build slowly, test constantly, layer complexity.
>
> Every task follows this format:
> **Goal → Steps → Expected Result → Test Method → Rollback Plan → ✅ Checkpoint**

---

# Naming

The system is called **Heimdall**.

Use this name consistently across: dashboard, CLI, voice, logs, branding, commit messages.

> *"Heimdall is indexing Saferoute..."*
> *"Ask Heimdall about your morning."*

**Wake word (future):** "Hey Heimdall" — short, clear, not confused with common words.

**Stupid acronym justification:** HEIMDALL stands for **H**yper-**E**nhanced **I**ntelligent **M**achine **D**ata **A**nalysis & **L**ogistics **L**ayer. Yes, it's ridiculous — that's the point. It sounds vaguely technical while being completely over-engineered for a personal assistant, which perfectly matches the project's ethos of building enterprise-grade infrastructure for personal productivity.

**Voice persona name options** (if you want a human name for the TTS voice):

| Name | Notes |
|---|---|
| **Nora** | Top pick — easy wake word, natural in speech, not sci-fi |
| **Clara** | Clean, professional |
| **Iris** | Short, distinct |
| **Ada** | Tech-adjacent, memorable |
| **Evelyn** | Warm, natural |

Default: use **Heimdall** for the system, **Nora** as the voice persona name if/when you add TTS.

---

# Architecture

## Full System Architecture

```
iPhone / Browser (PWA)
        ↓ HTTPS
Next.js Dashboard (Vercel)
        ↓
Auth Layer (JWT)
        ↓
Cloudflare Tunnel
        ↓
FastAPI Gateway
        ↓
Capability Planner
        ↓
Task Queue (Dramatiq + Redis)
   ├── LLM Router
   ├── Retrieval Engine (pgvector)
   ├── Tool Execution Layer
   ├── Memory System
   └── Background Workers
          ├── Ingestion Worker
          ├── Embedding Worker
          ├── Summariser Worker
          └── Indexing Worker
        ↓
Model Services
   ├── Ollama (local — Qwen3.5)
   ├── DeepSeek V4-Flash / V4-Pro
   ├── Gemini 2.5 Flash (vision)
   ├── Claude Sonnet 4.6 (code)
   ├── Groq (ultra-fast voice responses)
   └── OpenRouter :free (overflow)
        ↓
Tool Services
   ├── Google Maps / TfL APIs
   ├── Paperless-ngx (OCR + archive)
   ├── n8n (automation + notifications)
   ├── Garmin Connect / Apple Health
   └── VSCode Connector Service
        ↓
Data Layer
   ├── PostgreSQL (structured system state)
   ├── pgvector (semantic embeddings + retrieval in PostgreSQL)
   ├── Obsidian Vault (Markdown: wiki, journal, goals, budget, study)
   ├── Paperless Archive (documents + OCR)
   └── Object Storage (files, exports)
```

## VSCode Connector Architecture

```
Web Dashboard (mobile/desktop)
        ↓
Agent Orchestrator API
        ↓
Task Queue
        ↓
VSCode Connector Daemon (persistent, per machine)
        ↓
VSCode Extension (workspace operations)
        ↓
Local Workspace + Local Models
```

## VSCode Extension Responsibilities

The extension runs inside VSCode on each connected machine. It is the execution layer — the daemon calls into it.

**Workspace Sync**
- Detects repo changes (file saves, git events)
- Updates the project index in real time
- Syncs metadata to Atlas machine registry

**File Operations**
- Read files (for context and analysis)
- Patch files (line-range diffs)
- Overwrite files (full replacement)
- Create and delete files

**Terminal Execution**
- Run tests (`pytest`, `jest`, etc.)
- Run builds (`npm run build`, `cargo build`)
- Run scripts and arbitrary shell commands
- Execute git commands

**Git Operations**
- Stage and commit
- Create branches
- Push to remote
- PR creation (future)

All operations respect the active **Permission Mode** — the extension will not execute anything above the current trust level without confirmation.

---

```
atlas/
├── api/
│   ├── chat.py
│   ├── auth.py
│   ├── memory.py
│   ├── study.py
│   ├── maps.py
│   ├── health.py
│   ├── goals.py
│   ├── tasks.py
│   └── files.py
│
├── core/
│   ├── planner.py          # Capability planner (replaces simple classifier)
│   ├── router.py           # Model selection + dispatch
│   ├── retrieval.py        # LanceDB semantic search
│   ├── memory_manager.py   # Hierarchical memory
│   ├── permissions.py      # Tool permission levels
│   ├── embeddings.py       # Embedding pipeline
│   └── config.py           # Startup validation
│
├── services/
│   ├── ollama_service.py
│   ├── deepseek_service.py
│   ├── gemini_service.py
│   ├── paperless_service.py
│   └── maps_service.py
│
├── workers/
│   ├── ingestion_worker.py
│   ├── embedding_worker.py
│   ├── summariser_worker.py
│   └── indexing_worker.py
│
├── vscode/
│   ├── connector_daemon.py     # Persistent WS connection per machine
│   ├── machine_registry.py     # Machine ID, state, capabilities
│   └── extension/              # VSCode extension source
│
└── db/
    ├── postgres.py
    └── models.py
```

---

# API & Model Reference

## Local (Free, Always On)
| Model | Tool | Use Case |
|---|---|---|
| Qwen3.5:7b | Ollama | Routing, quick Q&A, simple tasks |
| Qwen3.5:32b | Ollama (post RTX 3090 build) | Most PA tasks |
| nomic-embed-text | Ollama | Local embeddings for pgvector |
| Whisper | Local binary | Speech-to-text |

## Cloud (Pay Per Use)
| Model | API | Use Case | Cost |
|---|---|---|---|
| DeepSeek V4-Flash | api.deepseek.com | Writing, docs, journal, budget | $0.14/M in, $0.28/M out |
| DeepSeek V4-Pro | api.deepseek.com | Complex reasoning, long docs | $1.74/M in, $3.48/M out |
| Gemini 2.5 Flash | Google AI Studio | Vision, photo reading, receipts | Free: 1,500 req/day |
| Claude Sonnet 4.6 | api.anthropic.com | Code generation | $3/M in, $15/M out |
| Groq (Llama 4 Scout) | groq.com | Ultra-fast voice responses | Free: 14,400 req/day |
| OpenRouter :free | openrouter.ai | Free overflow | Free (rate limited) |

## Specialist APIs
| Service | Use Case | Cost |
|---|---|---|
| Google Maps Directions | Journey time, routes | Free: 10k req/mo |
| Google Route Optimization | Drop-off solver, multi-stop | Pay per use |
| TfL Unified API | Live bus/tube (London) | Free |
| OpenWeatherMap | Morning brief weather | Free: 1k req/day |
| Google Calendar API | Schedule access | Free |
| Garmin Connect (python-garminconnect) | Steps, sleep, HRV, Body Battery | Free (personal) |
| Apple HealthKit | Health data via iOS Shortcut bridge | Free |
| Langfuse (self-hosted) | Prompt tracing, cost tracking, latency | Free |

## Capability Planner (replaces simple classifier)

The original `simple/writing/code` classifier is replaced with a planner that returns a list of required capabilities per request:

```json
{
  "capabilities": ["retrieval", "maps", "calendar"],
  "primary_model": "deepseek/v4-flash",
  "tools": ["get_directions", "get_calendar_events"],
  "requires_confirmation": false,
  "reasoning": "User needs journey info and schedule context"
}
```

This enables one message to trigger multiple tools in sequence, and allows pre-fetching relevant memory before calling any model.

## Permission Levels
| Level | Can Do | Cannot Do |
|---|---|---|
| `SAFE` | Read, analyse, suggest | Write files, push, deploy, delete |
| `CONFIRM_REQUIRED` | Commit, send messages, write files | Deploy, run migrations |
| `TRUSTED` | Commit, push, run terminal | Merge, run migrations |
| `AUTONOMOUS` | Deploy, merge, run migrations | Nothing blocked |

Default mode: `CONFIRM_REQUIRED`. Configurable per session from dashboard.

## Safety Mode Reference

| Mode | Reads | Edits Files | Commits | Pushes | Deploys | Migrations |
|---|---|---|---|---|---|---|
| **Safe** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Trusted** | ✅ | ✅ | ✅ | ✅ | ⚠️ confirm | ❌ |
| **Autonomous** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Use **Safe** for analysis and review sessions. Use **Trusted** for active development. Only enable **Autonomous** for well-tested, scoped tasks with a clear rollback plan.

## Task Approval Modes (Dashboard)

Configurable per session from the dashboard control panel:

| Mode | Behaviour |
|---|---|
| **Auto Approve** | Atlas executes without confirmation. Fastest, least safe. |
| **Ask Before Edit** | Confirm before any file is modified. |
| **Ask Before Push** | Edits are silent; confirm before git push. |
| **Ask Before Deploy** | All code changes silent; confirm before any deploy/migration. |

Default: **Ask Before Push**. Shown in dashboard header. Changeable mid-session.

---

# Retrieval & Memory Architecture

## Semantic Retrieval (LanceDB)

Four tables:
- `memory` — general facts and context
- `notes` — Obsidian vault content
- `chat_summaries` — compressed conversation history
- `code_chunks` — indexed project code

Each entry stores: `text`, `embedding` (768-dim vector from nomic-embed-text), `source_type`, `source_path`, checksum, timestamp.

## Retrieval Hierarchy (compresses context while improving relevance)

```
Layer 1 → Task / chat summaries          (most compressed, checked first)
Layer 2 → Project summaries
Layer 3 → Folder summaries
Layer 4 → File / note summaries
Layer 5 → Raw code chunks / text         (most detailed, last resort)
```

## Hierarchical Memory Types

| Type | What it stores | Lifespan |
|---|---|---|
| Working memory | Current conversation context | Session only |
| Episodic memory | Summarised past conversations | Persistent |
| Semantic memory | Facts, entities, relationships | Persistent |
| Short-term memory | Recent events, last 24h activity | Rolling window |

## Entity Graph

Tracked: people, projects, locations, recurring goals, organisations.
Relationships stored in PostgreSQL.
Example query: *"What projects involve James?"* → returns all tasks, notes, and conversations tagged with entity `James`.

---

# Project Indexing System

## Indexed Per File
- Path, language, framework
- Symbols: classes, functions, exports, imports
- Git branch + last modified timestamp
- Embedding of code chunk

## Auto-Generated Summaries
- File summary: what this file does (1–2 sentences)
- Folder summary: role of this directory
- Project summary: high-level what the repo does
- Task summaries: what was done, what changed
- Chat summaries: decisions, entities, outcomes

These summaries form Layers 1–4 of the retrieval hierarchy.

## Machine Registry

Each connected machine registers:
```json
{
  "machine_id": "desktop-rtx",
  "state": "online",
  "toolchains": ["node", "python", "rust"],
  "active_repos": ["saferoute", "atlas-dashboard"],
  "available_models": ["qwen3.5:32b"],
  "gpu": "RTX 3090 24GB",
  "cpu": "Ryzen 5 5600X"
}
```

Atlas dispatches tasks to the most capable available machine.

---

# Streaming

**Without streaming:** Wait 8 seconds → full response arrives at once.

**With streaming:** Tokens appear as they generate — feels dramatically faster.

## Stream Event Types
- `token` — model output token
- `file_read` — Atlas read a file
- `file_edit` — Atlas patched a file
- `terminal_log` — command output
- `test_result` — pass/fail from test runner
- `git_commit` — commit made
- `error` — failure with context
- `done` — task complete

## Transport
- Phase 3B: SSE (Server-Sent Events) — simpler, works in all browsers
- Later: WebSockets for bidirectional streaming (live task logs, voice)

---

# Wake Word (Future Phase)

```
Microphone (always on, local)
  ↓
Wake word detection (Porcupine / Picovoice — CPU only)
  ↓
Speech-to-text (Whisper local)
  ↓
Capability Planner
  ↓
Response (TTS — Kokoro local or ElevenLabs)
```

Not built until Phase 7+. Architecture accommodates it from day one.

---

# Obsidian Vault Structure

```
atlas-vault/
├── journal/          # Daily auto-drafts + your edits
├── goals/            # SMART goals as Markdown with frontmatter
├── wiki/             # General knowledge, LLM-compiled
├── life-docs/        # Important document summaries
├── budget/           # Rules, records, monthly snapshots
├── study/            # Flashcard decks + quiz state JSON
├── maps/             # Saved locations
├── health/           # Daily health summaries
├── meetings/         # Pre-meeting briefs
└── inbox/            # Drop zone — LLM processes and files automatically
```

---

# Monthly Running Cost

| Item | Cost |
|---|---|
| Vercel (dashboard) | Free |
| Cloudflare Tunnel | Free |
| DeepSeek API (personal use) | ~£1–3 |
| Google Maps API (light use) | Free tier |
| Gemini API (free tier) | Free |
| OpenWeatherMap | Free |
| Groq (free tier) | Free |
| Langfuse (self-hosted) | Free |
| Electricity (spare PC running) | ~£3–5 |
| Claude Pro (VSCode + Remote Control) | £16/mo optional |
| **Total without Claude Pro** | **~£4–8/mo** |
| **Total with Claude Pro** | **~£20–24/mo** |

---

# Dell PowerEdge R620 Server Setup Guide

## Initial Hardware Setup

**What you'll need:**
- Server + power cables (should come with it)
- Monitor + HDMI/DisplayPort cable (for initial setup)
- Keyboard + mouse
- Ethernet cable
- USB drive (8GB+) for OS installation

**Step 1: Physical Setup**
1. Connect server to power (both PSUs if you have dual power supplies)
2. Connect monitor to server's video output (R620 has VGA on the iDRAC or dedicated GPU card)
3. Connect keyboard and mouse
4. Connect Ethernet to your router/switch
5. Power on the server

**Step 2: Access BIOS/iDRAC**
- Press **F2** during boot for BIOS setup
- Press **Ctrl+E** for iDRAC setup (remote management)
- iDRAC IP configured: **192.168.18.120** (matches your PC's 192.168.18.x network)

## OS Installation

**Recommended OS: Ubuntu Server 22.04 LTS** (standard install, NOT minimal)
- Free, stable, excellent documentation
- Great Docker support
- Large package repository
- Long-term support until 2027
- **Why not minimal?** The R620 has plenty of RAM/storage. Standard install includes useful tools (curl, vim, net-tools) that make setup easier.

**Alternative: Proxmox VE 8.0**
- If you want to run multiple VMs
- Built-in virtualization platform
- Web-based management
- Can still run Docker in LXC containers

**Ubuntu Server Installation Steps:**
1. Download Ubuntu Server 22.04 LTS ISO
2. Create bootable USB drive (Rufus on Windows, `dd` on Linux)
3. Boot from USB (may need to change boot order in BIOS)
4. Follow installer:
   - Choose "Install Ubuntu Server"
   - Set hostname: `heimdall-server`
   - Create user: `heimdall` (or your username)
   - Enable SSH server (important!)
   - Install OpenSSH server
   - No additional packages needed initially

**Post-Installation Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git vim htop docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Enable SSH key-based auth (copy your SSH key)
ssh-copy-id heimdall@<server-ip>
```

## Remote Access Setup

**Method 1: SSH (Recommended for daily use)**
```bash
# From your main machine
ssh heimdall@<server-ip>
```

**Method 2: iDRAC Web Interface**
- Open browser to iDRAC IP: `http://192.168.18.120`
- Login with default credentials (root/calvin unless changed)
- Gives you remote console, power management, hardware monitoring
- iDRAC IP configured to match your network (192.168.18.x subnet)

**Method 3: Tailscale (Easy remote access)**
```bash
# On server
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# On your main machine
tailscale up
# Now you can SSH to heimdall@<tailscale-ip>
```

## Server Configuration for Heimdall

**Docker Setup (Recommended)**
```bash
# Install Docker Compose
sudo apt install docker-compose-plugin

# Create heimdall directory
mkdir -p /opt/heimdall
cd /opt/heimdall

# Create docker-compose.yml for services
# (See Phase 1A tasks for specific services)
```

**Performance Tuning**
```bash
# Check CPU cores and RAM
nproc
free -h

# Set up swap if needed (for heavy workloads)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Network Configuration**
- Static IP recommended for server
- Configure in `/etc/netplan/01-netcfg.yaml` (Ubuntu 22.04)
- Or set up in your router's DHCP reservation

## Hardware Specs to Expect

**Dell PowerEdge R620 Typical Configuration:**
- CPU: Dual Intel Xeon E5-2600 series (8-16 cores total)
- RAM: 32GB-128GB DDR3 ECC
- Storage: 8x 2.5" drive bays (SAS/SATA)
- Network: 4x 1GbE ports
- Management: iDRAC 7 Enterprise
- Power: Dual 750W PSUs

**What this means for Heimdall:**
- Plenty of CPU for embedding and processing
- ECC RAM perfect for data integrity
- Multiple drives for redundant storage (RAID)
- Network ports for services and redundancy

---

# Hardware Upgrade Path

| Stage | Hardware | Runs Locally |
|---|---|---|
| ✅ Current | **Dell PowerEdge R620** (Dual Xeon E5-2600, 32GB+ DDR3 ECC) | Qwen3.5:7b–13b, all services, cloud API fallback |
| Next | Add GPU or upgrade to GPU server | Qwen3.5:32b, fast inference, vLLM-ready |
| Target | RTX 3090 24GB, 64GB RAM, Ryzen 5 5600X | Full local inference, always-on voice, local TTS |

**Current Server:** Dell PowerEdge R620
- Dual Intel Xeon E5-2600 series (8–16 cores)
- 32GB–128GB DDR3 ECC RAM
- iDRAC 7 Enterprise remote management (IP: 192.168.18.120)
- 8x 2.5" drive bays, dual PSU

Architecture is fully compatible across all tiers. No rebuilding needed when upgrading.
Deferred until GPU build: Qwen3.5:32b, large embeddings, always-on voice, local TTS.

---

---

# PHASE 1A — Robust Foundation
*Goal: Proper database, vector search, document pipeline, async server. The right base.*

---

## Task 1A.1 — Install PostgreSQL

**Goal:** Replace SQLite with a proper relational database supporting future multi-user, multi-machine, and complex queries.

**Steps:**
```bash
# Linux
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql && sudo systemctl enable postgresql

# Create DB and user
sudo -u postgres psql
CREATE DATABASE atlas;
CREATE USER atlas_user WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE atlas TO atlas_user;
\q

# Python libraries
pip install sqlalchemy psycopg[binary] asyncpg alembic python-dotenv
```

Add to `.env`:
```env
DATABASE_URL=postgresql+asyncpg://atlas_user:your-password@localhost/atlas
DATABASE_URL_SYNC=postgresql+psycopg://atlas_user:your-password@localhost/atlas
```

Test connection:
```python
# test_db.py
import asyncio, asyncpg

async def test():
    conn = await asyncpg.connect("postgresql://atlas_user:your-password@localhost/atlas")
    print(await conn.fetchval("SELECT version()"))
    await conn.close()

asyncio.run(test())
```

**Expected Result:** PostgreSQL version string printed.

**Test Method:** `python test_db.py` — no errors, version printed.

**Rollback Plan:** Revert `DATABASE_URL` to `sqlite+aiosqlite:///atlas.db`. SQLite still works for early phases.

✅ **Checkpoint:** `python test_db.py` prints PostgreSQL version without errors.

---

## Task 1A.2 — Create SQLAlchemy Models

**Goal:** Define all database tables. One migration creates the full schema.

**Steps:**

Create `atlas/db/models.py`:
```python
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy import String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String, default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    subtasks: Mapped[dict] = mapped_column(JSON, default=list)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    linked_chat_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String)
    source_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UsageLog(Base):
    __tablename__ = "usage_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    model: Mapped[str] = mapped_column(String)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    task_type: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Machine(Base):
    __tablename__ = "machines"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    state: Mapped[str] = mapped_column(String, default="offline")
    toolchains: Mapped[list] = mapped_column(JSON, default=list)
    active_repos: Mapped[list] = mapped_column(JSON, default=list)
    available_models: Mapped[list] = mapped_column(JSON, default=list)
    gpu_info: Mapped[str] = mapped_column(String, nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # person/project/location/goal
    notes: Mapped[str] = mapped_column(Text, default="")
    related_ids: Mapped[list] = mapped_column(JSON, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Init script:
```python
# init_db.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from atlas.db.models import Base
import os
from dotenv import load_dotenv
load_dotenv()

async def init():
    engine = create_async_engine(os.getenv("DATABASE_URL"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

asyncio.run(init())
```

**Expected Result:** All 8 tables created in PostgreSQL.

**Test Method:** `psql -U atlas_user -d atlas -c "\dt"` shows all table names.

**Rollback Plan:** `DROP DATABASE atlas; CREATE DATABASE atlas;` and re-run init_db.py.

✅ **Checkpoint:** `\dt` shows: users, chats, messages, tasks, memory_entries, usage_logs, machines, entities.

---

## Task 1A.3 — Vector Database Setup (pgvector) ✅ COMPLETE

**Goal:** Vector search so Heimdall finds relevant notes, code, and memories semantically.

**Status:** COMPLETE — pgvector is the production retrieval engine.

**Why pgvector over LanceDB:**
- Dell R620 Xeon E5-2600 lacks AVX2 → LanceDB crashes with `Illegal instruction`
- pgvector runs inside PostgreSQL (no AVX2 requirement)
- Simpler architecture (one less service to manage)
- Native SQL queries, ACID compliance, backups with PostgreSQL

**Tables:** `vector_memory`, `vector_notes`, `vector_chat_summaries`, `vector_code_chunks`

**Steps:**
```bash
# Install pgvector Python library
pip install pgvector

# Enable pgvector extension in PostgreSQL
docker exec heimdall-postgres psql -U heimdall -d heimdall -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Pull embedding model via Ollama
docker exec heimdall-ollama ollama pull nomic-embed-text
```

Create `atlas/db/vector_store.py`:
```python
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def embed_text(text: str) -> list[float]:
    """Generate embedding using Ollama"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=30,
        )
        return response.json()["embedding"]

async def search_similar(session: AsyncSession, query: str, table: str, limit: int = 5):
    """Search pgvector table for similar items"""
    embedding = await embed_text(query)
    # Convert to string for PostgreSQL vector type
    vector_str = "[" + ",".join(map(str, embedding)) + "]"
    
    sql = text(f"""
        SELECT id, text, source_type, source_path,
               embedding <=> :vector as distance
        FROM {table}
        ORDER BY embedding <=> :vector
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {
        "vector": vector_str,
        "limit": limit
    })
    return result.fetchall()
```

**Expected Result:** pgvector extension enabled, embedding model pulled.

**Test Method:** 
```bash
# Verify pgvector is enabled
docker exec heimdall-postgres psql -U heimdall -d heimdall -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# Verify model is available
curl http://localhost:11434/api/tags | grep nomic-embed-text
```

**Rollback Plan:** `docker exec heimdall-postgres psql -U heimdall -d heimdall -c "DROP EXTENSION IF EXISTS vector;"`

✅ **Checkpoint:** pgvector extension listed, nomic-embed-text model available.

---

## Task 1A.4 — Build Embedding Service ✅ COMPLETE

**Goal:** Reusable async service for embedding, storing, and searching across all pgvector tables.

**Status:** COMPLETE — `atlas/core/embeddings.py` and `atlas/db/vector_store.py` operational.

**Current Implementation:**
- `embed()` → Ollama nomic-embed-text (768-dim vectors)
- `store()` → Insert into pgvector table with SQL
- `search()` → `<=>` cosine distance operator
- `search_all()` → Query across all 4 vector tables

**Code Location:**
- `atlas/db/vector_store.py` — pgvector operations
- `atlas/core/embeddings.py` — Embedding + similarity functions

**Test:**
```python
import asyncio
from atlas.db.vector_store import store, search_all

async def test():
    await store("vector_memory", "Heimdall is my personal AI assistant", "note", "test")
    await store("vector_memory", "Saving for a PC build this year", "goal", "goals/pc.md")
    results = await search_all("personal assistant savings")
    for r in results:
        print(r["text"][:80])

asyncio.run(test())
```

✅ **Checkpoint:** Embedding + pgvector search operational.

---

## Task 1A.5 — Install Paperless-ngx

**Goal:** All documents and receipts dropped into Atlas get OCR'd, tagged, and made searchable automatically.

**Steps:**

Create `~/paperless/docker-compose.yml`:
```yaml
version: "3.4"
services:
  broker:
    image: docker.io/library/redis:7
    restart: unless-stopped
  db:
    image: docker.io/library/postgres:16
    restart: unless-stopped
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: paperless
      POSTGRES_USER: paperless
      POSTGRES_PASSWORD: paperless
  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    restart: unless-stopped
    depends_on: [db, broker]
    ports:
      - "8010:8000"
    volumes:
      - data:/usr/src/paperless/data
      - media:/usr/src/paperless/media
      - ./consume:/usr/src/paperless/consume
      - ./export:/usr/src/paperless/export
    environment:
      PAPERLESS_REDIS: redis://broker:6379
      PAPERLESS_DBHOST: db
      PAPERLESS_DBUSER: paperless
      PAPERLESS_DBPASS: paperless
      PAPERLESS_SECRET_KEY: change-this-to-random-string
      PAPERLESS_OCR_LANGUAGE: eng
      PAPERLESS_TIME_ZONE: Europe/London
      PAPERLESS_URL: http://localhost:8010
volumes:
  data:
  media:
  pgdata:
```

```bash
cd ~/paperless
docker compose up -d
docker compose exec webserver python manage.py createsuperuser
```

Open http://localhost:8010.

**Expected Result:** Drop PDF into `~/paperless/consume/` → appears in UI with OCR text within 60 seconds.

**Test Method:** Drop any PDF into consume folder. Wait 60 seconds. Open UI → document searchable by its text content.

**Rollback Plan:** `docker compose down`. Data persists in Docker volumes.

✅ **Checkpoint:** PDF in consume folder → OCR text searchable in Paperless within 60 seconds.

---

## Task 1A.6 — Async FastAPI Setup

**Goal:** All API calls and file operations run async so multiple requests never block each other.

**Steps:**
```bash
pip install aiofiles
```

Convert `atlas/server.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from atlas.db.postgres import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Atlas", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```

Rules for all handlers:
- `def fn()` → `async def fn()`
- `httpx.post()` → `async with httpx.AsyncClient() as c: await c.post()`
- `open()` → `async with aiofiles.open() as f:`

**Expected Result:** Server handles 5+ simultaneous requests without blocking.

**Test Method:** `ab -n 20 -c 5 http://localhost:8000/health` — all 20 requests complete in under 2 seconds.

**Rollback Plan:** Revert to sync. Async is a pure internal change.

✅ **Checkpoint:** 5 concurrent `/health` requests all return within 500ms with no timeouts.

---

## Task 1A.7 — Task Queue (Dramatiq + Redis)

**Goal:** Long-running jobs (OCR, embeddings, summarisation) run in background workers so API responses are instant.

**Queue Types:**

| Queue | Priority | Used For |
|---|---|---|
| `high_priority` | Immediate | Interactive user tasks — flashcard gen, chat context, voice responses |
| `background` | Normal | Indexing, summarisation, embedding, inbox processing, cleanup |
| `scheduled` | Timed | Nightly backups, daily re-indexing, health checks, morning brief prep |

**Steps:**
```bash
pip install dramatiq[redis] redis
docker run -d --name redis -p 6379:6379 redis:7
```

Create `atlas/workers/tasks.py`:
```python
import dramatiq
from dramatiq.brokers.redis import RedisBroker

broker = RedisBroker(url="redis://localhost:6379")
dramatiq.set_broker(broker)

@dramatiq.actor(queue_name="background")
def embed_and_store(text: str, source_type: str, source_path: str):
    import asyncio
    from atlas.core.embeddings import store_memory
    asyncio.run(store_memory(text, source_type, source_path))

@dramatiq.actor(queue_name="background")
def process_inbox_file(filepath: str):
    import asyncio
    from atlas.workers.ingestion_worker import process_file
    from pathlib import Path
    asyncio.run(process_file(Path(filepath)))

@dramatiq.actor(queue_name="high_priority")
def generate_flashcards_async(topic: str, content: str):
    import asyncio
    from atlas.api.study import generate_flashcards_internal
    asyncio.run(generate_flashcards_internal(topic, content))
```

Start worker:
```bash
dramatiq atlas.workers.tasks &
```

Update upload endpoint to dispatch to queue:
```python
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    dest = INBOX_PATH / file.filename
    async with aiofiles.open(dest, "wb") as f:
        await f.write(await file.read())
    process_inbox_file.send(str(dest))  # Non-blocking dispatch
    return {"status": "queued", "filename": file.filename}
```

**Expected Result:** File upload returns in under 200ms. Processing happens in background.

**Test Method:** Upload a large PDF. API returns `{"status": "queued"}` instantly. File processed in background within 60 seconds.

**Rollback Plan:** Remove `.send()` calls, revert to direct function calls. Queue is additive.

✅ **Checkpoint:** Upload returns instantly. File processed in background. Appears in vault within 60 seconds.

---

---

# PHASE 1B — Security & Auth
*Goal: Safe to expose publicly. Single-user JWT auth with tool permission levels.*

---

## Task 1B.1 — JWT Authentication

**Goal:** All API endpoints require a valid login token.

**Long-term auth path:** Single-user JWT for all development phases. Migrate to **Supabase Auth** when multi-user or team workspace support is needed — it handles tokens, refresh, OAuth providers, and row-level security with minimal code change.

**Steps:**
```bash
pip install python-jose[cryptography] passlib[bcrypt] python-multipart
```

Create `atlas/api/auth.py`:
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"])
bearer = HTTPBearer()

def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/auth/login")
async def login(body: dict):
    if body.get("password") == os.getenv("ATLAS_PASSWORD"):
        return {"access_token": create_token("default-user"), "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Wrong password")
```

Add `JWT_SECRET_KEY` and `ATLAS_PASSWORD` to `.env`.

Add to Vercel fetch calls:
```typescript
"Authorization": `Bearer ${localStorage.getItem("atlas_token")}`
```

**Expected Result:** Unauthenticated request → 401. Authenticated → works.

**Test Method:** `curl -X POST http://localhost:8000/chat -d '{}'` → 401. With valid token → normal response.

**Rollback Plan:** Remove `Depends(get_current_user)` from endpoints. Auth is additive.

✅ **Checkpoint:** Request without token → 401. Login returns token. Token authorises subsequent requests.

---

## Task 1B.2 — Tool Permission Layer

**Goal:** Dangerous actions require explicit confirmation or elevated mode.

**Steps:**

Create `atlas/core/permissions.py`:
```python
from enum import Enum
from fastapi import HTTPException

class PermissionLevel(Enum):
    SAFE = 0
    CONFIRM_REQUIRED = 1
    TRUSTED = 2
    AUTONOMOUS = 3

TOOL_PERMISSIONS = {
    "read_file": PermissionLevel.SAFE,
    "search_notes": PermissionLevel.SAFE,
    "get_weather": PermissionLevel.SAFE,
    "get_directions": PermissionLevel.SAFE,
    "write_file": PermissionLevel.CONFIRM_REQUIRED,
    "send_notification": PermissionLevel.CONFIRM_REQUIRED,
    "git_commit": PermissionLevel.CONFIRM_REQUIRED,
    "git_push": PermissionLevel.TRUSTED,
    "run_terminal": PermissionLevel.TRUSTED,
    "delete_file": PermissionLevel.TRUSTED,
    "deploy": PermissionLevel.AUTONOMOUS,
    "run_migration": PermissionLevel.AUTONOMOUS,
}

CURRENT_MODE = PermissionLevel.CONFIRM_REQUIRED

def require_permission(tool_name: str):
    required = TOOL_PERMISSIONS.get(tool_name, PermissionLevel.TRUSTED)
    if CURRENT_MODE.value < required.value:
        raise HTTPException(
            status_code=403,
            detail=f"'{tool_name}' requires {required.name} mode. Current: {CURRENT_MODE.name}"
        )
```

**Expected Result:** `run_terminal` in SAFE mode → 403. In TRUSTED mode → passes.

**Test Method:** Set `CURRENT_MODE = SAFE`, call `require_permission("run_terminal")` → HTTPException raised.

**Rollback Plan:** Remove `require_permission()` calls. Permissions are additive.

✅ **Checkpoint:** `require_permission("run_terminal")` in SAFE mode raises 403. In TRUSTED mode passes silently.

---

## Task 1B.3 — Startup Config Validation

**Goal:** Server refuses to start if required secrets are missing. No silent failures.

**Steps:**

Create `atlas/core/config.py`:
```python
import os
from dotenv import load_dotenv
load_dotenv()

REQUIRED = ["DATABASE_URL", "JWT_SECRET_KEY", "ATLAS_PASSWORD"]
OPTIONAL = ["DEEPSEEK_API_KEY", "GEMINI_API_KEY", "GOOGLE_MAPS_KEY", "OPENWEATHER_KEY", "GARMIN_EMAIL", "ANTHROPIC_API_KEY"]

def validate_config():
    missing = [k for k in REQUIRED if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Atlas startup failed. Missing required secrets: {missing}")
    optional_missing = [k for k in OPTIONAL if not os.getenv(k)]
    if optional_missing:
        print(f"[WARN] Optional secrets not set (some features disabled): {optional_missing}")
    print("[OK] Config validated.")

validate_config()
```

Also verify `.gitignore` includes:
```
.env
*.env
.env.local
atlas-lancedb/
__pycache__/
```

**Expected Result:** Missing `JWT_SECRET_KEY` → RuntimeError with clear message, server stops.

**Test Method:** Temporarily remove `JWT_SECRET_KEY` from `.env`. Run server → error, does not start.

**Rollback Plan:** Add key back to `.env`.

✅ **Checkpoint:** Remove a required secret → server prints error and stops. Restore it → server starts normally.

---

## Task 1B.4 — API Rate Limiting

**Goal:** Prevent runaway workers, abuse, or accidents from burning API credits or exhausting resources.

**Steps:**

```bash
pip install slowapi
```

Create `atlas/core/rate_limiter.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI

# Per-endpoint limits
limiter = Limiter(key_func=get_remote_address)

# Limits:
# - /chat: 30/min (generous for conversation)
# - /upload: 10/min (file ingestion)
# - /dev/*: 5/min (dev mode safety)
# - Health checks: 60/min
# - Burst allowance: 5 requests before limit kicks in
```

Apply to endpoints:
```python
@app.post("/chat")
@limiter.limit("30/minute")
async def chat(req: ChatRequest):
    ...
```

Queue-based rate limiting (for external APIs):
```python
# atlas/core/circuit_breaker.py
class CircuitBreaker:
    """Circuit breaker for external APIs with exponential backoff"""
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, fn, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception(f"Circuit breaker OPEN for {self.timeout}s")
        
        try:
            result = fn(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
            raise e
```

**Expected Result:** 31st chat request in a minute → 429 Too Many Requests. External API failures trigger circuit breaker.

**Test Method:** `ab -n 50 -c 10 http://localhost:8000/health` → first 60 pass, rest rate limited.

✅ **Checkpoint:** Rate limits enforced. Circuit breaker opens after 5 consecutive API failures.

---

## Task 1B.5 — Security Middleware (PII & Prompt Injection)

**Goal:** Filter sensitive data before storage. Detect prompt injection attempts.

**Why:** Heimdall stores everything you say. You might accidentally paste:
- Passwords or API keys
- Credit card numbers
- Personal IDs
- Malicious prompts trying to override system instructions

**Implementation:**
```python
# atlas/core/security_middleware.py
import re
from fastapi import Request, HTTPException

# Patterns to detect
PII_PATTERNS = {
    "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "api_key": r"(sk-|pk-|ghp_|glpat-)[a-zA-Z0-9_\-]{20,}",
    "password_in_url": r"(https?://[^:]+:[^@]+@)",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
}

PROMPT_INJECTION_MARKERS = [
    "ignore previous instructions",
    "disregard your system prompt",
    "you are now",
    "DAN mode",
    "jailbreak",
    "system override",
]

def sanitize_input(text: str) -> tuple[str, list[str]]:
    """Returns (sanitized_text, detected_issues)"""
    issues = []
    
    # Detect PII
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            issues.append(f"pii:{pii_type}")
            # Redact: replace with [REDACTED-{type}]
            for match in matches:
                text = text.replace(match, f"[REDACTED-{pii_type}]")
    
    # Detect prompt injection
    lower = text.lower()
    for marker in PROMPT_INJECTION_MARKERS:
        if marker in lower:
            issues.append(f"injection_attempt:{marker}")
    
    return text, issues

# FastAPI middleware
@app.middleware("http")
async def security_filter(request: Request, call_next):
    if request.method == "POST" and "chat" in request.url.path:
        body = await request.body()
        if body:
            import json
            data = json.loads(body)
            if "message" in data:
                sanitized, issues = sanitize_input(data["message"])
                if issues:
                    # Log the attempt
                    log.warning("security_filter_triggered", issues=issues, user=user_id)
                    # If injection detected, block entirely
                    if any("injection" in i for i in issues):
                        raise HTTPException(400, "Potentially malicious input detected")
                data["message"] = sanitized
                # Re-serialize body
                request._body = json.dumps(data).encode()
    
    return await call_next(request)
```

**Expected Result:** PII auto-redacted before storage. Injection attempts logged and blocked.

✅ **Checkpoint:** Send message with fake credit card number → stored as `[REDACTED-credit_card]`. Send "ignore previous instructions" → 400 error.

---

---

# PHASE 2A — Memory System
*Goal: Atlas remembers across conversations and across time.*

---

## Task 2A.1 — Multi-Chat System with Auto-Archive

**Goal:** Multiple independent conversations stored in PostgreSQL, navigable in dashboard. Old chats auto-archive to prevent unbounded growth.

**Storage Context:** R620 has 8 drive bays, only 2 used. Current setup likely 2x drives in RAID. For long-term growth:
- **Option A:** Add 2-4 more drives, expand RAID array (requires backup/rebuild)
- **Option B:** Add SSDs as separate ZFS pool for hot data (PostgreSQL, active vault)
- **Option C:** External USB3 storage for cold archive (old chats, logs)
- **Option D:** Cloud sync to S3/Backblaze for offsite backup (encrypt before upload)

**Recommended:** Add 2x 1TB SSDs as new ZFS mirror for PostgreSQL + active vault. Keep existing HDDs for bulk storage (Paperless, old archives).

**Steps:**

Add to `atlas/api/chat.py`:
```python
@router.post("/chats")
async def create_chat(user_id: str = Depends(get_current_user), db=Depends(get_session)):
    chat = Chat(user_id=user_id, title="New chat")
    db.add(chat); await db.commit()
    return {"id": chat.id, "title": chat.title}

@router.get("/chats")
async def list_chats(user_id: str = Depends(get_current_user), db=Depends(get_session)):
    result = await db.execute(
        select(Chat).where(Chat.user_id == user_id).order_by(Chat.created_at.desc())
    )
    return result.scalars().all()
```

Add chat sidebar to Next.js dashboard:
- Left panel: chat list, "New Chat" button, rename on double-click
- Clicking a chat loads its history
- Active chat ID in Zustand state (Phase 5A)

**Expected Result:** Multiple chats persist. Switching between them loads correct history.

**Test Method:** Create 3 chats, send messages in each. Reload browser. All 3 chats with messages intact.

**Rollback Plan:** Revert to single-session model. History in component state only.

✅ **Checkpoint:** 3 chats created. Browser closed and reopened. All 3 chats with messages still present.

---

## Task 2A.1b — Chat Retention & Auto-Archive

**Goal:** Prevent PostgreSQL from growing unbounded. Auto-archive old chats while keeping summaries searchable.

**Policy:**
- Keep last 90 days of full chat history in `messages` table
- Archive chats >90 days to cold storage (JSON files in `~/atlas-archive/chats/`)
- Always keep chat summaries in pgvector (semantic memory persists forever)
- Compress archive with gzip (typically 10:1 ratio)

**Implementation:**
```python
# atlas/workers/archive_worker.py
@dramatiq.actor(queue_name="scheduled")
def archive_old_chats():
    """Run nightly: archive chats older than 90 days"""
    cutoff = datetime.utcnow() - timedelta(days=90)
    
    # Find old chats
    old_chats = db.execute(
        select(Chat).where(Chat.last_message_at < cutoff, Chat.archived == False)
    ).scalars().all()
    
    for chat in old_chats:
        # Export to JSON
        messages = db.execute(select(Message).where(Message.chat_id == chat.id)).scalars().all()
        archive_data = {
            "chat_id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "messages": [{"role": m.role, "content": m.content, "ts": m.created_at.isoformat()} for m in messages]
        }
        
        # Write compressed archive
        archive_path = Path(f"~/atlas-archive/chats/{chat.id[:8]}_{chat.created_at.strftime('%Y%m%d')}.json.gz")
        with gzip.open(archive_path, "wt") as f:
            json.dump(archive_data, f)
        
        # Delete messages, mark chat archived (keep metadata)
        db.execute(delete(Message).where(Message.chat_id == chat.id))
        chat.archived = True
        db.commit()

# atlas/api/chat.py - updated list endpoint
@router.get("/chats")
async def list_chats(archived: bool = False, ...):
    # Default shows only active chats
    # Set archived=true to see archived (with "restore" button)
```

**Expected Result:** Database size stable. Old chats accessible via archive browse. Full-text search still works via summaries in pgvector.

✅ **Checkpoint:** 91-day-old chat auto-archived to JSON.gz. Database row count drops. Archived chat appears in "Archive" tab with Restore button.

---

## Task 2A.2 — Chat Summarisation Worker

**Goal:** Every 15 messages, Atlas compresses the conversation into a semantic memory entry.

**Steps:**

Add to `atlas/workers/tasks.py`:
```python
@dramatiq.actor(queue_name="background")
def summarise_chat(chat_id: str):
    import asyncio
    asyncio.run(_summarise(chat_id))

async def _summarise(chat_id: str):
    # Fetch last 20 messages
    async with AsyncSession() as db:
        result = await db.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at).limit(20)
        )
        messages = result.scalars().all()
    
    conversation = "\n".join([f"{m.role}: {m.content}" for m in messages])
    
    prompt = f"""Summarise this conversation. Extract decisions, entities, tasks, topics.
Under 200 words. JSON only:
{{"summary": "...", "entities": ["..."], "tasks": ["..."], "topics": ["..."]}}

Conversation:
{conversation}"""
    
    from atlas.services.deepseek_service import call_deepseek
    result_text = await call_deepseek(prompt, model="deepseek-v4-flash")
    
    import json, re
    match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if match:
        data = json.loads(match.group())
        from atlas.core.embeddings import store_memory
        await store_memory(data.get("summary", result_text), "chat_summary", f"chat:{chat_id}")
```

Trigger: after saving every 15th message in a chat, call `summarise_chat.send(chat_id)`.

**Expected Result:** After 15 messages, a summary stored in pgvector `vector_chat_summaries` table.

**Test Method:** Send 15+ messages. Query `search_all("conversation topics")` → returns the summary.

**Rollback Plan:** Remove trigger. Summarisation is additive.

✅ **Checkpoint:** 15+ messages → summary in pgvector → `search_all` returns it in a new chat.

---

## Task 2A.3 — Retrieval-Augmented Responses (RAG)

**Goal:** Before calling any model, Heimdall searches pgvector for relevant context and injects it into the system prompt.

**Steps:**

Update `atlas/core/planner.py`:
```python
async def build_context(message: str) -> str:
    from atlas.core.embeddings import search_all
    results = await search_all(message, limit=4)
    if not results:
        return ""
    parts = [f"[{r['type']} — {r['source']}]: {r['text'][:300]}" for r in results]
    return "Relevant context from memory:\n" + "\n---\n".join(parts)

async def respond(message: str, history: list) -> dict:
    context = await build_context(message)
    system = f"You are Atlas, a personal AI assistant. Be concise and helpful.\n\n{context}"
    from atlas.core.router import route
    return await route(message, history=history, system=system)
```

**Expected Result:** Atlas answers questions about past conversations and saved notes without being told.

**Test Method:** Store a note: "My gym is at 7 Elgin Ave". Start a new chat. Ask "where is my gym?" → Atlas answers correctly from memory.

**Rollback Plan:** Remove `build_context()` call. Context injection is additive.

✅ **Checkpoint:** Store a fact in one chat. Open new chat. Ask about it. Atlas answers correctly without being reminded.

---

## Task 2A.4 — Entity Graph

**Goal:** Heimdall tracks people, projects, and locations as named entities that persist and can be queried.

**Steps:**

Extract entities during chat summarisation and upsert into the `entities` table:
```python
async def extract_and_store_entities(summary_data: dict, user_id: str, db):
    for name in summary_data.get("entities", []):
        result = await db.execute(
            select(Entity).where(Entity.user_id == user_id, Entity.name == name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.last_seen = datetime.utcnow()
        else:
            db.add(Entity(user_id=user_id, name=name, type="unknown", first_seen=datetime.utcnow()))
    await db.commit()
```

Add endpoint: `GET /entities?type=project` → returns all known entities of that type.

**Expected Result:** Mentioning "Saferoute project" and "James" in chat → both appear in entity list after summarisation.

**Test Method:** Mention a project name 3+ times in chat. After 15 messages and summarisation, `GET /entities` → project listed.

**Rollback Plan:** Drop entity table. Nothing else depends on it yet.

✅ **Checkpoint:** Entity mentioned in chat → appears in `GET /entities` after summarisation.

---

---

# PHASE 2B — Capability Planner & Tools
*Goal: One message triggers multiple tools. Atlas acts, not just answers.*

---

## Task 2B.1 — Capability Planner

**Goal:** Replace the simple classifier with a planner that returns a list of capabilities and tools needed.

**Steps:**

Create `atlas/core/planner.py`:
```python
PLAN_PROMPT = """You are a planning agent for Atlas.
Given a user message, return a JSON plan.

Capabilities: retrieval, maps, vision, study, goals, health, budget, calendar, code, writing, simple
Models: local (fast/free), flash (writing), pro (complex), vision (images), code (programming)
Tools: get_calendar, get_weather, get_directions, get_bus_times, search_notes, search_memory,
       read_goal, update_goal, read_budget, get_health, read_file, write_file, git_commit, create_task

JSON only:
{
  "capabilities": ["retrieval", "writing"],
  "model": "flash",
  "tools": ["search_notes", "get_weather"],
  "requires_confirmation": false,
  "reasoning": "one sentence"
}

User message: {message}"""

async def plan(message: str) -> dict:
    from atlas.services.ollama_service import call_ollama
    result = await call_ollama(PLAN_PROMPT.format(message=message))
    import json, re
    match = re.search(r'\{.*\}', result, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"capabilities": ["simple"], "model": "local", "tools": [], "requires_confirmation": False}
```

**Expected Result:** "How long to get to work and will it rain?" → plan includes `maps` + `simple`, tools `get_directions` + `get_weather`.

**Test Method:** Run 5 varied messages through planner. Check outputs are sensible for each type.

**Rollback Plan:** Revert to `router.py` classify. Planner is a drop-in replacement.

✅ **Checkpoint:** "Next bus and should I bring an umbrella?" → plan returns `["maps", "simple"]` with correct tools.

---

## Task 2B.2 — Tool Execution Engine

**Goal:** Planner output drives automatic tool execution before the model is called.

**Steps:**

Create `atlas/core/tool_executor.py`:
```python
from atlas.core.permissions import require_permission

TOOL_REGISTRY = {}

def tool(name: str, permission: str = "safe"):
    def decorator(fn):
        TOOL_REGISTRY[name] = {"fn": fn, "permission": permission}
        return fn
    return decorator

@tool("get_weather", permission="safe")
async def get_weather_tool(args: dict) -> str:
    from atlas.services.maps_service import get_weather
    return await get_weather()

@tool("get_directions", permission="safe")
async def get_directions_tool(args: dict) -> str:
    from atlas.services.maps_service import get_directions
    r = await get_directions(args.get("origin", "home"), args.get("destination", ""))
    return f"Journey: {r.get('duration')} ({r.get('distance')})"

@tool("search_notes", permission="safe")
async def search_notes_tool(args: dict) -> str:
    from atlas.core.embeddings import search_all
    results = await search_all(args.get("query", ""), limit=3)
    return "\n".join([r["text"][:200] for r in results])

@tool("create_task", permission="safe")
async def create_task_tool(args: dict) -> str:
    # Creates a task in PostgreSQL
    return f"Task created: '{args.get('title', 'unnamed')}'"

async def execute_tools(tool_names: list[str]) -> dict:
    results = {}
    for name in tool_names:
        if name in TOOL_REGISTRY:
            require_permission(name)
            try:
                results[name] = await TOOL_REGISTRY[name]["fn"]({})
            except Exception as e:
                results[name] = f"Error: {e}"
    return results
```

**Expected Result:** Planner returns `["get_weather", "search_notes"]` → both execute → both results injected into prompt.

**Test Method:** Ask "what's the weather and what are my goals?" → both tools execute → both visible in Atlas response.

**Rollback Plan:** Skip `execute_tools()` call. Tools are purely additive.

✅ **Checkpoint:** Two tools requested → both execute → both results appear in Atlas response.

---

---

# PHASE 3A — Observability
*Goal: Know what Atlas is doing, what it costs, and where it fails.*

---

## Task 3A.1 — Structured Logging

**Goal:** Every request, model call, and error logged in structured JSON format.

**Steps:**
```bash
pip install structlog
```

Create `atlas/core/logging.py`:
```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger()

# Usage anywhere:
# log.info("model_call", model="deepseek/v4-flash", tokens=450, latency_ms=820)
# log.error("tool_failed", tool="get_directions", error=str(e))
```

Add log calls to: every model call, every tool execution, every file operation, every error.

**Expected Result:** Structured JSON logs with timestamp, level, model, latency.

**Test Method:** Send a chat message. Check logs → see `model_call` entry with model name and latency_ms.

**Rollback Plan:** Remove structlog. Revert to `print()`. Logging is additive.

✅ **Checkpoint:** Single chat message → log entry shows `model_call` with model, tokens, latency_ms.

---

## Task 3A.2 — Langfuse Tracing

**Goal:** Full request traces viewable in a web UI — prompts, responses, token costs, latency.

**Steps:**
```bash
docker run -d --name langfuse -p 3001:3000 \
  -e NEXTAUTH_SECRET=change-me \
  -e SALT=change-me \
  -e DATABASE_URL=postgresql://atlas_user:password@host.docker.internal/atlas \
  langfuse/langfuse:latest

pip install langfuse
```

Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to `.env` (from Langfuse UI after login).

Wrap model calls:
```python
from langfuse import Langfuse
lf = Langfuse()

async def call_deepseek_traced(message: str, model: str) -> str:
    trace = lf.trace(name="atlas_chat")
    gen = trace.generation(name="call", model=model, input=message)
    response = await call_deepseek(message, model=model)
    gen.end(output=response)
    return response
```

**Expected Result:** Every model call appears in Langfuse at http://localhost:3001 with full trace.

**Test Method:** Send 3 messages. Open Langfuse → Traces — all 3 visible with prompt, response, latency.

**Rollback Plan:** Remove Langfuse wrapper. Tracing is additive.

✅ **Checkpoint:** 3 messages → 3 traces in Langfuse with model name, prompt, response visible.

---

---

# PHASE 3B — Streaming
*Goal: Responses appear word by word. Dramatically better feel.*

---

## Task 3B.1 — Streaming API Endpoint

**Goal:** Model tokens stream to the frontend via SSE as they're generated.

**Steps:**

Add to `atlas/api/chat.py`:
```python
from fastapi.responses import StreamingResponse
import json

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, user_id: str = Depends(get_current_user)):
    async def generate():
        plan = await planner.plan(req.message)
        tool_results = await execute_tools(plan.get("tools", []))
        context = "\n".join([f"{k}: {v}" for k, v in tool_results.items()])
        system = f"You are Atlas. {context}"
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
                json={"model": "deepseek-v4-flash", "messages": [
                    {"role": "system", "content": system},
                    *req.history,
                    {"role": "user", "content": req.message},
                ], "stream": True},
                timeout=60,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        delta = data["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield f"data: {json.dumps({'token': delta})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Expected Result:** Tokens arrive one at a time in terminal.

**Test Method:**
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Count to 5 slowly"}'
```
Numbers appear progressively.

**Rollback Plan:** Keep `/chat` non-streaming. `/chat/stream` is additive.

✅ **Checkpoint:** `curl -N` shows tokens arriving progressively, not all at once.

---

## Task 3B.2 — Streaming Frontend

**Goal:** Chat UI renders tokens live as they arrive. Cancel button works.

**Steps:**

Update chat component:
```typescript
const sendStreaming = async () => {
  setMessages(prev => [...prev, { role: "user", content: input }]);
  setMessages(prev => [...prev, { role: "assistant", content: "", streaming: true }]);
  setInput(""); setLoading(true);
  
  const response = await fetch(`${API}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${getToken()}` },
    body: JSON.stringify({ message: input, history: messages }),
  });
  
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value).split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ") && line !== "data: [DONE]") {
        const { token } = JSON.parse(line.slice(6));
        if (token) {
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1].content += token;
            return updated;
          });
        }
      }
    }
  }
  setLoading(false);
};
```

**Expected Result:** Response renders word by word. Cancel aborts mid-stream.

**Test Method:** Ask Atlas a long question. Watch tokens appear progressively. Click cancel — stops mid-sentence.

**Rollback Plan:** Use non-streaming `/chat` endpoint. Streaming is additive.

✅ **Checkpoint:** Response streams live. Cancel button stops generation cleanly.

---

---

# PHASE 4A — Persistent Task System
*Goal: Tasks exist independently of chats. Atlas creates and tracks them.*

---

## Task 4A.1 — Task Manager

**Goal:** Tasks stored in PostgreSQL with status, subtasks, and due dates. Visible in dashboard.

**Steps:**

Add to `atlas/api/tasks.py`:
```python
@router.post("/tasks")
async def create_task(body: dict, user_id: str = Depends(get_current_user), db=Depends(get_session)):
    task = Task(user_id=user_id, title=body.get("title"), subtasks=body.get("subtasks", []), due_date=body.get("due_date"))
    db.add(task); await db.commit()
    return task

@router.get("/tasks")
async def list_tasks(status: str = "pending", user_id: str = Depends(get_current_user), db=Depends(get_session)):
    result = await db.execute(select(Task).where(Task.user_id == user_id, Task.status == status))
    return result.scalars().all()

@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, body: dict, db=Depends(get_session)):
    task = await db.get(Task, task_id)
    for k, v in body.items():
        setattr(task, k, v)
    await db.commit()
    return task
```

Add Tasks tab to dashboard: list with status badges and due dates.

**Expected Result:** Tasks created and updated via API persist across sessions.

**Test Method:** Create 3 tasks. Mark one as done. Reload page. 2 pending, 1 done — all persist.

**Rollback Plan:** Remove Tasks tab. Reminders fall back to n8n only.

✅ **Checkpoint:** Create 3 tasks. Mark 1 done. Reload. Correct statuses persist.

---

## Task 4A.2 — Agent Task Creation from Chat

**Goal:** "Remind me to X on Friday" → task created automatically, Atlas confirms.

**Steps:**

Add `create_task` tool to registry (see Task 2B.2). Add instruction to Atlas system prompt:

> *"If the user asks to be reminded about something or needs to do something in future, use the create_task tool and confirm you've saved it."*

After creating a task, Atlas responds: *"Done — I've added 'call dentist' to your tasks for Friday."*

**Expected Result:** Natural language reminder → task in PostgreSQL → visible in Tasks tab.

**Test Method:** Say "remind me to review the budget this Sunday." Check `/tasks` → task appears with correct title.

**Rollback Plan:** Remove `create_task` from tool registry.

✅ **Checkpoint:** Natural language reminder → task appears in Tasks tab with correct title and due date.

---

---

# PHASE 5A — Frontend State & Resilience
*Goal: Dashboard state persists, API calls are cached, works on flaky networks.*

---

## Task 5A.1 — Zustand State Management

**Goal:** Active chat, messages, model selection, and auth token persist across page refreshes.

**Steps:**
```bash
npm install zustand
```

Create `src/store/useAtlasStore.ts`:
```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AtlasStore {
  chats: any[];
  activeChatId: string | null;
  modelOverride: string | null;
  token: string | null;
  setToken: (t: string) => void;
  setActiveChat: (id: string) => void;
  setModelOverride: (m: string | null) => void;
}

export const useAtlasStore = create<AtlasStore>()(
  persist(
    (set) => ({
      chats: [], activeChatId: null, modelOverride: null, token: null,
      setToken: (token) => set({ token }),
      setActiveChat: (id) => set({ activeChatId: id }),
      setModelOverride: (model) => set({ modelOverride: model }),
    }),
    { name: "atlas-store" }
  )
);
```

Replace all `useState` for persistent data with Zustand store.

**Expected Result:** Chat history, active chat, model override persist across refreshes.

**Test Method:** Select "DeepSeek Pro" override, refresh page. Override still selected.

**Rollback Plan:** Remove persist middleware. State reverts to component-level useState.

✅ **Checkpoint:** Select model override, refresh page → override preserved. Auth token persists.

---

## Task 5A.2 — TanStack Query Caching

**Goal:** API calls cached, retried on failure, background refresh keeps data fresh.

**Steps:**
```bash
npm install @tanstack/react-query
```

Wrap app in `QueryClientProvider`. Convert fetch calls:
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const { data: tasks } = useQuery({
  queryKey: ["tasks"],
  queryFn: () => fetch(`${API}/tasks`, { headers: authHeaders() }).then(r => r.json()),
  staleTime: 30_000,
  retry: 3,
});

const createTask = useMutation({
  mutationFn: (title: string) =>
    fetch(`${API}/tasks`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ title }) }).then(r => r.json()),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
});
```

**Expected Result:** Tasks/goals/health data cached. Retries on failure. No loading flicker on revisit.

**Test Method:** Open Tasks tab. Disconnect WiFi. Refresh — cached tasks still visible.

**Rollback Plan:** Remove TanStack Query. Revert to raw useEffect + fetch.

✅ **Checkpoint:** Load Tasks tab. Disconnect WiFi. Refresh. Cached tasks still visible.

---

---

# PHASE 6 — VSCode & Coding Integration
*Goal: Atlas is your full coding assistant. VSCode is the IDE. Phone controls it remotely.*

---

## Task 6.1 — Install Claude Code VSCode Extension

**Goal:** Full agentic AI coding in VSCode sidebar — replaces Cursor and Windsurf.

**Steps:**
1. VSCode → Extensions → search "Claude Code" → install Anthropic's official extension
2. Sign in with Anthropic account (Pro or Max subscription required)
3. Open a project, try: highlight code → ask Claude to explain it
4. Try: "@filename.py what does this do?"
5. Try: ask for a refactor → review the diff → accept or reject

**What you get:**
- Full codebase context — reads entire project
- Inline diffs with per-change accept/reject
- Plan review before applying
- `@-mention` any file or line range
- Multi-file edits
- Terminal execution with confirmation

**Expected Result:** Multi-file refactor completed via chat. Diff reviewed and accepted.

**Test Method:** Ask "add type hints to all functions in router.py" → diff appears → accept → file correct.

**Rollback Plan:** Uninstall extension. `git reset` any unwanted changes.

✅ **Checkpoint:** Claude Code completes a real multi-file edit. Diff reviewed and accepted from sidebar.

---

## Task 6.2 — Claude Code Remote Control

**Goal:** Start coding tasks from phone while away from desk.

**Steps:**
```bash
claude --remote-control
# or inside a session: /rc
```

Scan QR code with Claude iOS app. Same session, full context, streams output to phone.

**Expected Result:** Kick off task on PC. Monitor and prompt from phone. Changes applied to PC codebase.

**Test Method:** Start task on PC. Walk away. Send follow-up from phone. Change applies correctly.

**Rollback Plan:** Close session. No state changes unless edits explicitly accepted.

✅ **Checkpoint:** Coding instruction sent from iPhone → change applied to PC codebase within 60 seconds.

---

## Task 6.3 — CLAUDE.md Context Files

**Goal:** Atlas has full project context without you repeating yourself in every session.

**Steps:**

Create `CLAUDE.md` in each project root:
```markdown
# [Project Name] — Atlas Context

## Stack
[e.g. Next.js 15, FastAPI, Python 3.11, PostgreSQL, LanceDB]

## Architecture
[2-3 sentences on project structure]

## Conventions
- TypeScript strict mode
- Python: type hints everywhere, black formatter
- Commits: conventional commits (feat/fix/chore/docs)
- Never commit .env

## Key Files
- `src/app/` — Next.js pages
- `atlas/api/` — FastAPI route handlers
- `atlas/core/` — Core logic (planner, router, memory)

## Current Sprint Focus
[Update whenever you start a new area]

## Known Issues / TODOs
[Keep current]
```

**Expected Result:** Claude answers project-specific questions from CLAUDE.md without being told.

**Test Method:** Open project. Ask "what database are we using?" — Claude answers correctly from CLAUDE.md.

**Rollback Plan:** Delete the file. No functional impact.

✅ **Checkpoint:** Ask Claude a project question without explaining the stack. It answers correctly.

---

## Task 6.4 — VSCode Connector Daemon

**Goal:** Atlas can dispatch coding tasks to any connected machine from the dashboard or phone. Streams logs back.

**Steps:**

Create `atlas/vscode/connector_daemon.py`:
```python
"""
Persistent daemon per machine.
Connects to Atlas server via WebSocket.
Receives tasks, executes via Claude Code CLI, streams results.
"""
import asyncio, websockets, json, subprocess, os

ATLAS_WS = os.getenv("ATLAS_WS_URL", "ws://localhost:8000/ws/machines")
MACHINE_ID = os.getenv("MACHINE_ID", "desktop")

async def run_task(prompt: str, repo_path: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "claude", "--print", prompt,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode()

async def connect():
    async with websockets.connect(ATLAS_WS) as ws:
        await ws.send(json.dumps({
            "type": "register",
            "machine_id": MACHINE_ID,
            "toolchains": ["python", "node"],
        }))
        print(f"[Connector] '{MACHINE_ID}' connected to Atlas.")
        async for msg in ws:
            task = json.loads(msg)
            if task["type"] == "execute":
                result = await run_task(task["prompt"], task.get("repo_path", "."))
                await ws.send(json.dumps({"type": "result", "task_id": task["id"], "output": result}))

if __name__ == "__main__":
    asyncio.run(connect())
```

Add WebSocket endpoint to `atlas/server.py`:
```python
from fastapi import WebSocket

connected_machines: dict = {}

@app.websocket("/ws/machines")
async def machine_ws(websocket: WebSocket):
    await websocket.accept()
    machine_id = None
    try:
        async for data in websocket.iter_json():
            if data["type"] == "register":
                machine_id = data["machine_id"]
                connected_machines[machine_id] = websocket
    finally:
        if machine_id:
            connected_machines.pop(machine_id, None)
```

**Expected Result:** Daemon connects to Atlas server. Machine appears online in dashboard.

**Test Method:** Start daemon. Check `/machines` endpoint → shows `desktop` with state `online`.

**Rollback Plan:** Stop daemon. Machines go offline. No data lost.

✅ **Checkpoint:** Daemon connects. `/machines` shows machine as online with toolchain info.

---

---

# PHASE 7 — PA Features
*One task per feature. All independent once Phases 1–4 are complete.*

---

## Task 7.0 — Token Context Budgeting

**Goal:** Prevent context overflow. Track token budget per request so critical context isn't silently truncated.

**Why:** With RAG + tool results + chat history, cheap models (8k context) can overflow. Currently happens silently.

**Implementation:**
```python
# atlas/core/token_budget.py
import tiktoken  # or estimate: ~4 chars/token

MODEL_LIMITS = {
    "deepseek/v4-flash": 64000,
    "deepseek/v4-pro": 64000,
    "groq/llama-4-scout": 8192,
    "local/qwen3.5": 32768,
}

def estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 characters"""
    return len(text) // 4

class TokenBudget:
    def __init__(self, model: str, system_prompt: str):
        self.limit = MODEL_LIMITS.get(model, 8192)
        self.used = estimate_tokens(system_prompt)
        self.reserved = 500  # Leave room for response
        self.available = self.limit - self.used - self.reserved
    
    def can_fit(self, text: str) -> bool:
        return estimate_tokens(text) <= self.available
    
    def allocate(self, items: list[dict], priority_key: str = "score") -> list[dict]:
        """Allocate budget to highest-priority items that fit"""
        allocated = []
        for item in sorted(items, key=lambda x: x.get(priority_key, 0), reverse=True):
            tokens = estimate_tokens(item.get("text", ""))
            if tokens <= self.available:
                allocated.append(item)
                self.available -= tokens
            if self.available < 100:
                break
        return allocated
```

Use in planner:
```python
budget = TokenBudget(model, system_prompt)
rag_results = await search_all(message, limit=10)
filtered = budget.allocate(rag_results)
context = format_context(filtered)  # Only what fits
```

**Expected Result:** Model never receives >95% of context window. High-relevance items prioritized.

✅ **Checkpoint:** Log shows "Context: 4500/64000 tokens (7%)" — clear visibility into budget usage.

---

## Task 7.0b — Semantic Duplicate Detection & Backlink Extraction

**Goal:** Before storing new memories/notes/vault entries, check for semantic duplicates AND extract explicit backlinks to connect related content across all brains.

**Why:** Prevents vault pollution AND builds the knowledge graph automatically:
- Duplicate detection: avoid re-uploaded content
- Backlink extraction: auto-connect related concepts (Nate's "WAT framework" appears in 5 places → all linked)
- Cross-vault linking: reference from Personal Brain → YouTube Brain creates bidirectional edge

**Backlink Implementation:**
```python
# atlas/core/backlinks.py
import re

# Patterns that suggest relationships
LINK_PATTERNS = [
    # Explicit wiki-style links: [[Note Name]] or [[Note Name|Display Text]]
    (r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", "wiki"),
    # Markdown links to other vault files: [text](../other-brain/note.md)
    (r"\[([^\]]+)\]\([^)]*vault/([^)]+\.md)\)", "cross_vault"),
    # Entity mentions that match existing entity pages
    (r"\b(WAT framework|Claude Code|React|FastAPI|Docker)\b", "entity"),
    # Reference patterns: "as discussed in [X]", "see also [Y]"
    (r"(?:see also|as discussed in|refer to)[:\s]+([^,.]+)", "reference"),
]

async def extract_backlinks(content: str, source_vault: str, source_path: str) -> list[dict]:
    """Extract all outbound links from content"""
    links = []
    
    for pattern, link_type in LINK_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            if link_type == "wiki":
                target = match.group(1)
                links.append({
                    "type": "wiki",
                    "source": f"{source_vault}/{source_path}",
                    "target": f"{source_vault}/{slugify(target)}.md",
                    "display": match.group(0),
                })
            elif link_type == "entity":
                entity = match.group(1)
                # Find entity page across all vaults
                entity_location = await find_entity_page(entity)
                if entity_location:
                    links.append({
                        "type": "entity",
                        "source": f"{source_vault}/{source_path}",
                        "target": entity_location,
                        "entity": entity,
                    })
    
    return links

async def store_backlinks(links: list[dict]):
    """Store links in PostgreSQL for graph queries"""
    for link in links:
        await db.execute("""
            INSERT INTO knowledge_links (source, target, link_type, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (source, target) DO NOTHING
        """, link["source"], link["target"], link["type"])
        
        # Also create backlink (reverse direction)
        await db.execute("""
            INSERT INTO knowledge_links (source, target, link_type, is_backlink, created_at)
            VALUES ($1, $2, $3, true, NOW())
            ON CONFLICT (source, target) DO NOTHING
        """, link["target"], link["source"], link["type"])

async def get_related_notes(note_path: str, limit: int = 10) -> list[dict]:
    """Get notes linked to/from this note (bidirectional)"""
    rows = await db.fetch("""
        SELECT target as path, link_type, is_backlink,
               (SELECT title FROM vault_notes WHERE path = target) as title
        FROM knowledge_links
        WHERE source = $1
        UNION
        SELECT source as path, link_type, true as is_backlink,
               (SELECT title FROM vault_notes WHERE path = source) as title
        FROM knowledge_links
        WHERE target = $1
        LIMIT $2
    """, note_path, limit)
    return [dict(r) for r in rows]
```

**Multi-Vault Schema:**
```
vault/
├── personal/          # Private life, goals, journal, health
│   ├── goals/
│   ├── journal/
│   ├── health/
│   └── projects/
├── youtube/           # Consumed content, transcripts, takeaways
│   ├── transcripts/
│   ├── summaries/
│   └── references/    # Tools, techniques mentioned
├── wiki/              # General knowledge (factual, evergreen)
│   ├── concepts/
│   ├── people/
│   └── tools/
└── inbox/             # Staging area before filing
```

**Cross-Vault Linking:**
```markdown
---
id: "abc-123"
source_brain: "youtube"
links:
  - target: "personal/projects/fyp.md"
    type: "applies_to"
    direction: "outbound"
  - target: "wiki/fastapi.md"
    type: "mentions_tool"
  - target: "youtube/transcripts/karpathy-llm-tutorial.md"
    type: "related_concept"
entities: ["FastAPI", "Claude Code", "LLM", "FYP"]
---

# My React Learning Notes

I'm using [[Claude Code]] to build my FYP.  
See also: [my FYP project](../personal/projects/fyp.md)  
Tool mentioned: [FastAPI](../wiki/fastapi.md)
```

**Expected Result:** Every new note automatically linked to related notes. Graph queryable via API.

✅ **Checkpoint:** Create note mentioning "Claude Code" → auto-linked to existing "Claude Code" entity page in wiki/. Cross-vault link created.

---

## Task 7.0c — Knowledge Graph Visualization (Dashboard)

**Goal:** Visual graph of all notes/entities and their relationships, explorable in dashboard.

**Why:** Nate's Obsidian graph view lets you zoom from "everything" → "specific topic" → "specific note". We need equivalent for Heimdall.

**Implementation:**
```python
# atlas/api/knowledge_graph.py
@app.get("/graph/nodes")
async def get_graph_nodes(vault: str = None, query: str = None):
    """Return all nodes (notes + entities) for D3.js force graph"""
    sql = """
        SELECT 
            n.path as id,
            n.title as label,
            n.vault as group,
            n.node_type,
            COUNT(l.source) as connection_count
        FROM vault_notes n
        LEFT JOIN knowledge_links l ON n.path = l.source OR n.path = l.target
        WHERE ($1::text IS NULL OR n.vault = $1)
          AND ($2::text IS NULL OR n.title ILIKE '%' || $2 || '%')
        GROUP BY n.path
    """
    rows = await db.fetch(sql, vault, query)
    return {"nodes": [dict(r) for r in rows]}

@app.get("/graph/edges")
async def get_graph_edges(vault: str = None):
    """Return all edges (links between nodes)"""
    sql = """
        SELECT 
            source,
            target,
            link_type as type,
            is_backlink
        FROM knowledge_links
        WHERE ($1::text IS NULL 
               OR source LIKE $1 || '/%' 
               OR target LIKE $1 || '/%')
    """
    rows = await db.fetch(sql, vault)
    return {"edges": [dict(r) for r in rows]}

@app.get("/graph/neighborhood/{node_id}")
async def get_neighborhood(node_id: str, depth: int = 1):
    """Get N-hop neighborhood for focus+context view"""
    # Recursive CTE to find connected nodes up to depth N
    sql = """
        WITH RECURSIVE neighborhood AS (
            -- Base case: start node
            SELECT $1 as node, 0 as depth
            
            UNION
            
            -- Recursive step: follow links
            SELECT 
                CASE WHEN l.source = n.node THEN l.target ELSE l.source END,
                n.depth + 1
            FROM knowledge_links l
            JOIN neighborhood n ON l.source = n.node OR l.target = n.node
            WHERE n.depth < $2
        )
        SELECT DISTINCT node FROM neighborhood
    """
    return await db.fetch(sql, node_id, depth)
```

**Frontend (D3.js Force Graph):**
```typescript
// Dashboard Knowledge Graph Component
const KnowledgeGraph = () => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [focusNode, setFocusNode] = useState(null);
  
  useEffect(() => {
    // Fetch graph data
    Promise.all([
      fetch('/graph/nodes').then(r => r.json()),
      fetch('/graph/edges').then(r => r.json())
    ]).then(([n, e]) => {
      setNodes(n.nodes);
      setEdges(e.edges);
    });
  }, []);
  
  const handleNodeClick = (node) => {
    setFocusNode(node);
    // Fetch 2-hop neighborhood
    fetch(`/graph/neighborhood/${encodeURIComponent(node.id)}?depth=2`)
      .then(r => r.json())
      .then(neighbors => {
        // Highlight path, dim unrelated nodes
        highlightNeighborhood(node.id, neighbors);
      });
  };
  
  return (
    <div className="graph-container">
      <ForceGraph2D
        graphData={{ nodes, links: edges }}
        nodeAutoColorBy="group"  // Color by vault
        nodeVal="connection_count" // Size by connections
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        onNodeClick={handleNodeClick}
        nodeLabel="label"
      />
      {focusNode && <NodeSidebar node={focusNode} related={getRelated(focusNode.id)} />}
    </div>
  );
};
```

**Graph Features:**
- **Color coding:** Personal (blue), YouTube (red), Wiki (green), Inbox (gray)
- **Node size:** More connections = bigger node (hubs stand out)
- **Click to focus:** Dim unrelated nodes, show connection path
- **Filter by vault:** "Show only YouTube + cross-links to Personal"
- **Search integration:** Type "FastAPI" → graph zooms to that node + neighbors
- **Time slider:** "Show only notes from last 30 days" (animated graph evolution)

**Expected Result:** Interactive graph showing all knowledge connections. Click any node → see related notes from any vault.

✅ **Checkpoint:** Open graph view → see colored nodes for all vaults. Click "Claude Code" node → sidebar shows 5 linked notes (2 from youtube/, 1 from personal/, 1 from wiki/, 1 from goals/).

---

## Task 7.0d — Multi-Vault Architecture

**Goal:** Clean separation of concerns with explicit cross-vault linking rules.

**Vault Types:**

| Vault | Purpose | Write Permissions | Examples |
|-------|---------|-------------------|----------|
| `personal/` | Private life data | User + Heimdall | journal, goals, health, finances |
| `youtube/` | Content consumption | Heimdall auto | transcripts, summaries, takeaways |
| `wiki/` | Factual knowledge | User + Heimdall | tools, concepts, how-tos, people |
| `inbox/` | Staging area | User drop | unprocessed files, quick captures |
| `projects/` | Active work | User + Heimdall | code projects, FYP, side hustles |

**Cross-Vault Linking Rules:**
```python
ALLOWED_LINKS = {
    # Source vault: [allowed target vaults]
    "youtube": ["wiki", "personal"],      # YT content can reference tools/concepts or apply to life
    "personal": ["wiki", "youtube", "projects"],  # Life notes can reference anything
    "wiki": ["wiki", "youtube", "personal"],      # Wiki links widely
    "projects": ["wiki", "personal", "youtube"],  # Projects reference tools and life context
    "inbox": [],  # Inbox items get moved, not linked (temporary)
}

def validate_cross_vault_link(source_vault: str, target_vault: str) -> bool:
    return target_vault in ALLOWED_LINKS.get(source_vault, [])
```

**UI Organization:**
- **Vault tabs:** Personal | YouTube | Wiki | Projects | All
- **Default view:** "All" shows graph with color-coded vaults
- **Filter:** Click vault name to isolate + cross-links only

**Expected Result:** Clean mental model. YouTube consumption separate from personal goals, but easily connected via explicit links.

✅ **Checkpoint:** Create note in `youtube/` linking to `personal/goals/fyp.md` → link succeeds. Try linking `inbox/` to anything → blocked (inbox is staging only).

---

**Why:** Prevents vault pollution from:
- Multiple versions of same idea
- Duplicate flashcards from re-uploaded notes
- Redundant journal entries
- Re-ingested URLs

**Implementation:**
```python
# atlas/core/duplicates.py
from atlas.db.vector_store import search
from atlas.core.embeddings import cosine_similarity, embed

DUPLICATE_THRESHOLD = 0.95  # Cosine similarity

async def is_duplicate(text: str, table: str = "vector_memory") -> tuple[bool, str | None]:
    """Check if semantically similar content exists. Returns (is_dup, existing_id)."""
    results = await search(table, text, limit=1)
    if not results:
        return False, None
    
    # Re-embed to get exact comparison
    new_vec = await embed(text)
    existing_vec = results[0]["embedding"]  # Need to store raw vectors or re-fetch
    
    similarity = cosine_similarity(new_vec, existing_vec)
    if similarity > DUPLICATE_THRESHOLD:
        return True, results[0]["id"]
    return False, None

async def store_deduped(table: str, text: str, source_type: str, source_path: str = ""):
    is_dup, dup_id = await is_duplicate(text, table)
    if is_dup:
        log.info("Duplicate detected", existing_id=dup_id, new_source=source_path)
        # Option 1: Skip (default)
        # Option 2: Merge/update existing
        return dup_id
    return await store(table, text, source_type, source_path)
```

**Vault Integration:**
```python
# In vault_writer.py, before writing:
async def write_vault_file(path, content):
    # Check if similar content exists in vector_notes
    is_dup, existing = await is_duplicate(content, "vector_notes")
    if is_dup:
        # Create versioned filename: note.md → note-v2.md
        path = increment_version(path)
    # Proceed with write
```

**Expected Result:** Re-uploading same PDF → detected as duplicate → skipped or versioned.

✅ **Checkpoint:** Upload same file twice → second upload either skipped or versioned, never duplicated silently.

---

---

## Task 7.1 — Morning Brief Agent

**Goal:** 7am daily brief: schedule, goals, weather, health, budget. Conversational follow-up.

- Add `/morning-brief` endpoint
- Queries: Google Calendar, OpenWeatherMap, active goals, yesterday's health, budget snapshot
- n8n: 7am trigger → call endpoint → push notification
- Dashboard loads brief automatically on first open

✅ **Checkpoint:** Brief arrives at 7am. Open dashboard → brief loads. Ask follow-up → answered with context.

---

## Task 7.2 — Inbox Auto-Processor

**Goal:** Drop any file into `~/atlas-vault/inbox/` → LLM files and summarises it automatically.

- Watch inbox folder (background worker)
- LLM extracts: summary, suggested filename, correct vault folder
- **Duplicate check:** Compare against existing vault content before filing
- Moves file + creates companion note in Obsidian with timestamp + checksum
- Embeds summary into pgvector notes table

✅ **Checkpoint:** Drop PDF → processed within 60 seconds → note appears in correct Obsidian folder.

---

## Task 7.3 — SMART Goals System

**Goal:** Goals as Markdown with frontmatter. Dashboard tab. Atlas updates via chat.

- Goal template with: title, status, deadline, category, milestones
- Dashboard Goals tab: reads from Obsidian via `/goals` endpoint
- Atlas can mark milestones, update status, add progress notes via chat commands
- n8n weekly nudge: goal progress summary

✅ **Checkpoint:** Create goal. Update milestone via chat. Change visible in Goals tab and Obsidian.

---

## Task 7.4 — Auto-Journal

**Goal:** Nightly draft generated from context. Ready to review in Obsidian.

- n8n trigger: 9pm daily
- Pulls today's calendar + any notes you added + weather
- DeepSeek V4-Flash drafts entry (first person, reflective, blanks where uncertain)
- Saves to `~/atlas-vault/journal/YYYY-MM-DD-draft.md`
- Morning brief includes: "yesterday's draft is ready for review"

✅ **Checkpoint:** 9pm notification → open Obsidian → sensible draft exists for today.

---

## Task 7.5 — Budget System

**Goal:** Income rules, recurring payments, savings targets, affordability queries.

- `budget/rules.json`: income splits, fixed expenses, savings targets, recurring payments
- Dashboard Budget tab: current month snapshot
- n8n: 3 days before each payment → reminder notification
- Chat queries: "can I afford X?" → Atlas answers using real data

**Future upgrades (backlog):** CSV import, receipt OCR, visual analytics, anomaly alerts.

✅ **Checkpoint:** Ask "can I afford £300 this month?" → Atlas answers using your actual rules.json data.

---

## Task 7.6 — Study System

**Goal:** Upload notes → flashcards → quiz → spaced repetition.

- `/study/generate`: upload content → 10 flashcards returned + saved as JSON
- Dashboard Study tab: deck list, flip-card UI, mark pass/fail
- Spaced repetition: intervals increase on pass, reset on fail, stored in state file
- Auto-quiz: 10 random due cards, score tracked

✅ **Checkpoint:** Upload notes → flashcards generated → quiz works → intervals update per session.

---

## Task 7.7 — Maps & Journey Planning

**Goal:** Journey times, live bus arrivals, drop-off solver.

- Saved locations in `maps/locations.json`
- Google Maps Directions: "how long to [place]?" → answered in seconds
- TfL API: "next bus?" → live arrivals
- Drop-off solver: driver A→B, you need to get to C → optimal drop-off point with map link and timing

✅ **Checkpoint:** Drop-off solver returns optimal point, driver detour, your journey time, and a Google Maps link.

---

## Task 7.8 — Apple Health Bridge

**Goal:** Daily health data from iPhone synced to Atlas automatically.

- iOS Shortcut: runs at 7am, exports steps/sleep/heart rate as JSON
- POSTs to `/health/apple` endpoint
- Saved as `~/atlas-vault/health/YYYY-MM-DD.json`
- Included in morning brief context

✅ **Checkpoint:** Trigger shortcut manually → health JSON in vault → morning brief includes step count.

---

## Task 7.9 — Garmin Connect Sync

**Goal:** Richer health data: Body Battery, HRV, sleep stages, workout details.

- `python-garminconnect` library: 130+ API methods
- Pulls: steps, sleep, HRV, Body Battery, stress, VO2 max
- Saves as `~/atlas-vault/health/YYYY-MM-DD_garmin.json`
- n8n: 6:55am trigger → run sync before morning brief

✅ **Checkpoint:** `python garmin_sync.py` → Garmin JSON with Body Battery and HRV values in health folder.

---

## Task 7.10 — Health Insights

**Goal:** Atlas surfaces patterns across 14 days of check-ins and wearable data.

- `/health/checkin`: voice/text note → LLM extracts structured data (energy 1–5, mood 1–5, sleep quality, exercise)
- `/health/insights`: 14-day analysis → specific pattern observations (e.g. "better sleep → higher energy 4/5 times")
- Dashboard Health tab: recent check-ins + latest insight

✅ **Checkpoint:** 3+ check-ins → `/health/insights` returns a specific, actionable pattern observation.

---

## Task 7.11 — Meeting & Call Prep Agent

**Goal:** 30 mins before any calendar event, Atlas briefs you on relevant context.

- n8n: check calendar every 30 mins → if event in next 30 mins, trigger prep
- Searches Obsidian vault for notes mentioning attendees / event topic
- Formats: key context, last interaction notes, 2–3 talking points
- Push notification with brief before the meeting

✅ **Checkpoint:** Calendar event in 30 mins → notification arrives with relevant vault context.

---

## Task 7.12 — AI Reading Assistant

**Goal:** Any URL or text → summary + wiki note + flashcards automatically.

- `/read/process`: URL or pasted content → summary + key ideas + flashcard deck + tags
- Auto-saves wiki note to `~/atlas-vault/wiki/`
- Flashcard deck ready in Study tab immediately
- iOS Share extension: share URL from Safari → Atlas processes it

✅ **Checkpoint:** POST a URL → wiki note created + flashcard deck available in Study tab.

---

## Task 7.13 — Proactive Context Agent

**Goal:** Heimdall surfaces things without being asked. Feels like a real PA.

- Runs every 4 hours via n8n
- Checks: upcoming payments (3 days), goal deadlines (7 days), due flashcards, unreviewed journal drafts
- If items found → push notification with warm, concise nudge
- Silence if nothing needs attention

✅ **Checkpoint:** Goal deadline 3 days away → proactive nudge arrives without you asking.

---

## Task 7.14 — Habit & Mood Tracker

**Goal:** 30-second voice/tap daily check-in. Atlas notices patterns over time.

- Quick check-in input in dashboard (or via voice)
- LLM extracts: energy, mood, sleep quality, exercise, free notes
- Stored as JSON, visualised in Health tab
- Patterns surfaced in morning brief: *"You've been more energised on days after 7+ hours sleep"*

✅ **Checkpoint:** 5 check-ins → morning brief includes a specific pattern observation about your data.

---

---

# PHASE 8 — Production Hardening

---

## Task 8.0 — Vault Integrity (Timestamps & Checksums)

**Goal:** Prevent vault corruption, detect conflicts, enable safe concurrent writes.

**Why:** Multiple sources write to vault (auto-indexer, ingestion, manual Obsidian edits). Need to detect:
- Concurrent modifications
- File corruption (bitrot, partial writes)
- Out-of-sync state between pgvector and vault

**Implementation:**

**1. File Metadata in Frontmatter:**
```markdown
---
id: "uuid-here"
created_at: "2026-05-11T14:30:00Z"
modified_at: "2026-05-11T16:45:00Z"
checksum: "sha256:a1b2c3..."
source: "heimdall-ingest"
---

# Note content here
```

**2. Checksum on Write:**
```python
# atlas/core/vault_writer.py
import hashlib
from datetime import datetime

def compute_checksum(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]

async def write_vault_file(path: Path, content: str, source: str = "heimdall"):
    checksum = compute_checksum(content)
    frontmatter = f"""---
id: "{uuid.uuid4()}"
created_at: "{datetime.utcnow().isoformat()}"
checksum: "sha256:{checksum}"
source: "{source}"
---

"""
    full_content = frontmatter + content
    
    # Check for conflicts before writing
    if path.exists():
        existing = path.read_text()
        existing_checksum = extract_checksum(existing)
        if existing_checksum != checksum:
            # Conflict! File changed since we last saw it
            path = path.with_suffix(f".conflict-{datetime.now().strftime('%H%M%S')}.md")
    
    path.write_text(full_content)
    
    # Store checksum in pgvector for cross-check
    await store("vector_notes", content, source_type="vault", source_path=str(path), checksum=checksum)
```

**3. Integrity Checker:**
```python
# atlas/api/vault.py
@app.post("/vault/verify")
async def verify_vault_integrity():
    """Scan vault, verify checksums, report inconsistencies"""
    issues = []
    for file in vault_path.rglob("*.md"):
        content = file.read_text()
        stored_checksum = extract_checksum(content)
        actual_checksum = compute_checksum(extract_content(content))
        
        if stored_checksum != actual_checksum:
            issues.append({"file": str(file), "error": "checksum_mismatch"})
        
        # Check if file exists in pgvector
        db_record = await search("vector_notes", f"source_path:{file}", limit=1)
        if not db_record or db_record[0].get("checksum") != stored_checksum:
            issues.append({"file": str(file), "error": "db_sync_mismatch"})
    
    return {"status": "ok" if not issues else "issues_found", "issues": issues}
```

**Expected Result:** Every vault file has verifiable checksum. Conflicts create versioned files. `/vault/verify` detects drift.

✅ **Checkpoint:** Corrupt a vault file manually → `/vault/verify` detects checksum mismatch. Fix function restores from pgvector backup.

---

## Task 8.1 — Systemd Services

**Goal:** All Atlas services start automatically on boot.

Create `/etc/systemd/system/atlas-server.service` (and repeat for: `atlas-worker`, `atlas-inbox-watcher`, `atlas-cloudflare-tunnel`, `atlas-connector-daemon`):

```ini
[Unit]
Description=Atlas Server
After=network.target postgresql.service

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/atlas
ExecStart=/usr/bin/python3 -m uvicorn atlas.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/YOUR_USERNAME/atlas/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable atlas-server atlas-worker
sudo systemctl start atlas-server atlas-worker
```

✅ **Checkpoint:** Reboot server PC → all services running within 60 seconds. Dashboard accessible.

---

## Task 8.1b — Deep Health Monitoring System

**Goal:** Know when services are degrading before users notice. Full dependency health checks.

**Why:** Current `/health` is shallow. Need to detect:
- PostgreSQL connection pool exhaustion
- Redis memory pressure
- Ollama model not loaded
- External API rate limit approaching

**Implementation:**
```python
# atlas/api/health.py
@app.get("/health/deep")
async def deep_health():
    checks = {
        "postgres": await check_postgres(),
        "redis": await check_redis(),
        "ollama": await check_ollama(),
        "pgvector": await check_pgvector(),
        "external_apis": await check_external_apis(),
    }
    
    all_healthy = all(c["status"] == "ok" for c in checks.values())
    status_code = 200 if all_healthy else 503
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

async def check_postgres():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        start = time.time()
        await conn.fetchval("SELECT 1")
        latency = (time.time() - start) * 1000
        pool_size = len(connection_pool._holders)  # Track pool exhaustion
        return {"status": "ok", "latency_ms": latency, "pool_usage": pool_size}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def check_ollama():
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = r.json().get("models", [])
        has_embedder = any("nomic-embed" in m["name"] for m in models)
        return {"status": "ok", "models_loaded": len(models), "embedder_ready": has_embedder}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def check_external_apis():
    # Quick probe, don't burn quota
    results = {}
    for api_name, test_fn in [("deepseek", probe_deepseek), ("groq", probe_groq)]:
        try:
            results[api_name] = await test_fn()  # Lightweight HEAD request or token count check
        except Exception as e:
            results[api_name] = {"status": "unreachable", "error": str(e)}
    return results
```

**Dashboard Integration:**
- Health tab with green/yellow/red indicators
- Alert history (store failures in PostgreSQL)
- Auto-refresh every 30 seconds

**Expected Result:** `/health/deep` reveals problems before they cause user-facing errors.

✅ **Checkpoint:** Stop PostgreSQL container → `/health/deep` returns 503 with specific error in 2 seconds.

---

## Task 8.2 — Usage & Cost Dashboard Tab

**Goal:** See exactly what Atlas is spending on APIs and how each model is performing.

**Token & API Tracking** (from `usage_logs` table + Langfuse):
- Daily / weekly / monthly API spend per model
- Token counts (input + output) per model
- Average latency per model
- Error rates per model
- Tasks completed vs failed

**Resource Tracking:**
- GPU runtime (when local inference is running)
- Storage usage (LanceDB, Paperless archive, vault size)
- Per-task cost breakdown (prompt cost + embedding cost + any tool API calls)
- Total spend this month vs rolling average

**Dashboard Metrics Layout:**

*Daily view:*
- Total spend, total runtime, active task count

*Per-model view:*
- Response speed (p50 / p95 latency)
- Token usage (input vs output ratio)
- Error rate

Add "Usage" tab to dashboard with recharts bar/line charts. Export to CSV button for monthly review.

✅ **Checkpoint:** Usage tab shows last 7 days of model usage with per-model cost breakdown and today's total spend.

---

## Task 8.3 — Automated Backup

**Goal:** Vault, database, and vector store backed up nightly. Last 7 days retained.

Create `~/atlas/backup.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=~/atlas-backups
mkdir -p $BACKUP_DIR

pg_dump atlas > $BACKUP_DIR/postgres-$DATE.sql
cp -r ~/atlas-vault $BACKUP_DIR/vault-$DATE
cp -r ~/atlas-lancedb $BACKUP_DIR/lancedb-$DATE

# Keep last 7 days
find $BACKUP_DIR -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
find $BACKUP_DIR -name "postgres-*.sql" -mtime +7 -delete

echo "Backup complete: $DATE"
```

n8n: 3am daily → run backup script → push "backup complete" notification.

✅ **Checkpoint:** Run `backup.sh` manually → 3 backup items created. Verify postgres backup restores with `psql atlas < postgres-DATE.sql`.

---

---

# MILESTONES SUMMARY

| # | Milestone | Done When |
|---|---|---|
| M1 | **Database Foundation** | PostgreSQL + LanceDB running, all tables created, embedding service working |
| M2 | **Secure Server** | JWT auth, permission levels, config validation, async server |
| M3 | **Dashboard Live** | Next.js on Vercel, streaming chat, voice input, file upload — works from phone |
| M4 | **Memory Working** | Multi-chat, conversation summaries in LanceDB, RAG answers correctly |
| M5 | **Planner Active** | Capability planner replaces classifier, multi-tool execution works |
| M6 | **Observability** | Langfuse traces, structured logs, usage dashboard tab |
| M7 | **Streaming** | Live token rendering in dashboard, cancel button works |
| M8 | **Task System** | Tasks persist in PostgreSQL, Atlas creates tasks from natural language |
| M9 | **Morning Brief** | Daily brief at 7am, conversational follow-up, includes weather + goals |
| M10 | **Files Filing** | Drop file in inbox → processed → filed in vault within 60 seconds |
| M11 | **Goals & Journal** | Goals in dashboard, nightly draft appearing, Atlas updates via chat |
| M12 | **Budget Active** | Rules set, payment reminders firing, affordability queries working |
| M13 | **Study System** | Notes → flashcards → quiz → spaced repetition tracked |
| M14 | **Maps Working** | Journey queries, bus times, drop-off solver all answering correctly |
| M15 | **Health Connected** | Apple Health + Garmin syncing daily, insights generated from data |
| M16 | **VSCode Integrated** | Claude Code in VSCode, Remote Control from phone, CLAUDE.md files in place |
| M17 | **Connector Online** | Connector daemon registered, machine shows online in dashboard |
| M18 | **Proactive PA** | Nudges arriving without asking. Atlas feels like a real assistant. |
| M19 | **Dev Mode Live** | Code changes from iPhone via dashboard — diff generated, reviewed, applied, committed |

---

# PHASE 9 — Dev Mode (Late Stage Feature)
*Goal: Make code changes to Heimdall from iPhone via the dashboard. No laptop needed for quick edits.*

> **⚠️ PRIORITY: LOW** — This is a late-stage convenience feature, not MVP. 
> 
> **Why push back:** Security risk (LLM-generated code running on server) for marginal benefit. On PC, use VSCode. On iPhone, use Claude Code remote control (Phase 6.2) for now.
>
> **Build only after:** Auth is battle-tested, all core features stable, and you specifically need mobile edits while away from desk.

> **Design intent:** Mobile-first UI. Auth (Phase 1B) must be complete before building this.

---

## Task 6B.1 — Dev Mode Panel (Dashboard)

**Goal:** A mobile-optimised panel in the Heimdall dashboard where you describe a code change in plain English, review the generated diff, and approve it to be applied on the server.

**Hard dependency:** JWT auth (Task 1B.1) must be complete. Dev Mode must be gated — no token, no access.

**Steps:**

1. Add a `Dev Mode` tab/panel to the dashboard — hidden on desktop (`@media (min-width: 1024px) { display: none }`), visible on mobile.
2. UI components:
   - File picker (dropdown of repo files, or free-text path)
   - Prompt textarea: *"What change do you want to make?"*
   - **Generate Diff** button → calls `/dev/suggest`
   - Diff viewer (coloured `+`/`-` lines, monospace, scrollable)
   - **Apply** / **Discard** buttons
3. Add `/dev/suggest` endpoint to FastAPI:

```python
# atlas/api/dev.py
@router.post("/dev/suggest")
async def suggest_change(body: DevRequest, user=Depends(get_current_user)):
    # body: { file_path: str, instruction: str, current_content: str }
    # Call Groq/DeepSeek with system prompt: "You are a code editor. Return a unified diff only. No prose."
    # Return: { diff: str, file_path: str }
```

4. Add `/dev/apply` endpoint:

```python
@router.post("/dev/apply")
async def apply_change(body: ApplyRequest, user=Depends(get_current_user)):
    # body: { file_path: str, diff: str }
    # Validate file_path is within /opt/heimdall (no path traversal)
    # Apply patch via subprocess: patch -p1 < diff
    # Run: git add <file>, git commit -m "Dev Mode: <short description>"
    # Return: { success: bool, commit_hash: str }
```

5. Add `/dev/files` endpoint: returns list of `.py` files in `/opt/heimdall/atlas/` for the file picker.

**Safety rules (non-negotiable):**
- All `/dev/*` routes require valid JWT
- `file_path` must resolve within `/opt/heimdall` — reject anything with `..` or outside project root
- `patch` is applied via `subprocess` with `check=True` — if it fails, return error, do not partially apply
- Every apply creates a git commit — full audit trail, easy rollback with `git revert`
- Never auto-apply — user must press **Apply** explicitly

**Expected Result:** On iPhone, open dashboard → Dev Mode tab → describe change → see diff → tap Apply → change committed on server.

**Test Method:**
```bash
# 1. Login and get token
curl -X POST http://100.113.79.103:8000/auth/login -d '{"password": "YOUR_PW"}'

# 2. Suggest a change
curl -X POST http://100.113.79.103:8000/dev/suggest \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "atlas/api/chat.py", "instruction": "Add a comment at the top of the file"}'

# 3. Apply the diff
curl -X POST http://100.113.79.103:8000/dev/apply \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "atlas/api/chat.py", "diff": "<diff from previous step>"}'

# 4. Verify git log
git -C /opt/heimdall log --oneline -3
```

**Rollback Plan:** `git revert HEAD` on server. All applies are committed so nothing is unrecoverable.

✅ **Checkpoint:** From iPhone Safari on Tailscale, open dashboard → Dev Mode visible → describe trivial change → diff renders correctly → Apply commits it → `git log` shows the commit.

---

## Task 6B.2 — Safety Enhancements (Optional hardening)

**Goal:** Extra guardrails once basic Dev Mode is working.

- **Dry-run mode:** Apply patch to a temp copy, run `python -m py_compile` on it, only write to disk if syntax is valid
- **Restart hook:** After apply, optionally `systemctl restart heimdall` (opt-in toggle in UI)
- **Diff size limit:** Reject diffs over 200 lines — large changes should be done in VSCode
- **Session log:** Store each Dev Mode action (file, instruction, diff, commit hash) to PostgreSQL for audit

✅ **Checkpoint:** Syntactically broken patch is rejected before touching disk. Restart toggle works. Audit log visible in dashboard.

---

# NOTES

- **Start with Phase 1A before anything else.** The database and embedding foundation affects every feature above it.
- **Never commit `.env`.** Enforced by `config.py` at startup.
- **DeepSeek V4 865GB** = download size of weights for self-hosting. You're calling the API. Nothing to download. Cost is pennies.
- **Apple Health** has no cloud API — iOS Shortcut bridge is the only method. Works reliably in practice.
- **Garmin** `python-garminconnect` is an unofficial library. Fine for personal use.
- **Old server** — share the model number when ready. Will advise exactly what it can run.
- **Streaming** is one of the highest-impact UX improvements. Prioritise Phase 3B once Phase 1A–2B is solid.
- **VSCode Connector Daemon** is Phase 6 work — don't start it until memory and task systems are stable.
- **Wake word** (always-on voice) deferred to post-hardware-upgrade. Architecture supports it from day one.
- **Budget upgrades** (CSV import, receipt OCR, visual analytics) are backlog — add after core budget system is working.

---

*Document version: 2.1 — May 2026*
*Merged: ARIA Architecture Revision + VSCode Connector Additions*
*Atlas — Build something you'd actually use every day.*
