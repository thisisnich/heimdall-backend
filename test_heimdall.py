"""
Heimdall Integration Test Suite
Run: python3 test_heimdall.py
Tests the live API at localhost:8000
"""
import asyncio
import httpx
import json
import sys
import time

BASE = "http://localhost:8000"
PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
INFO = "\033[33m·\033[0m"

results = []

def section(title):
    print(f"\n\033[1m\033[34m── {title} ──\033[0m")

def ok(name, detail=""):
    results.append((True, name))
    print(f"  {PASS} {name}" + (f"  \033[2m{detail}\033[0m" if detail else ""))

def fail(name, detail=""):
    results.append((False, name))
    print(f"  {FAIL} {name}" + (f"  \033[31m{detail}\033[0m" if detail else ""))

def info(msg):
    print(f"  {INFO} \033[2m{msg}\033[0m")


async def run():
    async with httpx.AsyncClient(timeout=60, base_url=BASE) as c:

        # ── 1. Root ──────────────────────────────────────────────
        section("Root & Docs")
        try:
            r = await c.get("/")
            d = r.json()
            assert d["name"] == "Heimdall"
            ok("GET / returns Heimdall identity", f"status={d['status']}")
        except Exception as e:
            fail("GET /", str(e))

        try:
            r = await c.get("/docs")
            assert r.status_code == 200
            ok("GET /docs (Swagger UI) reachable")
        except Exception as e:
            fail("GET /docs", str(e))

        # ── 2. Health ─────────────────────────────────────────────
        section("Health — /health")
        try:
            r = await c.get("/health")
            d = r.json()
            assert "services" in d
            svcs = d["services"]
            for svc, info_d in svcs.items():
                status = info_d.get("status", "unknown")
                if status == "ok":
                    ok(f"{svc} is healthy", info_d.get("detail", ""))
                else:
                    fail(f"{svc} is not healthy", info_d.get("detail", ""))
        except Exception as e:
            fail("/health endpoint", str(e))

        # ── 3. Models ─────────────────────────────────────────────
        section("Models — /models")
        local_models = []
        cloud_models = []
        try:
            r = await c.get("/models")
            d = r.json()
            local_models = d.get("local", [])
            cloud_models = d.get("cloud", [])
            ok(f"Local models returned", f"{len(local_models)} model(s): {[m['id'] for m in local_models]}")
            ok(f"Cloud models returned", f"{len(cloud_models)} model(s)")
            avail_cloud = [m for m in cloud_models if m["available"]]
            if avail_cloud:
                ok(f"Cloud models available", f"{[m['id'] for m in avail_cloud]}")
            else:
                fail("No cloud models available — check API keys in .env")
        except Exception as e:
            fail("/models endpoint", str(e))

        # ── 4. Dashboard ──────────────────────────────────────────
        section("Dashboard — /dashboard")
        try:
            r = await c.get("/dashboard")
            assert r.status_code == 200
            assert "Heimdall" in r.text
            assert "switchTab" in r.text
            assert "sendChat" in r.text
            ok("Dashboard HTML served", f"{len(r.text):,} chars")
            ok("Required JS functions present (switchTab, sendChat)")
        except Exception as e:
            fail("/dashboard", str(e))

        # ── 5. Embeddings ─────────────────────────────────────────
        section("Embeddings — atlas/core/embeddings.py")
        try:
            from atlas.core.embeddings import embed, embed_batch, cosine_similarity
            v1 = await embed("machine learning and neural networks")
            assert len(v1) == 768
            ok("embed() returns 768-dim vector", f"first val={v1[0]:.4f}")

            v2 = await embed("deep learning artificial intelligence")
            v3 = await embed("the price of eggs at the supermarket")
            sim_high = cosine_similarity(v1, v2)
            sim_low  = cosine_similarity(v1, v3)
            ok(f"Similar texts score higher", f"related={sim_high:.3f} vs unrelated={sim_low:.3f}")
            assert sim_high > sim_low, "Similarity ordering wrong!"

            vecs = await embed_batch(["hello world", "goodbye world"])
            assert len(vecs) == 2 and len(vecs[0]) == 768
            ok("embed_batch() works", f"2 vectors returned")
        except Exception as e:
            fail("Embeddings", str(e))

        # ── 6. Vector Store ───────────────────────────────────────
        section("Vector Store — /memory")
        stored_id = None
        try:
            r = await c.post("/memory/store", json={
                "text": "Heimdall test entry — integration test run",
                "table": "vector_memory",
                "source_type": "test",
                "source_path": "test_heimdall.py"
            })
            assert r.status_code == 200
            stored_id = r.json().get("id")
            ok("POST /memory/store", f"id={stored_id[:8]}…" if stored_id else "no id")
        except Exception as e:
            fail("POST /memory/store", str(e))

        try:
            r = await c.get("/memory/search", params={"q": "integration test run", "limit": 5})
            assert r.status_code == 200
            results_mem = r.json()
            assert isinstance(results_mem, list)
            found = any("test" in res.get("text", "").lower() for res in results_mem)
            ok("GET /memory/search returns results", f"{len(results_mem)} result(s)")
            if found:
                ok("Stored entry is semantically retrievable")
            else:
                fail("Stored entry not found in search results")
        except Exception as e:
            fail("GET /memory/search", str(e))

        # ── 7. Chat (non-streaming) ───────────────────────────────
        section("Chat — POST /chat")
        groq_model = next((m["id"] for m in cloud_models if m["available"] and m["provider"] == "groq"), None)
        test_model = groq_model or (local_models[0]["id"] if local_models else "qwen3:1.7b")
        info(f"Using model: {test_model}")
        try:
            t0 = time.time()
            r = await c.post("/chat", json={
                "message": "Reply with exactly: HEIMDALL_TEST_OK",
                "model": test_model,
                "history": []
            })
            elapsed = time.time() - t0
            assert r.status_code == 200
            d = r.json()
            assert "reply" in d and len(d["reply"]) > 0
            ok(f"POST /chat got reply", f"{elapsed:.1f}s — model={d['model']}")
            info(f"Reply preview: {d['reply'][:80].strip()}")
        except Exception as e:
            fail("POST /chat", str(e))

        # ── 8. Chat streaming ─────────────────────────────────────
        section("Chat — POST /chat/stream (SSE)")
        try:
            t0 = time.time()
            tokens = []
            event_types = set()
            async with c.stream("POST", "/chat/stream", json={
                "message": "Say hello in 5 words",
                "model": test_model,
                "history": []
            }) as resp:
                assert resp.status_code == 200
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    ev = json.loads(line[6:])
                    event_types.add(ev["type"])
                    if ev["type"] == "token":
                        tokens.append(ev["data"])
                    if ev["type"] == "done":
                        break
            elapsed = time.time() - t0
            full_reply = "".join(tokens)
            ok(f"Stream received {len(tokens)} tokens", f"{elapsed:.1f}s total")
            ok(f"Event types seen: {event_types}")
            ok(f"Full streamed reply", full_reply[:60].strip())
        except Exception as e:
            fail("POST /chat/stream", str(e))

        # ── Summary ───────────────────────────────────────────────
        print("\n" + "─" * 48)
        passed = sum(1 for r in results if r[0])
        total  = len(results)
        colour = "\033[32m" if passed == total else "\033[33m" if passed > total // 2 else "\033[31m"
        print(f"{colour}  {passed}/{total} checks passed\033[0m")
        if passed < total:
            print("\n  Failed:")
            for ok_, name in results:
                if not ok_:
                    print(f"    {FAIL} {name}")
        print()


if __name__ == "__main__":
    asyncio.run(run())
