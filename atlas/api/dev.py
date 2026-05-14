"""
Dev Mode API — LLM-powered code generation + apply for the Next.js frontend.
All endpoints require JWT auth. Changes are sandboxed to /opt/heimdall-web.
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from atlas.api.auth import require_auth
from atlas.services.groq_service import chat as groq_chat

router = APIRouter(prefix="/dev", tags=["dev"])

WEB_ROOT = Path("/opt/heimdall-web")
ALLOWED_EXTENSIONS = {".tsx", ".ts", ".css", ".json", ".md"}
BLOCKED_PATHS = {
    "app/layout.tsx", "app/globals.css", "next.config.ts",
    "package.json", "tsconfig.json", "postcss.config.mjs",
    "lib/api.ts", "lib/store.ts",
}
MAX_FILE_SIZE = 64_000  # chars — keep within LLM context

DEV_SYSTEM = """You are an expert Next.js / TypeScript / Tailwind developer working on the Heimdall personal AI dashboard.

The project uses:
- Next.js 16 App Router (all pages in /app/, "use client" for interactive components)
- TypeScript
- Tailwind CSS v4 (no tailwind.config.js — just use utility classes)
- Lucide React for icons
- Zustand for state
- react-markdown for rendering markdown
- All API calls go through /api proxy defined in next.config.ts

Style conventions:
- Dark theme: bg-zinc-950, bg-zinc-900, bg-zinc-800 for surfaces
- Accent: violet-600 / violet-400
- Text: zinc-100 (primary), zinc-400 (secondary), zinc-600 (muted)
- Rounded corners: rounded-xl for cards, rounded-lg for inputs
- Auth guard: wrap pages in <Shell> component which includes <AuthGuard> + <BottomNav>

TASK: Given the user's request and the current file content(s), produce the complete new file content(s).

CRITICAL FILE LOCATION RULES — follow exactly:
- New pages go in: app/<pagename>/page.tsx  (e.g. app/vault/page.tsx)
- Shared components go in: components/<Name>.tsx  (e.g. components/MyWidget.tsx)
- Utility/API code goes in: lib/<name>.ts
- NEVER create files inside app/layout/, app/components/, or any path that conflicts with the root layout.tsx, globals.css, or existing components/
- NEVER use lucide-react-native — use lucide-react
- NEVER use "use client" from "next/app" — use "use client" as a bare directive on line 1
- ALWAYS start client components with: "use client";  as the very first line

Respond ONLY with a JSON object in this exact format — no markdown fences, no explanation outside the JSON:
{
  "explanation": "one sentence describing what you changed",
  "files": [
    {
      "path": "relative/path/from/web/root.tsx",
      "content": "full new file content here"
    }
  ]
}

If the request requires creating a new page, put it at app/<pagename>/page.tsx.
If the request modifies an existing file, return the complete new file (not a diff).
Keep changes minimal and focused. Never touch files not relevant to the request."""


class GenerateRequest(BaseModel):
    prompt: str
    files: list[str] = []  # relative paths to include as context


class ApplyRequest(BaseModel):
    files: list[dict]  # [{"path": "...", "content": "..."}]
    explanation: str = ""


class FileReadRequest(BaseModel):
    path: str  # relative path


def _resolve_safe(rel_path: str) -> Path:
    """Resolve a relative path inside WEB_ROOT, raising if it escapes."""
    # Normalize separators
    rel_path = rel_path.replace("\\", "/").lstrip("/")
    if rel_path in BLOCKED_PATHS:
        raise HTTPException(status_code=400, detail=f"File is protected: {rel_path}")
    resolved = (WEB_ROOT / rel_path).resolve()
    if not str(resolved).startswith(str(WEB_ROOT.resolve())):
        raise HTTPException(status_code=400, detail="Path outside web root")
    if resolved.suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension not allowed: {resolved.suffix}")
    return resolved


@router.get("/files")
async def list_files(_: str = Depends(require_auth)):
    """List all editable source files in the web project."""
    results = []
    for ext in ALLOWED_EXTENSIONS:
        for p in WEB_ROOT.rglob(f"*{ext}"):
            rel = str(p.relative_to(WEB_ROOT))
            # Skip node_modules and .next
            if "node_modules" in rel or ".next" in rel:
                continue
            results.append(rel)
    return {"files": sorted(results)}


@router.post("/read")
async def read_file(req: FileReadRequest, _: str = Depends(require_auth)):
    """Read a file's current content."""
    path = _resolve_safe(req.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    content = path.read_text(errors="replace")
    return {"path": req.path, "content": content[:MAX_FILE_SIZE]}


@router.post("/generate")
async def generate_patch(req: GenerateRequest, _: str = Depends(require_auth)):
    """Send prompt + file context to LLM, return proposed file changes."""
    context_blocks = []
    for rel_path in req.files[:5]:  # limit context files
        try:
            path = _resolve_safe(rel_path)
            if path.exists():
                content = path.read_text(errors="replace")[:MAX_FILE_SIZE]
                context_blocks.append(f"### FILE: {rel_path}\n```\n{content}\n```")
        except HTTPException:
            continue

    context = "\n\n".join(context_blocks) if context_blocks else "No files provided — you may create new files."

    messages = [
        {"role": "system", "content": DEV_SYSTEM},
        {"role": "user", "content": f"CURRENT FILES:\n{context}\n\nREQUEST: {req.prompt}"},
    ]

    try:
        raw = await groq_chat(messages, model="groq-llama3-70b")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    # Extract JSON from response
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        raise HTTPException(status_code=422, detail="LLM did not return valid JSON")

    import json
    try:
        result = json.loads(json_match.group())
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Failed to parse LLM JSON response")

    if "files" not in result:
        raise HTTPException(status_code=422, detail="LLM response missing 'files' key")

    # Attach original content for diff display
    originals: dict[str, str] = {}
    for f in result["files"]:
        rel = f.get("path", "")
        try:
            p = _resolve_safe(rel)
            if p.exists():
                originals[rel] = p.read_text(errors="replace")[:MAX_FILE_SIZE]
            else:
                originals[rel] = ""  # new file
        except HTTPException:
            originals[rel] = ""

    return {
        "explanation": result.get("explanation", ""),
        "files": result["files"],
        "originals": originals,
    }


@router.post("/apply")
async def apply_patch(req: ApplyRequest, _: str = Depends(require_auth)):
    """Write files and rebuild the Next.js app."""
    written = []
    for file_change in req.files:
        rel_path = file_change.get("path", "")
        content = file_change.get("content", "")
        if not rel_path or not content:
            continue
        try:
            path = _resolve_safe(rel_path)
        except HTTPException as e:
            return {"status": "error", "detail": str(e.detail), "written": written}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        written.append(rel_path)

    if not written:
        raise HTTPException(status_code=400, detail="No files written")

    # Rebuild Next.js
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(WEB_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        build_ok = result.returncode == 0
        build_output = (result.stdout + result.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return {"status": "error", "detail": "Build timed out", "written": written}

    if not build_ok:
        return {
            "status": "build_failed",
            "detail": "Files written but build failed — check output",
            "build_output": build_output,
            "written": written,
        }

    # Restart the web service
    try:
        subprocess.run(
            ["sudo", "systemctl", "restart", "heimdall-web"],
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass  # Best effort — build succeeded even if restart fails

    return {
        "status": "success",
        "written": written,
        "explanation": req.explanation,
        "build_output": build_output[-1000:],
    }
