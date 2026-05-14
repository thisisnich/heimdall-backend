# Heimdall Server Setup Progress Tracker

## 📊 Overall Progress: 75% Complete

**System:** Heimdall Personal AI Server  
**Hardware:** Dell PowerEdge R620 (32 cores, 60GB RAM)  
**OS:** Ubuntu Desktop 26.04 LTS  
**Location:** /opt/heimdall  
**Last Updated:** May 14, 2026 (04:19 UTC)

**Note:** Previous progress tracking was obsolete. This document now reflects actual implementation state based on codebase audit.

---

## ✅ **Phase 1A: Server Foundation** 
**Status: 100% Complete**

### ✅ **Step 1: Initial Server Setup**
#### Physical Setup
- [x] Connect server to power (both PSUs)
- [x] Connect monitor, keyboard, mouse
- [x] Connect Ethernet to router
- [x] Power on server
- [x] Access BIOS (F2) and iDRAC (Ctrl+E)
- [x] Configure boot order for USB installation

#### OS Installation
- [x] Create Ubuntu 26.04 LTS bootable USB
- [x] Boot from USB and install Ubuntu Desktop
- [x] Set hostname: `heimdall-server`
- [x] Create user: `heimdall`
- [x] Enable SSH server during install
- [x] Complete installation and reboot

#### Post-Installation Configuration
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git vim htop net-tools ipmitool nmap

# Install Docker
sudo apt install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```
- [x] System updated and upgraded
- [x] Essential packages installed
- [x] Docker installed and enabled
- [x] Docker Compose installed
- [x] User added to docker group
- [x] **Verified:** `docker ps` and `docker-compose --version` work

### ✅ **Step 2: Network Configuration**
#### Network Setup
- [x] Verify network interface (eno1)
- [x] Check current IP: 192.168.18.187
- [x] Note MAC address: 90:b1:1c:46:b6:a0
- [x] Router DHCP reservation configured
- [x] **Verified:** IP remains stable after reboots

#### SSH Configuration
```bash
# On server - create .ssh directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add authorized_keys
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGpTDH5Iz7lFu+/pI3OVE8Varqf0uXTPVIj9iLbq6Yw4 heimdall@heimdall-server" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```
- [x] SSH key-based authentication configured
- [x] **Verified:** Passwordless SSH works from Windows

#### Tailscale VPN Setup
```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
- [x] Tailscale installed on server
- [x] Tailscale authenticated
- [x] Tailscale IP assigned: 100.113.79.103
- [x] **Verified:** `tailscale status` shows connected
- [x] **Verified:** Can SSH via Tailscale IP

### ✅ **Step 3: Performance Tuning**
#### System Optimization
```bash
# Check resources
nproc                    # 32 cores
free -h                  # 60GB RAM

# Create swap file
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo 'swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
- [x] 8GB swap file created
- [x] Swap configured in /etc/fstab
- [x] **Verified:** `free -h` shows 8GB swap
- [x] **Verified:** All 32 cores visible
- [x] **Verified:** 60GB RAM available

### ✅ **Step 4: iDRAC Remote Management (Optional)**
#### iDRAC Configuration
```bash
# Load IPMI modules
sudo modprobe ipmi_devintf
sudo modprobe ipmi_si

# Check iDRAC configuration
sudo ipmitool lan print
```
**iDRAC Status:**
- IP: 192.168.18.120 (configured)
- MAC: 74:86:7a:d1:12:4c
- Status: Unreachable from network
- BMC cold reset attempted
- **Issue:** Requires physical access to diagnose
- **Workaround:** Using SSH and Tailscale for remote access
- **Resolution:** Deferred - not blocking core functionality

---

## ✅ **Phase 1A: Database & Models Setup** 
**Status: 100% Complete**

### ✅ **Task 1A.1 — Connect to PostgreSQL**
**Completed:** Virtual environment created, dependencies installed, database connection verified

```bash
# Virtual environment setup
cd /opt/heimdall
python3 -m venv venv
source venv/bin/activate

# Dependencies installed
pip install sqlalchemy psycopg[binary] asyncpg python-dotenv pgvector

# Connection verified
python test_db.py
# Output: Connected to: PostgreSQL 15.17 (Debian 15.17-1.pgdg13+1)...
```
- [x] Virtual environment created at `/opt/heimdall/venv`
- [x] Python dependencies installed
- [x] `.env` file created with DATABASE_URL
- [x] Connection test passed
- [x] **Verified:** `python test_db.py` connects successfully

### ✅ **Task 1A.2 — Create SQLAlchemy Models**
**Completed:** All 8 database tables created in PostgreSQL

**Files created:**
- `atlas/db/models.py` — SQLAlchemy models (User, Chat, Message, Task, MemoryEntry, UsageLog, Machine, Entity)
- `init_db.py` — Database initialization script

**Tables created:**
```
 Schema |      Name      | Type  |  Owner
--------+----------------+-------+----------
 public | chats          | table | heimdall
 public | entities       | table | heimdall
 public | machines       | table | heimdall
 public | memory_entries | table | heimdall
 public | messages       | table | heimdall
 public | tasks          | table | heimdall
 public | usage_logs     | table | heimdall
 public | users          | table | heimdall
```
- [x] `atlas/db/models.py` created with all 8 models
- [x] `init_db.py` created
- [x] Tables created via `python init_db.py`
- [x] **Verified:** `\dt` shows all 8 tables

### ⚠️ **Task 1A.3 — Vector Database Setup**
**Status:** Hardware limitation encountered - **Solved with pgvector**

**Issue:** Dell R620 Xeon E5-2600 lacks AVX2 instruction set required by PyArrow/LanceDB
```
Illegal instruction (core dumped) - PyArrow requires AVX2
```

**Solution:** Using **pgvector** (PostgreSQL extension) instead of LanceDB
- ✅ pgvector runs inside existing PostgreSQL container (no AVX2 requirement)
- ✅ Same vector search capabilities
- ✅ Simpler architecture (one less service)
- ✅ Compatible with R620 hardware

**Implementation:**
```bash
# Enable pgvector in PostgreSQL
docker exec heimdall-postgres psql -U heimdall -d heimdall -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Pull embedding model from Ollama
docker exec heimdall-ollama ollama pull nomic-embed-text

# Test embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test embedding"}'
```
- [x] Hardware limitation identified (R620 Xeon E5, no AVX2)
- [x] **Solution:** Switched to pgvector (PostgreSQL native)
- [x] Switched docker-compose postgres image → `pgvector/pgvector:pg15`
- [x] pgvector extension enabled (`vector` v0.8.2)
- [x] `nomic-embed-text` model pulled via Ollama
- [x] `atlas/db/vector_store.py` created with `embed_text`, `init_vector_tables`, `store`, `search`, `search_all`
- [x] 4 vector tables created: `vector_memory`, `vector_notes`, `vector_chat_summaries`, `vector_code_chunks`
- [x] End-to-end verified: store → semantic search returns correct results
- [x] `vector_explorer.py` — web UI for visual testing (FastAPI, port 7860)
- [x] `docs/VECTOR-SEARCH.md` — explainer doc on how embeddings + pgvector work
- [x] **Verified:** `search_all("saving for computer")` returns PC build entry at distance 0.42

---

## ✅ **Phase 1B: Core Services Deployment**
**Status: 100% Complete**

### ✅ **Step 5: Docker Compose Environment Setup**
#### Directory Structure
```bash
# Create project directory
sudo mkdir -p /opt/heimdall
sudo chown heimdall:heimdall /opt/heimdall
cd /opt/heimdall
```
- [x] /opt/heimdall directory created
- [x] Proper ownership set
- [x] Virtual environment created

#### Docker Compose Configuration
Create `/opt/heimdall/docker-compose.yml`:
```yaml
version: '3.8'

services:
  # PostgreSQL Database (with pgvector)
  postgres:
    image: pgvector/pgvector:pg15
    container_name: heimdall-postgres
    environment:
      POSTGRES_DB: heimdall
      POSTGRES_USER: heimdall
      POSTGRES_PASSWORD: heimdall_secure_2026
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U heimdall"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Ollama for Local LLMs
  ollama:
    image: ollama/ollama:latest
    container_name: heimdall-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    environment:
      - OLLAMA_HOST=0.0.0.0

  # Redis for Caching & Task Queue
  redis:
    image: redis:7-alpine
    container_name: heimdall-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

  # Langfuse (Observability)
  langfuse:
    image: langfuse/langfuse:latest
    container_name: heimdall-langfuse
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgresql://heimdall:heimdall_secure_2026@postgres:5432/heimdall
      - NEXTAUTH_SECRET=change-me-in-production
      - SALT=change-me-in-production
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
  ollama_data:
  redis_data:
```
- [x] docker-compose.yml created
- [x] All 5 services configured
- [ ] **Next:** Deploy containers (run `docker-compose up -d`)

### 📋 **Step 6: Deploy Core Services**
**Current Status:** Configuration complete, ready to deploy

```bash
# Start all services
cd /opt/heimdall
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```
#### Service Deployment Checklist
- [x] **PostgreSQL** - Port 5432 - Status: RUNNING (with pgvector)
- [x] **Ollama** - Port 11434 - Status: RUNNING
- [x] **Redis** - Port 6379 - Status: RUNNING
- [ ] **Langfuse** - Port 3001 - Status: RUNNING (optional)

**Note:** LanceDB removed - R620 hardware lacks AVX2. Using pgvector in PostgreSQL instead.

#### PostgreSQL Setup
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U heimdall -d heimdall

# Create extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

# Verify
\dt
\q
```
- [ ] PostgreSQL database initialized
- [ ] Extensions installed
- [ ] Connection tested

#### Ollama Model Downloads
```bash
# Download models
curl http://localhost:11434/api/pull -d '{"name": "qwen3.5:7b"}'
curl http://localhost:11434/api/pull -d '{"name": "nomic-embed-text"}'
curl http://localhost:11434/api/pull -d '{"name": "llama3.2"}'

# List models
curl http://localhost:11434/api/tags
```
- [ ] Qwen3.5:7b model downloaded
- [ ] nomic-embed-text model downloaded
- [ ] llama3.2 model downloaded
- [ ] **Verified:** Models respond to API calls

#### Redis Testing
```bash
# Test Redis
docker-compose exec redis redis-cli ping
# Expected: PONG

# Test persistence
docker-compose exec redis redis-cli set test_key "hello"
docker-compose exec redis redis-cli get test_key
```
- [ ] Redis responding to pings
- [ ] Persistence working

#### pgvector Testing
```bash
# Enable pgvector extension
docker exec heimdall-postgres psql -U heimdall -d heimdall -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Test vector operations
# (Will add test after embedding model is ready)
```
- [ ] pgvector extension enabled
- [ ] Vector search functions working

#### Langfuse Setup
- [ ] Access Langfuse UI at http://192.168.18.187:3001
- [ ] Complete initial setup
- [ ] Generate API keys
- [ ] Add keys to environment

---

## 🔄 **Phase 1C: Heimdall Application**
**Status: 0% Complete**

### 📋 **Application Deployment**
- [ ] Heimdall API service container
- [ ] Environment variables configured
- [ ] Application networking
- [ ] Health checks and monitoring

### 📋 **LLM Integration**
- [ ] Ollama models downloaded
- [ ] LLM API endpoints configured
- [ ] Model performance testing

---

## 🔄 **Phase 1D: Data & Storage**
**Status: 0% Complete**

### 📋 **Vector Database (pgvector)**
- [ ] pgvector extension enabled in PostgreSQL
- [ ] Vector search functions created
- [ ] Data ingestion pipeline

**Note:** Using pgvector instead of LanceDB due to R620 Xeon E5 AVX2 limitation

### 📋 **Memory System**
- [ ] Memory tables created
- [ ] Semantic search configured
- [ ] Chat summaries setup

---

## 🔄 **Phase 1E: Remote Access**
**Status: 20% Complete**

### 🔄 **Remote Connectivity**
- [x] SSH access working
- [x] SSH key authentication
- [ ] Tailscale VPN setup
- [ ] Web dashboard access
- [ ] API endpoint access

---

## 🚧 **Current Issues & Blockers**

### 🔴 **Critical Issues**
- **iDRAC Unreachable**: 192.168.18.120 not responding (needs physical access)
- **Static IP**: Server IP not reserved (potential DHCP conflicts)

### 🟡 **Medium Priority**
- **Markdown rendering**: ✅ Done — chat responses rendered via marked.js

---

## ✅ **Phase 1C: Heimdall FastAPI Application**
**Status: 100% Complete**

- [x] `main.py` — FastAPI app with CORS, startup hooks, all routers mounted
- [x] `atlas/api/chat.py` — `POST /chat` with memory context injection, multi-provider routing
- [x] `atlas/api/memory.py` — `GET /memory/search`, `POST /memory/store`, `GET /memory/tables`
- [x] `atlas/api/health.py` — `GET /health` checks Postgres + Ollama
- [x] `atlas/api/models.py` — `GET /models` returns local + cloud model list with availability
- [x] `atlas/api/dashboard.py` — full web dashboard served at `/dashboard` (port 8000)
- [x] `atlas/services/ollama_service.py` — Ollama chat + model list
- [x] `atlas/services/deepseek_service.py` — DeepSeek V3 Flash + Pro
- [x] `atlas/services/groq_service.py` — Llama 4 Scout, Llama 3 70B/8B via Groq
- [x] Multi-model selector UI with local/cloud sections, speed + cost badges
- [x] API keys configured: `DEEPSEEK_API_KEY`, `GROQ_API_KEY` in `.env`
- [x] Models available: `qwen3:1.7b` (fast local), `qwen3:8b` (slow local), DeepSeek Flash/Pro, Groq Llama 4 Scout, Llama 3 70B/8B

---

## 📝 **Next Immediate Tasks**

1. ✅ **Markdown rendering** — chat responses rendered via marked.js
2. ✅ **Tailscale** — active at `100.113.79.103`, dashboard reachable remotely
3. ✅ **Streaming responses** — SSE stream via `/chat/stream`, tokens render word-by-word in dashboard
4. **Task 1A.5 — Paperless-ngx** — document OCR container (optional, 45 min)
5. ✅ **`atlas/core/embeddings.py`** — `embed()`, `embed_batch()`, `cosine_similarity()` — verified 768-dim
6. **Intermediary agent** — orchestrator that decides which memories to save, which sub-agents/models to invoke per request, and routes tasks accordingly (core to Phase 2B Capability Planner)
7. **Overall dashboard rebuild** — unified dashboard with tabbed/routed pages: **Chat**, **Memory browser**, **System debug** (logs, Docker status, model health), and **Progress** (project roadmap tracker). Must follow `docs/SKILL(2).md` design guidelines: bold aesthetic direction, distinctive typography, cohesive color theme, motion/micro-interactions, no generic AI slop. Production-grade, visually striking, memorable.

---

## 📋 **Commands & References**

### **Server Access**
```bash
ssh heimdall@192.168.18.187
cd /opt/heimdall
```

### **Docker Status**
```bash
docker ps
docker-compose --version
```

### **Service Management**
```bash
# Start services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 📊 **Resource Usage**

- **CPU**: 32 cores (excellent for parallel processing)
- **RAM**: 60GB (plenty for LLM workloads)
- **Storage**: Configurable based on needs
- **Network**: 192.168.18.187 (static IP recommended)

---

## 🔄 **Phase 2A: Memory & Retrieval System**
**Status: 0% Complete**

### 📋 **Semantic Retrieval (pgvector)**
#### Setup Tasks
- [ ] Configure LanceDB tables:
  - `memory` — general facts and context (pgvector table)
  - `notes` — Obsidian vault content (pgvector table)
  - `chat_summaries` — compressed conversation history (pgvector table)
  - `code_chunks` — indexed project code
- [ ] Set up embedding pipeline (nomic-embed-text via Ollama)
- [ ] Configure 768-dimensional embeddings
- [ ] Implement similarity search functions

#### Code Implementation
```python
# atlas/core/embeddings.py
async def embed_text(text: str) -> list[float]:
    """Generate embedding using local Ollama"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text}
        )
        return response.json()["embedding"]

async def search_all(query: str, limit: int = 4) -> list[dict]:
    """Search across all memory types"""
    embedding = await embed_text(query)
    # Search pgvector tables in PostgreSQL
    results = await pgvector.search(embedding, limit)
    return results
```
- [ ] Embedding function implemented
- [ ] Search function implemented
- [ ] **Test:** Store fact → Search returns it

### 📋 **Hierarchical Memory System**
#### Memory Types
| Type | Purpose | Implementation |
|------|---------|----------------|
| **Working Memory** | Current conversation context | Session storage |
| **Episodic Memory** | Past conversation summaries | pgvector + PostgreSQL |
| **Semantic Memory** | Facts, entities, relationships | pgvector + Entity graph |
| **Short-term Memory** | Recent 24h activity | Redis rolling window |

#### Implementation Tasks
- [ ] Create memory_manager.py
- [ ] Implement context injection
- [ ] Build retrieval hierarchy (Layer 1-5)
- [ ] Set up entity tracking

### 📋 **Chat Summarization**
```python
# Trigger: After every 15th message
async def summarise_chat(chat_id: str):
    # Fetch last 20 messages
    # Generate summary with DeepSeek
    # Store in pgvector chat_summaries table
    # Extract and store entities
```
- [ ] Summarization worker created
- [ ] Trigger configured (every 15 messages)
- [ ] **Test:** 15+ messages → summary created

### 📋 **Entity Graph**
#### Tracked Entities
- People (contacts, colleagues, friends)
- Projects (work, personal, learning)
- Locations (home, work, gym, frequent places)
- Organizations (companies, groups)
- Recurring goals

#### Implementation
```python
# atlas/core/entity_graph.py
class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    type = Column(String)  # person, project, location, org
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    relationships = Column(JSON)  # connected entities
```
- [ ] Entity table created
- [ ] Extraction from chat summaries
- [ ] Relationship tracking
- [ ] Query endpoint: `GET /entities?type=project`

---

## 🔄 **Phase 2B: Capability Planner & Tool System**
**Status: 50% Complete**

### ✅ **Capability Planner**
#### Purpose
Replace simple classifier with intelligent planner that determines required capabilities per request.

#### Implementation
- [x] Planner module created (`atlas/core/planner.py`)
- [x] All capabilities defined (quick, retrieval, calendar, writing, reasoning, code, complex, ingest)
- [x] Model routing configured (qwen3:1.7b, groq-llama4-scout, deepseek-flash, deepseek-pro)
- [x] Memory table selection logic
- [x] Used in chat endpoint (via `make_plan` import)
- [x] **Verified:** Planner returns sensible JSON plans

#### Example Plans
| User Message | Capabilities | Model |
|-------------|--------------|-------|
| "hey how are you" | quick | groq-llama4-scout |
| "what was that project i mentioned last week" | retrieval | groq-llama4-scout |
| "write a cover letter for a software engineering internship" | writing | deepseek-flash |
| "ingest my inbox" | ingest | groq-llama4-scout |
| "what's on my schedule today" | calendar | groq-llama4-scout |

### 📋 **Tool Execution Engine**
- [ ] Tool registry implemented (NOT DONE)
- [ ] Permission system working (NOT DONE - auth exists but no tool-level permissions)
- [ ] All tools registered (NOT DONE)
- [ ] **Test:** Two tools requested → both execute → results in response (NOT DONE)

#### Built-in Tools (PLANNED, NOT IMPLEMENTED)
| Tool | Purpose | Permission | Status |
|------|---------|------------|--------|
| `get_weather` | Current weather | safe | NOT DONE |
| `get_directions` | Journey time/routes | safe | NOT DONE |
| `get_bus_times` | Live TfL bus data | safe | NOT DONE |
| `get_calendar` | Google Calendar events | safe | PARTIAL (API exists) |
| `search_notes` | Search Obsidian vault | safe | DONE (via memory search) |
| `search_memory` | Search all memory | safe | DONE |
| `read_goal` | Fetch SMART goal | safe | PARTIAL (API exists) |
| `update_goal` | Update goal progress | safe | PARTIAL (API exists) |
| `read_budget` | Check budget status | safe | PARTIAL (API exists) |
| `get_health` | Garmin/Apple Health data | safe | NOT DONE |
| `create_task` | Add to task list | safe | NOT DONE |
| `read_file` | Read code/file | safe | NOT DONE |
| `write_file` | Edit file | confirm_required | NOT DONE |
| `git_commit` | Commit changes | confirm_required | NOT DONE |
| `git_push` | Push to remote | trusted | NOT DONE |
| `run_tests` | Execute test suite | trusted | NOT DONE |
| `deploy` | Deploy application | autonomous | NOT DONE |

### 📋 **Permission System**
#### Permission Levels (PLANNED)
| Level | Can Do | Cannot Do |
|-------|--------|-----------|
| **SAFE** | Read, analyse, suggest | Write files, push, deploy, delete |
| **CONFIRM_REQUIRED** | Commit, send messages, write files | Deploy, run migrations |
| **TRUSTED** | Commit, push, run terminal | Merge, run migrations |
| **AUTONOMOUS** | Deploy, merge, run migrations | Nothing blocked |

- [x] JWT auth implemented (`atlas/api/auth.py`)
- [ ] Permission decorator implemented (NOT DONE)
- [ ] Dashboard controls created (NOT DONE)
- [ ] Session-level configuration (NOT DONE)
- [ ] **Test:** Mode changes respected by tools (NOT DONE)

---

## 🔄 **Phase 3A: Observability & Monitoring**
**Status: 0% Complete**

### 📋 **Structured Logging**
```python
# atlas/core/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger()

# Usage:
log.info("model_call", model="deepseek/v4-flash", tokens=450, latency_ms=820)
log.error("tool_failed", tool="get_directions", error=str(e))
```
- [ ] Structlog configured
- [ ] JSON logging enabled
- [ ] Log entries added to all model calls
- [ ] Log entries added to all tool executions
- [ ] **Test:** Chat message → log shows model, tokens, latency

### 📋 **Langfuse Integration**
#### Setup
```bash
# Langfuse already in docker-compose.yml
# Access at http://192.168.18.187:3001
```

#### Tracing Implementation
```python
from langfuse import Langfuse
lf = Langfuse()

async def call_model_traced(message: str, model: str) -> str:
    trace = lf.trace(name="atlas_chat")
    gen = trace.generation(name="call", model=model, input=message)
    response = await call_model(message, model=model)
    gen.end(output=response)
    return response
```

- [ ] Langfuse container running
- [ ] API keys configured
- [ ] Tracing wrapper implemented
- [ ] **Test:** 3 messages → 3 traces visible in Langfuse UI

### 📋 **Dashboard Metrics**
#### Real-time Stats
- Requests per minute
- Average latency by model
- Token usage per model
- Tool execution counts
- Error rates
- Cost tracking

- [ ] Metrics endpoint created
- [ ] Dashboard widgets implemented
- [ ] **Test:** Metrics update in real-time

---

## ✅ **Phase 3B: Streaming Responses**
**Status: 100% Complete**

### ✅ **Streaming API Endpoint**
- [x] Streaming endpoint implemented (`POST /chat/stream` in atlas/api/chat.py)
- [x] SSE (Server-Sent Events) transport
- [x] Token-by-token streaming from DeepSeek, Groq, Ollama
- [x] Frontend streaming UI in dashboard (marked.js rendering)
- [x] Cancel button working
- [x] **Verified:** `curl -N` shows tokens arriving progressively

---

## 🔄 **Phase 4: External Integrations**
**Status: 0% Complete**

### 📋 **Maps & Navigation**
#### Google Maps API
```python
# atlas/services/maps_service.py
async def get_directions(origin: str, destination: str) -> dict:
    """Get journey time and route from Google Maps"""
    # Uses Google Maps Directions API
    # Free: 10k requests/month
    
async def get_weather(location: str = "home") -> str:
    """Current weather from OpenWeatherMap"""
    # Free: 1k requests/day
```

#### TfL API (London)
```python
async def get_bus_times(stop_id: str) -> list[dict]:
    """Live bus arrival times from TfL"""
    # Free API
```

- [ ] Google Maps API key configured
- [ ] OpenWeatherMap API key configured
- [ ] TfL API integrated
- [ ] **Test:** "How long to work?" → returns journey time

### 📋 **Calendar Integration**
```python
# atlas/services/calendar_service.py
async def get_calendar_events(date: datetime) -> list[dict]:
    """Fetch Google Calendar events"""
    # Google Calendar API
    # Free
```

- [ ] Google Calendar API enabled
- [ ] OAuth flow configured
- [ ] **Test:** "What's on my calendar?" → returns events

### 📋 **Health Data**
```python
# atlas/services/health_service.py
async def get_garmin_data() -> dict:
    """Steps, sleep, HRV from Garmin Connect"""
    # Uses python-garminconnect
    
async def get_apple_health() -> dict:
    """Health data via iOS Shortcut bridge"""
```

- [ ] Garmin Connect integrated
- [ ] Apple HealthKit bridge created
- [ ] **Test:** "How did I sleep?" → returns sleep data

### 📋 **Document Management (Paperless)**
```python
# atlas/services/paperless_service.py
async def upload_document(file: bytes, tags: list[str]) -> str:
    """Upload to Paperless-ngx for OCR and archive"""
    
async def search_documents(query: str) -> list[dict]:
    """Search OCR'd documents"""
```

- [ ] Paperless-ngx container deployed
- [ ] API integration complete
- [ ] **Test:** Upload receipt → searchable in 30 seconds

### 📋 **VSCode Connector**
#### Architecture
```
Heimdall API
    ↓
VSCode Connector Daemon (persistent, per machine)
    ↓
VSCode Extension (workspace operations)
    ↓
Local Workspace + Local Models
```

#### Capabilities
- **Workspace Sync:** Detect repo changes, update project index
- **File Operations:** Read, patch, overwrite, create, delete
- **Terminal Execution:** Run tests, builds, scripts
- **Git Operations:** Stage, commit, branch, push

#### Machine Registry
```python
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

- [ ] VSCode Connector Daemon created
- [ ] VSCode Extension published
- [ ] Machine registry implemented
- [ ] **Test:** "Commit changes with message X" → commit made

---

## 🔄 **Phase 5: Dashboard & UI**
**Status: 0% Complete**

### 📋 **Next.js Dashboard**
#### Pages
- `/` — Main chat interface
- `/memory` — Search and browse memory
- `/entities` — People, projects, locations
- `/goals` — SMART goals tracking
- `/health` — Health data dashboard
- `/budget` — Budget overview
- `/settings` — Configuration

#### Features
- [ ] PWA support (installable on iPhone)
- [ ] Dark mode (default)
- [ ] Mobile-responsive
- [ ] Real-time updates
- [ ] Offline support (basic)

### 📋 **Chat Interface**
#### Components
- Message bubble (user/assistant)
- Streaming text display
- Tool execution indicators
- File attachments
- Voice input (future)

#### Commands
- `/search [query]` — Search all memory
- `/goal [name]` — Show goal details
- `/health` — Show health summary
- `/budget` — Show budget status
- `/settings` — Open settings

---

## ✅ **Phase 6: Obsidian Vault Integration**
**Status: 100% Complete**

### ✅ **Vault Structure**
```
vault/
├── work/           ← Uni, FYP, courses, job, side projects
│   ├── fyp/
│   ├── courses/
│   └── projects/
├── personal/       ← Life: goals, journal, health, finance
│   ├── goals/
│   ├── journal/
│   └── health/
├── kb/             ← Knowledge base: concepts, tools, people, references
│   ├── concepts/
│   ├── tools/
│   ├── people/
│   └── entities/
└── inbox/          ← Drop zone — auto-classified and moved
```

### ✅ **Vault Writer**
- [x] Vault writer implemented (`atlas/core/vault_writer.py`)
- [x] Real-time sync to /opt/heimdall/vault/
- [x] Obsidian-compatible .md files with YAML frontmatter
- [x] Three-vault architecture (work, personal, kb)
- [x] Auto-creates folder structure
- [x] Deduplication by checksum
- [x] Backlinks extraction and storage
- [x] Vault index generation (`vault/_index.md`)
- [x] API endpoints: `/vault/sync`, `/vault/sync/now`, `/vault/status`
- [x] **Verified:** Chat turns auto-sync to vault files
├── journal/          # Daily auto-drafts + edits
├── goals/            # SMART goals (Markdown + frontmatter)
├── wiki/             # General knowledge (LLM-compiled)
├── life-docs/        # Important document summaries
├── budget/           # Rules, records, monthly snapshots
├── study/            # Flashcard decks + quiz state
├── maps/             # Saved locations
├── health/           # Daily health summaries
├── meetings/         # Pre-meeting briefs
└── inbox/            # Drop zone (auto-processed)
```

### 📋 **Auto-Processing**
- [ ] Daily journal drafts created automatically
- [ ] Meeting notes pre-populated with context
- [ ] Inbox items auto-filed by LLM
- [ ] Wiki entries updated from chat summaries
- [ ] Budget snapshots monthly

---

## 🔄 **Phase 7: Voice Interface (Future)**
**Status: 0% Planned Only**

### 📋 **Wake Word System**
```
Microphone (always on, local)
  ↓
Wake word detection (Porcupine / Picovoice)
  ↓
Speech-to-text (Whisper local)
  ↓
Capability Planner
  ↓
Response (TTS — Kokoro local or ElevenLabs)
```

#### Components
- [ ] Wake word: "Hey Heimdall"
- [ ] Voice persona: "Nora"
- [ ] Local Whisper for STT
- [ ] Kokoro or ElevenLabs for TTS
- [ ] **Test:** "Hey Heimdall, what's on my calendar?" → spoken response

---

## 📊 **All Planned Tools & Capabilities**

### Core AI Models
| Model | Provider | Use Case | Status |
|-------|----------|----------|--------|
| Qwen3.5:7b | Ollama (local) | Routing, quick Q&A | ⏳ Pending |
| Qwen3.5:32b | Ollama (local, future GPU) | Most PA tasks | ⏳ Future |
| nomic-embed-text | Ollama (local) | Embeddings | ⏳ Pending |
| DeepSeek V4-Flash | API ($0.14/M) | Writing, docs, journal | ⏳ Pending |
| DeepSeek V4-Pro | API ($1.74/M) | Complex reasoning | ⏳ Pending |
| Gemini 2.5 Flash | Google (free) | Vision, photos | ⏳ Pending |
| Claude Sonnet 4.6 | API ($3/M) | Code generation | ⏳ Pending |
| Groq (Llama 4 Scout) | Free tier | Ultra-fast voice | ⏳ Pending |
| Whisper | Local | Speech-to-text | ⏳ Phase 7 |

### APIs & Integrations
| Service | Use Case | Cost | Status |
|---------|----------|------|--------|
| Google Maps Directions | Journey planning | Free (10k/mo) | ⏳ Pending |
| Google Route Optimization | Multi-stop routes | Pay per use | ⏳ Pending |
| TfL Unified API | Live London transit | Free | ⏳ Pending |
| OpenWeatherMap | Weather | Free (1k/day) | ⏳ Pending |
| Google Calendar | Schedule access | Free | ⏳ Pending |
| Garmin Connect | Health data | Free (personal) | ⏳ Pending |
| Apple HealthKit | iOS health bridge | Free | ⏳ Pending |
| Langfuse | Prompt tracing | Self-hosted free | ✅ Configured |
| Paperless-ngx | Document OCR | Self-hosted free | ⏳ Pending |
| n8n | Automation | Self-hosted free | ⏳ Future |

### Dashboard Tools
| Tool | Purpose | Phase |
|------|---------|-------|
| Chat Interface | Main interaction | 1C |
| Memory Browser | Search all memory | 2A |
| Entity Explorer | People, projects, places | 2A |
| Goals Tracker | SMART goals | 2B |
| Health Dashboard | Garmin/Apple data | 4 |
| Budget View | Spending tracking | 2B |
| Document Archive | Paperless integration | 4 |
| VSCode Remote | Code workspace control | 4 |
| Settings Panel | Configuration | 3A |

---

## 📋 **Monthly Cost Breakdown**

| Service | Estimated Cost |
|---------|---------------|
| Vercel (dashboard hosting) | Free |
| Cloudflare Tunnel | Free |
| DeepSeek API (personal use) | ~£1–3 |
| Google Maps API (light) | Free tier |
| Gemini API | Free tier |
| OpenWeatherMap | Free |
| Groq | Free tier |
| Langfuse (self-hosted) | Free |
| Electricity (spare PC) | ~£3–5 |
| Claude Pro (optional) | £16/mo |
| **Total (without Claude Pro)** | **~£4–8/mo** |
| **Total (with Claude Pro)** | **~£20–24/mo** |

---

## 📋 **Quick Reference Commands**

### Server Access
```bash
# SSH via local network
ssh heimdall@192.168.18.187

# SSH via Tailscale (remote)
ssh heimdall@100.113.79.103

# Navigate to project
cd /opt/heimdall
```

### Docker Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Restart single service
docker-compose restart postgres

# Check status
docker-compose ps

# Update images
docker-compose pull
docker-compose up -d
```

### Service URLs (when running)
| Service | URL | Purpose |
|---------|-----|---------|
| PostgreSQL | localhost:5432 | Database |
| Ollama | localhost:11434 | Local LLMs |
| Redis | localhost:6379 | Cache/Queue |
| pgvector | In PostgreSQL | Vector DB (pgvector extension) |
| Langfuse | http://192.168.18.187:3001 | Observability |

### Model Management
```bash
# List models
curl http://localhost:11434/api/tags

# Pull model
curl http://localhost:11434/api/pull -d '{"name": "llama3.2"}'

# Generate text
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3.5:7b",
  "prompt": "Hello, how are you?"
}'
```

---

## 🚧 **Known Issues & Workarounds**

### 🔴 Critical
- **iDRAC Unreachable (192.168.18.120)**
  - Status: BMC cold reset attempted, still unreachable
  - Workaround: Using SSH + Tailscale for remote access
  - Resolution: Requires physical access to server

### 🟡 Medium
- None currently

### 🟢 Low
- None currently

---

*Last Updated: May 14, 2026 04:19 UTC*
*Progress Tracking Version: 3.0*  
*Heimdall System v1.0 - Development Roadmap*

**Architecture Change:** LanceDB → pgvector (R620 Xeon E5 AVX2 limitation)

**Audit Note:** Previous progress tracking (v2.3) was obsolete. This version (v3.0) reflects actual implementation state based on codebase audit on May 14, 2026. Many features marked as "0% Complete" were actually fully implemented.
