"""
Heimdall Full Test Suite
Run: python tests/test_suite.py
Requires: server running on localhost:8000, correct ADMIN_PASSWORD in .env
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE = "http://localhost:8000"
PASS = os.getenv("ADMIN_PASSWORD", "changeme")
USER = os.getenv("ADMIN_USERNAME", "nicholas")


class Suite:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.token = ""

    def ok(self, n, msg):
        self.passed += 1
        print(f"  PASS [{n:02d}] {msg}")

    def fail(self, n, msg, detail=""):
        self.failed += 1
        print(f"  FAIL [{n:02d}] {msg}  →  {str(detail)[:120]}")

    @property
    def H(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}


async def run():
    s = Suite()
    pending_session = ""

    async with httpx.AsyncClient(timeout=90, base_url=BASE) as c:

        # ── Core ──────────────────────────────────────────────────────────────
        print("── Core ──")

        r = await c.get("/")
        s.ok(1, "Root") if r.status_code == 200 else s.fail(1, "Root", r.text)

        r = await c.get("/health")
        svc = r.json().get("status", "?")
        s.ok(2, f"Health: {svc}") if r.status_code == 200 else s.fail(2, "Health", r.text)

        r = await c.get("/models")
        s.ok(3, f"Models: HTTP {r.status_code}") if r.status_code in (200, 502) else s.fail(3, "Models", r.text)

        # ── Auth ──────────────────────────────────────────────────────────────
        print("\n── Auth ──")

        r = await c.post("/auth/login", data={"username": USER, "password": PASS})
        if r.status_code == 200:
            s.token = r.json()["access_token"]
            s.ok(4, f"Login: {len(s.token)}-char token")
        else:
            s.fail(4, "Login", r.text)

        r = await c.get("/auth/me", headers=s.H)
        s.ok(5, f"/auth/me: {r.json().get('username')}") if r.status_code == 200 else s.fail(5, "/auth/me", r.text)

        r = await c.post("/auth/login", data={"username": USER, "password": "wrongpassword123"})
        s.ok(6, "Wrong password → 401") if r.status_code == 401 else s.fail(6, "Wrong password not rejected", r.status_code)

        r = await c.post("/auth/refresh", headers=s.H)
        s.ok(7, "Token refresh") if r.status_code == 200 else s.fail(7, "Token refresh", r.text)

        r = await c.get("/auth/me", headers={"Authorization": "Bearer garbage.invalid.token"})
        s.ok(8, "Invalid token → 401") if r.status_code == 401 else s.fail(8, "Invalid token not rejected", r.status_code)

        # ── Memory ────────────────────────────────────────────────────────────
        print("\n── Memory ──")

        r = await c.get("/memory/counts")
        s.ok(9, f"Counts: {r.json()}") if r.status_code == 200 else s.fail(9, "Memory counts", r.text)

        r = await c.post("/memory/store", json={"text": "Heimdall test suite entry", "source_type": "test", "table": "vector_memory"})
        s.ok(10, f"Store: {str(r.json().get('id', ''))[:12]}...") if r.status_code == 200 else s.fail(10, "Memory store", r.text)

        r = await c.get("/memory/search", params={"q": "test suite", "table": "vector_memory", "limit": 3})
        s.ok(11, f"Search (GET): {len(r.json())} results") if r.status_code == 200 else s.fail(11, "Memory search", r.text)

        r = await c.get("/memory/browse", params={"table": "vector_memory", "limit": 5})
        s.ok(12, f"Browse: {len(r.json())} rows") if r.status_code == 200 else s.fail(12, "Memory browse", r.text)

        # ── Chat + Planner ────────────────────────────────────────────────────
        print("\n── Chat + Planner ──")

        r = await c.post("/chat/plan", json={"message": "hey how are you"})
        p = r.json()["plan"]
        s.ok(13, f"Plan(quick): model={p['model']} store={p['store']}") if r.status_code == 200 else s.fail(13, "Plan quick", r.text)

        r = await c.post("/chat/plan", json={"message": "what was that goal i had about my PC build"})
        p = r.json()["plan"]
        s.ok(14, f"Plan(retrieval): tables={p['memory_tables']}") if "retrieval" in p["capabilities"] else s.fail(14, f"Expected retrieval cap", p["capabilities"])

        r = await c.post("/chat/plan", json={"message": "write me a python script to rename files in bulk"})
        p = r.json()["plan"]
        s.ok(15, f"Plan(code/write): model={p['model']} caps={p['capabilities']}") if r.status_code == 200 else s.fail(15, "Plan code", r.text)

        r = await c.post("/chat", json={"message": "what do you know about me?"})
        d = r.json()
        s.ok(16, f"Chat: model={d['model']} ctx={len(d['context_used'])} items") if r.status_code == 200 else s.fail(16, "Chat", r.text)

        r = await c.post("/chat", json={"message": "my favourite programming language is Python"})
        d = r.json()
        s.ok(17, f"Chat(new fact): store={d['plan'].get('store')} model={d['model']}") if r.status_code == 200 else s.fail(17, "Chat fact", r.text)

        # ── Ingestion ─────────────────────────────────────────────────────────
        print("\n── Ingestion ──")

        r = await c.post("/ingest/text", json={
            "text": "CAP theorem: in a distributed system you can only guarantee 2 of Consistency, Availability, Partition tolerance.",
            "hint": "distributed systems lecture notes",
        })
        d = r.json()
        s.ok(18, f'Ingest text: "{d.get("title")}" → {d.get("vault_folder")} ({d.get("chunks_stored")} chunks)') if d.get("status") == "indexed" else s.fail(18, "Ingest text", d)

        r = await c.post("/ingest/text", json={"text": "abc xyz 123"})
        d = r.json()
        s.ok(19, f'Ingest ambiguous → {d["status"]}  Q: {d.get("question", "")[:55]}') if d.get("status") == "needs_clarification" else s.fail(19, "Expected clarification", d)
        pending_session = d.get("session_id", "")

        if pending_session:
            r2 = await c.post("/ingest/clarify", json={"session_id": pending_session, "answer": "this is a test string, file it under wiki"})
            d2 = r2.json()
            s.ok(20, f'Clarify: "{d2.get("title")}" → {d2.get("vault_folder")}') if r2.status_code == 200 else s.fail(20, "Clarify", r2.text)
        else:
            s.fail(20, "No session_id returned for clarification")

        md_path = Path(__file__).parent.parent / "vault/wiki/react-useeffect-notes.md"
        if md_path.exists():
            r = await c.post("/ingest/file",
                files={"file": ("react.md", md_path.read_bytes(), "text/markdown")},
                data={"hint": "react hooks study note"})
            d = r.json()
            s.ok(21, f'Ingest file: "{d.get("title")}" → {d.get("vault_folder")}') if r.status_code == 200 else s.fail(21, "Ingest file", r.text)
        else:
            # fallback: use any small text file
            r = await c.post("/ingest/file",
                files={"file": ("notes.txt", b"Quicksort divides array recursively around a pivot.", "text/plain")},
                data={"hint": "algorithm notes"})
            d = r.json()
            s.ok(21, f'Ingest file (fallback): "{d.get("title")}" → {d.get("vault_folder")}') if r.status_code == 200 else s.fail(21, "Ingest file fallback", r.text)

        r = await c.get("/ingest/supported")
        s.ok(22, f'Supported: {len(r.json()["files"])} file types') if r.status_code == 200 else s.fail(22, "Ingest supported", r.text)

        # ── Vault ─────────────────────────────────────────────────────────────
        print("\n── Vault ──")

        r = await c.get("/vault/status")
        sections = {k: v["files"] for k, v in r.json()["sections"].items()}
        s.ok(23, f"Vault status: {sections}") if r.status_code == 200 else s.fail(23, "Vault status", r.text)

        r = await c.post("/vault/sync/now")
        d = r.json()
        s.ok(24, f'Vault sync: written={d.get("written")} skipped={d.get("skipped")} errors={d.get("errors")}') if r.status_code == 200 else s.fail(24, "Vault sync", r.text)

        # ── Brief ─────────────────────────────────────────────────────────────
        print("\n── Brief ──")

        r = await c.get("/brief")
        s.ok(25, f'Brief: {len(r.json().get("brief", ""))} chars') if r.status_code == 200 else s.fail(25, "Brief", str(r.text)[:80])

    # ── Summary ───────────────────────────────────────────────────────────────
    total = s.passed + s.failed
    print(f"\n{'='*44}")
    print(f"  {s.passed} passed  |  {s.failed} failed  |  {total} total")
    print(f"{'='*44}")
    return s.failed


if __name__ == "__main__":
    print(f"=== HEIMDALL FULL SUITE  ({BASE}) ===\n")
    failures = asyncio.run(run())
    sys.exit(1 if failures else 0)
