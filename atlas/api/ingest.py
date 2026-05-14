"""
Ingest API — upload files or URLs, get them classified and indexed.

Endpoints:
  POST /ingest/file    — upload a file (multipart)
  POST /ingest/url     — submit a YouTube or Instagram URL
  POST /ingest/text    — submit raw text/markdown directly
  POST /ingest/clarify — answer a clarification question to complete a pending ingest
"""

import logging
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from atlas.services.ingest_service import extract
from atlas.core.ingest_agent import ingest, IngestResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])

# In-memory pending clarifications: {session_id: {content, hint}}
# Simple dict — good enough without auth. Will move to Redis in Phase 4.
_pending: dict[str, dict] = {}


def _result_response(result: IngestResult) -> dict:
    if result.status == "needs_clarification":
        return {
            "status": "needs_clarification",
            "question": result.clarification_question,
            "title": result.title,
            "suggested_folder": result.vault_folder,
        }
    if result.status == "error":
        raise HTTPException(status_code=422, detail=result.error)
    return {
        "status": "indexed",
        "title": result.title,
        "vault_folder": result.vault_folder,
        "vault_file": result.vault_file,
        "chunks_stored": result.chunks_stored,
        "summary": result.summary,
        "tags": result.tags,
    }


@router.post("/file")
async def ingest_file(
    file: UploadFile = File(...),
    hint: str = Form(default=""),
    folder: str = Form(default=""),
):
    """
    Upload a file for ingestion.
    Supported: .txt .md .pdf .docx .pptx .jpg .png .webp (and other images)
    Optional: hint — a note about what this file is for.
    Optional: folder — force a vault folder (goals/people/ideas/wiki/journal/places).
    """
    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    try:
        content = await extract(file_bytes=file_bytes, filename=file.filename or "upload")
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    # Store in pending in case clarification is needed
    session_id = f"file-{hash(file_bytes)}"
    _pending[session_id] = {"content": content, "hint": hint}

    result = await ingest(content, user_hint=hint, force_folder=folder)

    if result.status == "needs_clarification":
        return {**_result_response(result), "session_id": session_id}

    _pending.pop(session_id, None)
    return _result_response(result)


class URLRequest(BaseModel):
    url: str
    hint: str = ""
    folder: str = ""


@router.post("/url")
async def ingest_url(req: URLRequest):
    """
    Submit a YouTube or Instagram URL for ingestion.
    Extracts transcript/captions/metadata via yt-dlp.
    """
    try:
        content = await extract(url=req.url)
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL extraction failed: {e}")

    session_id = f"url-{hash(req.url)}"
    _pending[session_id] = {"content": content, "hint": req.hint}

    result = await ingest(content, user_hint=req.hint, force_folder=req.folder)

    if result.status == "needs_clarification":
        return {**_result_response(result), "session_id": session_id}

    _pending.pop(session_id, None)
    return _result_response(result)


class TextRequest(BaseModel):
    text: str
    filename: str = "paste.md"
    hint: str = ""
    folder: str = ""


@router.post("/text")
async def ingest_text(req: TextRequest):
    """
    Submit raw text or markdown directly for ingestion.
    Useful for pasting notes, copying content from apps, etc.
    """
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Text is empty")

    try:
        content = await extract(
            file_bytes=req.text.encode("utf-8"),
            filename=req.filename if req.filename.endswith((".txt", ".md")) else req.filename + ".md",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    session_id = f"text-{hash(req.text[:100])}"
    _pending[session_id] = {"content": content, "hint": req.hint}

    result = await ingest(content, user_hint=req.hint, force_folder=req.folder)

    if result.status == "needs_clarification":
        return {**_result_response(result), "session_id": session_id}

    _pending.pop(session_id, None)
    return _result_response(result)


class ClarifyRequest(BaseModel):
    session_id: str
    answer: str
    folder: str = ""


@router.post("/clarify")
async def ingest_clarify(req: ClarifyRequest):
    """
    Answer a clarification question from a previous /ingest/* call.
    Pass the session_id returned by the original request.
    """
    pending = _pending.get(req.session_id)
    if not pending:
        raise HTTPException(
            status_code=404,
            detail="Session not found or already completed. Re-upload the file.",
        )

    content = pending["content"]
    hint = pending["hint"]

    result = await ingest(
        content,
        user_hint=hint,
        clarification_answer=req.answer,
        force_folder=req.folder,
    )

    if result.status == "needs_clarification":
        # Still unclear — ask again
        return {**_result_response(result), "session_id": req.session_id}

    _pending.pop(req.session_id, None)
    return _result_response(result)


@router.get("/supported")
async def supported_formats():
    """List all supported ingest formats."""
    return {
        "files": [".txt", ".md", ".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic"],
        "urls": ["YouTube (youtube.com, youtu.be)", "Instagram (instagram.com/p/, /reel/, /tv/)"],
        "text": "Raw text via POST /ingest/text",
        "max_file_size_mb": 50,
        "image_backend": "Gemini 2.0 Flash (requires GEMINI_API_KEY)",
        "video_backend": "yt-dlp (free, no API key needed)",
    }
