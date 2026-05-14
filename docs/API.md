# Heimdall API Reference

Base URL: `http://localhost:8000` (local) or `http://100.113.79.103:8000` (Tailscale)

Interactive docs: `/docs` (Swagger UI), `/redoc`

---

## Authentication

Heimdall uses **JWT bearer tokens**. Get a token via `/auth/login`, then pass it as:
```
Authorization: Bearer <token>
```
Tokens are valid for **7 days** by default (`JWT_EXPIRE_MINUTES` in `.env`).

> Currently auth is not enforced on most routes — it is wired and ready to be applied once you want to lock down Tailscale access. Use `Depends(require_auth)` on any route to protect it.

### `POST /auth/login`
Standard OAuth2 password flow.

**Request** (form data):
```
username=nicholas
password=<your_password>
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in_minutes": 10080
}
```

### `GET /auth/me`
Returns current user. Requires valid token.

```json
{ "username": "nicholas", "is_admin": true }
```

### `POST /auth/refresh`
Issues a new token from a valid existing one. Requires valid token.

---

## Chat

### `POST /chat`
Send a message. The **Capability Planner** automatically selects the best model and fetches relevant memory context.

**Request:**
```json
{
  "message": "what do you know about my goals?",
  "history": [],
  "model": null,
  "store_in_memory": false
}
```
- `model` — override the planner's model choice (e.g. `"groq-llama4-scout"`, `"deepseek-flash"`, `"qwen3:8b"`)
- `store_in_memory` — force storage of the message regardless of planner decision
- `history` — list of `{role, content}` dicts for multi-turn context

**Response:**
```json
{
  "reply": "Here's what I know...",
  "model": "groq-llama4-scout",
  "plan": {
    "model": "groq-llama4-scout",
    "capabilities": ["retrieval"],
    "memory_tables": ["vector_memory"],
    "memory_query": "personal goals",
    "store": false,
    "reasoning": "Needs memory retrieval for personal goals."
  },
  "context_used": [
    { "id": "...", "text": "User's goal is...", "source_type": "goal", "distance": 0.12 }
  ]
}
```

### `POST /chat/stream`
Same as `/chat` but streams tokens as Server-Sent Events.

**SSE event types:**
| type | payload |
|------|---------|
| `plan` | The routing plan (first event) |
| `context` | Memory context used |
| `token` | Each streamed token |
| `done` | `{model, plan}` — stream complete |
| `error` | Error message |

### `POST /chat/plan`
Debug endpoint — returns the planner's routing decision without calling the LLM.

**Request:** `{"message": "your message"}`

**Response:**
```json
{
  "message": "your message",
  "plan": { "model": "...", "capabilities": [...], ... }
}
```

---

## Memory

### `GET /memory/counts`
Returns entry count per vector table.
```json
{ "vector_memory": 17, "vector_notes": 4, "vector_chat_summaries": 0, "vector_code_chunks": 0 }
```

### `POST /memory/store`
Manually store a fact.
```json
{ "text": "I prefer dark mode on all apps", "source_type": "preference", "table": "vector_memory" }
```

### `GET /memory/search?q=...&table=...&limit=5`
Semantic search a specific table.

### `GET /memory/browse?table=...&limit=50&offset=0`
Browse all entries in a table (no embedding needed).

### `GET /memory/tables`
Returns the list of available vector tables.

---

## Ingestion

Upload any file or URL — the **Ingest Agent** extracts content, classifies it, stores it to memory, and writes it to the Obsidian vault.

### `POST /ingest/file`
Multipart file upload.

**Form fields:**
- `file` — the file (required)
- `hint` — optional note about what this is for
- `folder` — force a vault folder (`goals`, `people`, `ideas`, `wiki`, `journal`, `places`)

**Supported types:** `.txt`, `.md`, `.pdf`, `.docx`, `.pptx`, `.jpg`, `.png`, `.webp`, `.gif`, `.bmp`, `.heic`

**Response (indexed):**
```json
{
  "status": "indexed",
  "title": "React useEffect Notes",
  "vault_folder": "wiki",
  "vault_file": "/opt/heimdall/vault/wiki/react-useeffect-notes.md",
  "chunks_stored": 3,
  "summary": "Notes on React useEffect hook behaviour.",
  "tags": ["react", "programming"]
}
```

**Response (needs clarification):**
```json
{
  "status": "needs_clarification",
  "question": "Is this a personal note or reference material?",
  "title": "",
  "suggested_folder": "wiki",
  "session_id": "file-83920..."
}
```

### `POST /ingest/url`
Submit a YouTube or Instagram URL.
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "hint": "productivity video",
  "folder": ""
}
```
Uses `yt-dlp` to extract transcript, captions, title, description.

### `POST /ingest/text`
Submit raw text or markdown directly.
```json
{
  "text": "CAP theorem: Consistency, Availability, Partition tolerance — pick 2.",
  "filename": "distributed-systems.md",
  "hint": "lecture notes",
  "folder": ""
}
```

### `POST /ingest/clarify`
Answer a clarification question from a previous ingest call.
```json
{
  "session_id": "file-83920...",
  "answer": "This is a reference note for my distributed systems module.",
  "folder": ""
}
```

### `GET /ingest/supported`
Lists all supported formats and backends.

---

## Vault

The vault is an Obsidian-compatible folder at `/opt/heimdall/vault/`. Point Obsidian at this folder.

### `GET /vault/status`
Returns file counts per vault section.
```json
{
  "vault_path": "/opt/heimdall/vault",
  "index_exists": true,
  "sections": {
    "people": { "files": 1, "names": ["mr-tan"] },
    "goals":  { "files": 3, "names": ["rtx-3090-pc-build", ...] },
    ...
  }
}
```

### `POST /vault/sync`
Trigger a full vault sync in the background (non-blocking).

### `POST /vault/sync/now`
Trigger a full vault sync and wait for it. Returns summary:
```json
{ "status": "done", "written": 10, "skipped": 21, "errors": 0 }
```

---

## System

### `GET /health`
Returns status of all services (PostgreSQL, Ollama, Redis).

### `GET /models`
Returns available Ollama models and configured cloud models.

### `GET /brief`
Generates your morning brief — a summary of goals, recent notes, and a motivational nudge.

---

## Available Models

| ID | Provider | Best for |
|----|----------|----------|
| `groq-llama4-scout` | Groq (cloud) | Quick answers, retrieval, short tasks |
| `groq-llama3-70b` | Groq (cloud) | Heavier reasoning via Groq |
| `groq-llama3-8b` | Groq (cloud) | Fast indexing/planning (internal use) |
| `deepseek-flash` | DeepSeek (cloud) | Writing, code, analysis |
| `deepseek-pro` | DeepSeek (cloud) | Complex multi-step reasoning |
| `qwen3:8b` | Ollama (local) | Local general use |
| `qwen3:1.7b` | Ollama (local) | Local fast/trivial tasks |
| `nomic-embed-text` | Ollama (local) | Embeddings (internal use) |

---

## Vault Structure

```
/opt/heimdall/vault/
├── _index.md          ← auto-generated overview
├── people/            ← one .md per person
├── goals/             ← one .md per goal
├── ideas/             ← projects, ideas, plans
├── places/            ← location notes
├── journal/           ← one .md per day (YYYY-MM-DD.md)
└── wiki/              ← reference material, facts, notes
```

Each file uses YAML frontmatter:
```yaml
---
title: "React useEffect Notes"
type: study
created: 2026-05-11
updated: 2026-05-11
tags: [react, programming]
source: heimdall/ingest
---
```

---

## Running the Server

```bash
cd /opt/heimdall
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Auto-start on boot (systemd service — see `docs/SERVER-README.md`).

## Running the Test Suite

```bash
cd /opt/heimdall
source venv/bin/activate
python tests/test_suite.py
```

Expected: **25/25 passing** (test 14 may occasionally show a flaky Groq rate-limit fallback — this is expected behaviour).
