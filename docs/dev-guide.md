# Heimdall Developer Guide

## Architecture Overview

```
/opt/heimdall/          ← FastAPI backend (Python)
/opt/heimdall-web/      ← Next.js frontend (TypeScript)
```

### Backend Stack
- **FastAPI** + **uvicorn** on port 8000
- **PostgreSQL** + **pgvector** — vector memory, notes, chat
- **Ollama** on port 11434 — local LLM (llava:13b for vision)
- **Groq API** — fast cloud LLM (Llama 4 Scout, Llama 3.3 70b)
- **DeepSeek API** — fallback cloud LLM
- **Gemini 2.5 Flash** — precision OCR for financial images

### Frontend Stack
- **Next.js 16** App Router, TypeScript, Tailwind CSS v4
- **Zustand** — auth + chat state (persisted to localStorage)
- **react-markdown** — renders LLM responses
- All API calls proxied through `/api/*` → `127.0.0.1:8000`

---

## Services

| Service | Command | Port |
|---|---|---|
| Backend | `sudo systemctl restart heimdall` | 8000 |
| Frontend | `sudo systemctl restart heimdall-web` | 3000 |

Check status: `sudo systemctl status heimdall heimdall-web`

Logs: `sudo journalctl -u heimdall -f` or `sudo journalctl -u heimdall-web -f`

---

## Backend — How to Add an Endpoint

1. Create or edit a router in `/opt/heimdall/atlas/api/<name>.py`
2. Add the router to `/opt/heimdall/main.py`:
   ```python
   from atlas.api.<name> import router as <name>_router
   app.include_router(<name>_router)
   ```
3. Restart: `sudo systemctl restart heimdall`

### Auth-protected endpoint pattern
```python
from atlas.api.auth import require_auth
from fastapi import Depends

@router.get("/something")
async def my_endpoint(user: str = Depends(require_auth)):
    ...
```

### DB session pattern
```python
from atlas.db.session import get_session

async with get_session() as session:
    result = await session.execute(select(MyModel))
```

### Vector memory pattern
```python
from atlas.db.vector_store import search, browse, store

results = await search("vector_memory", "query text", limit=5)
all_entries = await browse("vector_notes", limit=50)
```

---

## Frontend — How to Add a Page

1. Create `/opt/heimdall-web/app/<pagename>/page.tsx`
2. Start with `"use client";` if it has any interactivity
3. Wrap in `<Shell>` for auth guard + bottom nav:
   ```tsx
   "use client";
   import Shell from "@/components/Shell";

   export default function MyPage() {
     return (
       <Shell>
         <div className="px-4 pt-6">...</div>
       </Shell>
     );
   }
   ```
4. Add to bottom nav in `/opt/heimdall-web/components/BottomNav.tsx`
5. Build + restart:
   ```bash
   cd /opt/heimdall-web && npm run build
   sudo systemctl restart heimdall-web
   ```

### API call pattern (frontend)
All calls go through `lib/api.ts`. The base is `/api` which proxies to port 8000.
```ts
import { myEndpoint } from "@/lib/api";
const result = await myEndpoint.get();
```

### Style conventions
- **Surfaces:** `bg-zinc-950` (page), `bg-zinc-900` (card), `bg-zinc-800` (input)
- **Accent:** `violet-600` (buttons), `violet-400` (active/highlight)
- **Text:** `zinc-100` (primary), `zinc-400` (secondary), `zinc-600` (muted)
- **Cards:** `rounded-xl border border-zinc-800`
- **Inputs:** `rounded-xl bg-zinc-800 focus:ring-2 focus:ring-violet-500`

---

## Dev Mode (from the browser)

Go to `http://100.113.79.103:3000/dev`

1. Pick context files (existing pages the LLM should read)
2. Describe the change in plain English
3. Review the generated code
4. Hit **Apply & rebuild** — files written, build runs, service restarts

**What the LLM can touch:**
- `app/<name>/page.tsx` — pages
- `components/<Name>.tsx` — shared components
- `lib/<name>.ts` — utilities

**What is protected (never overwritten):**
- `app/layout.tsx`, `app/globals.css`, `next.config.ts`, `package.json`

---

## Ingestion

POST to `/api/ingest/file`, `/api/ingest/url`, or `/api/ingest/text`

The pipeline:
1. Extract raw text (PyMuPDF, python-docx, yt-dlp, Gemini/Ollama for images)
2. Groq LLM classifies → vault folder, title, tags, summary
3. Chunk → embed → store to `vector_notes`
4. Write Markdown to `/opt/heimdall/vault/<folder>/<title>.md`

---

## Vision Routing

Images are processed with smart routing:
1. **Ollama llava:13b** does a fast scan (local, free)
2. If financial/text-heavy content detected → escalate to **Gemini 2.5 Flash** (billing enabled)
3. Otherwise use llava result directly

Trigger keywords: bank, statement, SGD, transaction, invoice, receipt, balance, etc.

---

## Environment Variables

File: `/opt/heimdall/.env`

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `GROQ_API_KEY` | Groq cloud LLM |
| `GEMINI_API_KEY` | Google Gemini vision |
| `JWT_SECRET` | Token signing key |
| `JWT_EXPIRE_MINUTES` | Token lifetime (default 10080 = 7 days) |
| `ADMIN_USERNAME` | Login username |
| `ADMIN_PASSWORD` | Login password |
| `OLLAMA_BASE_URL` | Ollama endpoint (default localhost:11434) |
| `OLLAMA_VISION_MODEL` | Vision model (llava:13b) |
| `VAULT_PATH` | Obsidian vault path (/opt/heimdall/vault) |

---

## Key File Locations

```
atlas/
  api/          ← FastAPI routers (chat, auth, brief, ingest, goals, habits, budget, dev...)
  core/         ← Business logic (planner, indexer, vault_writer, embeddings)
  db/           ← DB models, session, vector_store
  services/     ← External APIs (groq, deepseek, ollama, ingest_service)

heimdall-web/
  app/          ← Next.js pages (page.tsx per route)
  components/   ← Shared UI (Shell, BottomNav, AuthGuard)
  lib/          ← API client (api.ts), Zustand store (store.ts)
```

---

## Common Fixes

**Backend won't start:**
```bash
sudo journalctl -u heimdall --no-pager -n 30 | grep -E "Error|Import|Module"
```

**Port 8000 not listening:**
```bash
ss -tlnp | grep 8000
sudo systemctl restart heimdall
```

**Frontend build fails:**
```bash
cd /opt/heimdall-web && npm run build
# Check error, fix file, rebuild
```

**CORS errors:** All frontend API calls must go through `/api/*` (the Next.js proxy). Never call `http://...:8000` directly from the browser.
