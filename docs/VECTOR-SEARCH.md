# Vector Search in Heimdall
*How embeddings, pgvector, and semantic search actually work*

---

## The Core Idea

Normal database search is exact — it finds rows where the text *literally matches* your query.

Vector search is semantic — it finds rows that *mean the same thing* as your query, even if the words are completely different.

**Example:**
```
Query:   "computer hardware plans"
Matches: "I am saving money for a new PC build with RTX 3090"  ← distance: 0.42
Matches: "Atlas is my personal AI assistant on a Dell R620"    ← distance: 0.58
Misses:  "The weather in London is rainy today"                ← distance: 0.81
```

The word "computer" never appears in the top result, but the *meaning* is close, so it surfaces.

---

## Step 1: Embeddings (Text → Numbers)

Before you can search by meaning, text has to be converted into numbers. This is called an **embedding**.

```
"I want to build a new PC"
        ↓  nomic-embed-text (runs in Ollama locally)
[0.021, -0.847, 0.334, 0.109, ... × 768 numbers]
```

- The model (`nomic-embed-text`) was trained on billions of sentences
- It learned that similar sentences produce *similar numbers*
- The result is a **768-dimensional vector** — a list of 768 floats
- Every piece of text maps to a unique point in this 768-dimensional space

**In code:**
```python
# atlas/db/vector_store.py
async def embed_text(text: str) -> list[float]:
    response = await client.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text},
    )
    return response.json()["embedding"]  # list of 768 floats
```

---

## Step 2: Storage (Numbers → PostgreSQL)

The 768 numbers are stored alongside the original text in PostgreSQL, using the **pgvector** extension.

```sql
CREATE TABLE vector_memory (
    id          TEXT PRIMARY KEY,
    text        TEXT NOT NULL,         -- original text
    source_type TEXT NOT NULL,         -- 'fact', 'note', 'goal', 'code'
    source_path TEXT DEFAULT '',       -- where it came from
    embedding   vector(768)            -- the 768 numbers
);
```

`vector(768)` is a special column type added by pgvector. PostgreSQL normally can't store or compare these — pgvector makes it possible.

---

## Step 3: Search (Query → Distance → Results)

When you search, the query text is also embedded into 768 numbers. Then PostgreSQL compares that query vector against every stored vector using **cosine distance**.

```
Query vector:   [0.12, -0.55, 0.33, ...]
Stored vector:  [0.10, -0.51, 0.31, ...]  ← distance 0.04 (very similar)
Stored vector:  [0.80,  0.23, -0.40, ...]  ← distance 0.95 (very different)
```

**Cosine distance** measures the angle between two vectors in 768-dimensional space:
- `0.0` = identical meaning
- `0.3–0.5` = closely related
- `0.7+` = unrelated

The SQL looks like this:
```sql
SELECT text, source_type, embedding <=> $1::vector AS distance
FROM vector_memory
ORDER BY embedding <=> $1::vector   -- <=> is the cosine distance operator
LIMIT 5;
```

`<=>` is a pgvector operator — it doesn't exist in plain PostgreSQL.

---

## The Four Tables

Heimdall splits stored data into four separate vector tables, each for a different type of content:

| Table | What goes in | Example |
|---|---|---|
| `vector_memory` | Facts, preferences, context | "I prefer dark mode in all my apps" |
| `vector_notes` | Obsidian vault notes (future) | "Meeting notes: discussed React migration" |
| `vector_chat_summaries` | Compressed past conversations | "User asked about PC build budget on May 5" |
| `vector_code_chunks` | Indexed project code (future) | `def calculate_route(origin, dest):` |

`search_all()` searches all four tables at once and returns the best matches sorted by distance.

---

## Full Flow: Storing a Memory

```
You:   "Store: I prefer dark mode in all my tools"
          ↓
embed_text()
  → Sends text to Ollama (nomic-embed-text)
  → Returns 768 floats
          ↓
store()
  → Generates a UUID
  → INSERTs (id, text, source_type, source_path, embedding) into vector_memory
          ↓
PostgreSQL stores the row with the vector column
```

---

## Full Flow: Semantic Search

```
You:   Search "night mode preferences"
          ↓
embed_text("night mode preferences")
  → Returns 768 floats for the query
          ↓
search()
  → Sends query vector to PostgreSQL
  → PostgreSQL computes cosine distance vs every stored embedding
  → Returns rows ordered by distance (closest first)
          ↓
Results:
  [0.18] "I prefer dark mode in all my tools"     ← strong match
  [0.52] "Atlas runs on a Dell PowerEdge R620"    ← weak match
```

---

## Why nomic-embed-text?

It's a local model that runs entirely on the R620 — no API key, no cloud, no cost. 768 dimensions is a sweet spot: detailed enough for good results, small enough to be fast on CPU.

Alternatives (future):
- `mxbai-embed-large` — 1024-dim, higher quality, slower
- OpenAI `text-embedding-3-small` — cloud, costs money

---

## Files

| File | Purpose |
|---|---|
| `atlas/db/vector_store.py` | Core functions: `embed_text`, `store`, `search`, `search_all` |
| `vector_explorer.py` | Web UI for manually testing the vector store |
| `docker-compose.yml` | Runs `pgvector/pgvector:pg15` (PostgreSQL with vector support) |

---

## Limitations Right Now

- **No index**: searches do a full table scan (fine for small datasets, slow at 100k+ rows). An IVFFlat index will be added later once there's enough data.
- **Tables are independent**: `search_all` merges results after the fact — it's not a single joined query.
- **768-dim is fixed**: changing the embedding model would require re-embedding all stored data.
