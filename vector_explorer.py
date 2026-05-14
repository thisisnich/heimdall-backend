from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from string import Template
import asyncio
from atlas.db.vector_store import init_vector_tables, store, search, search_all, VECTOR_TABLES

app = FastAPI()

HTML = Template("""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heimdall — Vector Explorer</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; padding: 2rem; }
  h1 { font-size: 1.6rem; font-weight: 700; color: #a78bfa; margin-bottom: 0.25rem; letter-spacing: -0.02em; }
  .subtitle { color: #64748b; font-size: 0.85rem; margin-bottom: 2.5rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
  @media(max-width: 800px) { .grid { grid-template-columns: 1fr; } }
  .card { background: #1e2130; border: 1px solid #2d3148; border-radius: 12px; padding: 1.5rem; }
  .card h2 { font-size: 1rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1.25rem; }
  label { display: block; font-size: 0.8rem; color: #64748b; margin-bottom: 0.35rem; margin-top: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; }
  label:first-of-type { margin-top: 0; }
  input, select, textarea { width: 100%; background: #0f1117; border: 1px solid #2d3148; border-radius: 8px; color: #e2e8f0; padding: 0.55rem 0.75rem; font-size: 0.9rem; font-family: inherit; outline: none; transition: border-color 0.15s; }
  input:focus, select:focus, textarea:focus { border-color: #7c3aed; }
  textarea { resize: vertical; min-height: 80px; }
  button { margin-top: 1.1rem; width: 100%; padding: 0.65rem; background: #7c3aed; color: #fff; border: none; border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: background 0.15s; }
  button:hover { background: #6d28d9; }
  button:active { background: #5b21b6; }
  .results { margin-top: 1.5rem; }
  .result-item { background: #0f1117; border: 1px solid #2d3148; border-radius: 8px; padding: 0.9rem 1rem; margin-bottom: 0.6rem; position: relative; }
  .result-text { font-size: 0.92rem; line-height: 1.5; color: #e2e8f0; margin-bottom: 0.5rem; }
  .badges { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
  .badge { font-size: 0.72rem; padding: 0.2rem 0.55rem; border-radius: 99px; font-weight: 600; }
  .badge-type { background: #1e3a5f; color: #60a5fa; }
  .badge-table { background: #2d1b4e; color: #a78bfa; }
  .badge-path { background: #1a2e1a; color: #4ade80; font-weight: 400; font-size: 0.7rem; }
  .distance-bar-wrap { margin-bottom: 0.6rem; }
  .distance-label { font-size: 0.72rem; color: #64748b; margin-bottom: 0.2rem; }
  .distance-bar { height: 4px; background: #2d3148; border-radius: 99px; overflow: hidden; }
  .distance-fill { height: 100%; border-radius: 99px; }
  .msg-success { background: #14532d; border: 1px solid #166534; color: #4ade80; border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.85rem; margin-top: 1rem; }
  .msg-error { background: #450a0a; border: 1px solid #7f1d1d; color: #f87171; border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.85rem; margin-top: 1rem; }
  .empty { color: #475569; font-size: 0.85rem; padding: 1rem 0; text-align: center; }
  .spinner { display: none; }
  form.loading .spinner { display: inline; }
  form.loading button span.btn-text { display: none; }
  .table-counts { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }
  .count-pill { background: #1e2130; border: 1px solid #2d3148; border-radius: 99px; padding: 0.3rem 0.85rem; font-size: 0.78rem; color: #94a3b8; }
  .count-pill strong { color: #a78bfa; }
</style>
</head>
<body>

<h1>⚡ Heimdall Vector Explorer</h1>
<p class="subtitle">Test semantic search against pgvector — store text, then search by meaning</p>

<div class="table-counts" id="counts">
  ${counts_html}
</div>

<div class="grid">

  <!-- STORE -->
  <div class="card">
    <h2>📥 Store Text</h2>
    <form method="post" action="/store" onsubmit="this.classList.add('loading')">
      <label>Text to store</label>
      <textarea name="text" required placeholder="e.g. I prefer dark mode in all my tools"></textarea>
      <label>Table</label>
      <select name="table">
        ${table_options}
      </select>
      <label>Source type</label>
      <input name="source_type" value="fact" placeholder="fact / note / goal / code">
      <label>Source path <span style="color:#475569">(optional)</span></label>
      <input name="source_path" placeholder="e.g. goals/pc.md">
      <button type="submit"><span class="btn-text">Store →</span><span class="spinner">Embedding…</span></button>
    </form>
    ${store_msg}
  </div>

  <!-- SEARCH -->
  <div class="card">
    <h2>🔍 Semantic Search</h2>
    <form method="post" action="/search" onsubmit="this.classList.add('loading')">
      <label>Query</label>
      <input name="query" required placeholder="e.g. computer hardware plans" value="${last_query}">
      <label>Table</label>
      <select name="table">
        <option value="__all__">All tables</option>
        ${table_options}
      </select>
      <label>Results limit</label>
      <input name="limit" type="number" value="${last_limit}" min="1" max="20">
      <button type="submit"><span class="btn-text">Search →</span><span class="spinner">Searching…</span></button>
    </form>
    <div class="results">
      ${results_html}
    </div>
  </div>

</div>
</body>
</html>
""")


def make_table_options(selected="vector_memory"):
    opts = []
    for t in VECTOR_TABLES:
        sel = "selected" if t == selected else ""
        opts.append(f'<option value="{t}" {sel}>{t}</option>')
    return "\n".join(opts)


def distance_color(d: float) -> str:
    if d < 0.35:
        return "#4ade80"
    if d < 0.55:
        return "#facc15"
    return "#f87171"


def render_results(results: list[dict], table_label: str = "") -> str:
    if not results:
        return '<p class="empty">No results found.</p>'
    html = []
    for r in results:
        d = r["distance"]
        pct = max(0, min(100, int((1 - d) * 100)))
        color = distance_color(d)
        tbl = r.get("table", table_label)
        path_badge = f'<span class="badge badge-path">{r["source_path"]}</span>' if r.get("source_path") else ""
        tbl_badge = f'<span class="badge badge-table">{tbl}</span>' if tbl else ""
        html.append(f"""
        <div class="result-item">
          <div class="distance-bar-wrap">
            <div class="distance-label">Similarity: {pct}% &nbsp;·&nbsp; distance {d:.4f}</div>
            <div class="distance-bar"><div class="distance-fill" style="width:{pct}%;background:{color}"></div></div>
          </div>
          <div class="result-text">{r['text']}</div>
          <div class="badges">
            <span class="badge badge-type">{r['source_type']}</span>
            {tbl_badge}
            {path_badge}
          </div>
        </div>
        """)
    return "\n".join(html)


async def get_counts() -> str:
    from atlas.db.vector_store import get_conn
    conn = await get_conn()
    try:
        pills = []
        for t in VECTOR_TABLES:
            try:
                row = await conn.fetchrow(f"SELECT COUNT(*) AS c FROM {t}")
                pills.append(f'<span class="count-pill">{t}: <strong>{row["c"]}</strong></span>')
            except Exception:
                pills.append(f'<span class="count-pill">{t}: <strong>?</strong></span>')
        return "\n".join(pills)
    finally:
        await conn.close()


@app.on_event("startup")
async def startup():
    await init_vector_tables()


@app.get("/", response_class=HTMLResponse)
async def index():
    counts = await get_counts()
    return HTML.substitute(
        counts_html=counts,
        table_options=make_table_options(),
        store_msg="",
        results_html='<p class="empty">Enter a query above and hit Search.</p>',
        last_query="",
        last_limit=5,
    )


@app.post("/store", response_class=HTMLResponse)
async def store_handler(
    text: str = Form(...),
    table: str = Form(...),
    source_type: str = Form("fact"),
    source_path: str = Form(""),
):
    try:
        entry_id = await store(table, text, source_type, source_path)
        msg = f'<div class="msg-success">✅ Stored! ID: <code>{entry_id}</code></div>'
    except Exception as e:
        msg = f'<div class="msg-error">❌ Error: {e}</div>'
    counts = await get_counts()
    return HTML.substitute(
        counts_html=counts,
        table_options=make_table_options(selected=table),
        store_msg=msg,
        results_html='<p class="empty">Enter a query above and hit Search.</p>',
        last_query="",
        last_limit=5,
    )


@app.post("/search", response_class=HTMLResponse)
async def search_handler(
    query: str = Form(...),
    table: str = Form("__all__"),
    limit: int = Form(5),
):
    try:
        if table == "__all__":
            raw = await search_all(query, limit=limit)
            for r in raw:
                r["table"] = ""
            label = ""
        else:
            raw = await search(table, query, limit=limit)
            label = table
        results_html = render_results(raw, table_label=label)
    except Exception as e:
        results_html = f'<div class="msg-error">❌ Error: {e}</div>'
    counts = await get_counts()
    return HTML.substitute(
        counts_html=counts,
        table_options=make_table_options(selected=table if table != "__all__" else "vector_memory"),
        store_msg="",
        results_html=results_html,
        last_query=query,
        last_limit=limit,
    )
