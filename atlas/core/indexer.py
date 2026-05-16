"""
Smart Indexer — runs after every chat turn.
Uses a fast LLM to extract entities and decide what's worth saving.
Fires and forgets (asyncio background task).
"""
import asyncio
import json
import logging
from datetime import date, datetime
from atlas.db.vector_store import store, browse, VECTOR_TABLES
from atlas.db.session import get_session
from atlas.services.groq_service import chat as groq_chat
from atlas.core.vault_writer import sync_entry as vault_sync_entry
from atlas.core.date_parser import normalize_date_terms

logger = logging.getLogger(__name__)

# Use the fastest model for indexing — low latency, low cost
INDEX_MODEL = "groq-llama3-8b"

EXTRACT_PROMPT = """You are an entity extractor for a personal AI assistant called Heimdall.
Given a user message, extract any facts worth remembering long-term.

Return a JSON array. Each item has:
- "text": the fact to store (one concise sentence)
- "type": one of: person | place | idea | goal | preference | event | fact
- "save": true if worth storing, false if trivial/conversational filler

Rules:
- People: names, relationships, jobs, traits
- Places: locations the user mentions visiting or living
- Ideas: concepts, projects, plans the user is thinking about
- Goals: things the user wants to achieve
- Preferences: likes, dislikes, habits
- Events: things that happened today or recently
- Fact: anything else that doesn't fit above
- DO NOT save: greetings, "thanks", questions with no content, test messages

Respond ONLY with a valid JSON array, no explanation, no markdown.

Example output:
[
  {"text": "User's friend James works at DBS Bank", "type": "person", "save": true},
  {"text": "User visited Tiong Bahru today", "type": "place", "save": true},
  {"text": "User wants to achieve 4.0 GPA this semester", "type": "goal", "save": true}
]

User message: """

TRANSACTION_PROMPT = """You are a financial transaction extractor for a personal AI assistant.
Given a user message, extract any income or expense transactions.

Return a JSON array. Each item has:
- "amount": the number (positive float, no currency symbol)
- "type": "income" or "expense"
- "description": brief description of what was bought/sold
- "merchant": store/merchant name (if mentioned)
- "category": suggested category (food, transport, shopping, entertainment, bills, etc.)

Rules:
- Extract ONLY if the user mentions spending money or receiving income
- Look for phrases like "spent", "bought", "paid", "cost", "earned", "received", "salary"
- DO NOT extract budget limit statements (e.g., "set budget to $75", "budget is $150", "transport budget 75") - these are category settings, not actual transactions
- If no transaction is mentioned, return an empty array []
- Amount should be a number only, no $ or other symbols

Respond ONLY with a valid JSON array, no explanation, no markdown.

Example output:
[
  {"amount": 15.50, "type": "expense", "description": "coffee", "merchant": "Starbucks", "category": "food"},
  {"amount": 3000, "type": "income", "description": "monthly salary", "merchant": null, "category": "salary"}
]

User message: """


async def extract_and_index(user_message: str, assistant_reply: str) -> list[dict]:
    """
    Extract entities from a chat turn and store them.
    Returns list of stored items (for logging/debug).
    """
    # Normalize date terms in the user message before extraction
    user_message = normalize_date_terms(user_message)
    if len(user_message.strip()) < 10:
        return []

    prompt = EXTRACT_PROMPT + json.dumps(user_message)

    try:
        messages = [
            {"role": "system", "content": "You are a JSON-only entity extractor. Return only valid JSON arrays."},
            {"role": "user", "content": prompt}
        ]
        raw = await groq_chat(messages, model=INDEX_MODEL)

        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        entities = json.loads(raw)
        assert isinstance(entities, list)

    except Exception as e:
        logger.warning(f"Indexer extraction failed: {e} | raw={raw[:200] if 'raw' in dir() else '?'}")
        return []

    stored = []
    for entity in entities:
        if not entity.get("save", False):
            continue
        text = entity.get("text", "").strip()
        etype = entity.get("type", "fact")
        if not text:
            continue

        # Dedup: skip if very similar text already exists in vector_memory
        # (simple text prefix check — full semantic dedup is Phase 2B)
        try:
            existing = await browse("vector_memory", limit=200)
            texts_lower = [e["text"].lower() for e in existing]
            if any(text.lower()[:40] in t for t in texts_lower):
                logger.debug(f"Indexer skip (duplicate): {text[:60]}")
                continue
        except Exception:
            pass

        try:
            entry_id = await store(
                "vector_memory",
                text,
                source_type=etype,
                source_path="chat/auto"
            )
            stored.append({"id": entry_id, "text": text, "type": etype})
            logger.info(f"Indexed [{etype}]: {text[:80]}")
            await vault_sync_entry({"id": entry_id, "text": text, "source_type": etype, "source_path": "chat/auto"})
        except Exception as e:
            logger.warning(f"Indexer store failed: {e}")

    return stored


async def append_daily_log(user_message: str, assistant_reply: str):
    """
    Append this exchange to today's daily journal in vector_notes.
    Stores a summary sentence of what happened, tagged as source_type=daily_log.
    """
    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M")

    # Normalize date terms in user message for the log
    normalized_message = normalize_date_terms(user_message)
    
    # Build a one-line log entry from the user message
    # Keep it brief — just enough to reconstruct "what happened today"
    summary = f"[{today} {now}] User: {normalized_message[:120].strip()}"

    try:
        entry_id = await store(
            "vector_notes",
            summary,
            source_type="daily_log",
            source_path=f"journal/{today}"
        )
        await vault_sync_entry({"id": entry_id, "text": summary, "source_type": "daily_log", "source_path": f"journal/{today}"})
    except Exception as e:
        logger.warning(f"Daily log store failed: {e}")


async def extract_transactions(user_message: str) -> list[dict]:
    """
    Extract financial transactions from a user message.
    Returns list of transaction dicts.
    """
    if len(user_message.strip()) < 10:
        return []

    prompt = TRANSACTION_PROMPT + json.dumps(user_message)
    logger.info(f"[TransactionExtractor] Extracting from: {user_message[:50]}...")

    try:
        messages = [
            {"role": "system", "content": "You are a JSON-only transaction extractor. Return only valid JSON arrays."},
            {"role": "user", "content": prompt}
        ]
        raw = await groq_chat(messages, model=INDEX_MODEL)
        logger.info(f"[TransactionExtractor] LLM response: {raw[:200]}...")

        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        transactions = json.loads(raw)
        assert isinstance(transactions, list)
        logger.info(f"[TransactionExtractor] Parsed {len(transactions)} transactions")
        return transactions

    except Exception as e:
        logger.warning(f"Transaction extraction failed: {e}")
        return []


async def log_transactions(transactions: list[dict], user_id: str = "default"):
    """
    Log extracted transactions to the budget system.
    """
    if not transactions:
        return []

    from atlas.services import budget_service

    logged = []
    async with get_session() as session:
        for tx in transactions:
            try:
                amount = float(tx.get("amount", 0))
                if amount <= 0:
                    continue

                tx_type = tx.get("type", "expense")
                description = tx.get("description", "").strip()
                merchant = tx.get("merchant")
                category = tx.get("category")

                if not description:
                    continue

                # Try to find or create a category based on the suggested category
                category_id = None
                if category:
                    categories = await budget_service.list_budget_categories(session, user_id, type="expense")
                    # Simple matching - exact or contains
                    for cat in categories:
                        if category.lower() in cat.name.lower() or cat.name.lower() in category.lower():
                            category_id = cat.id
                            break
                    # If no match, create the category
                    if not category_id:
                        new_cat = await budget_service.create_budget_category(
                            session, user_id, name=category.title(),
                            type="expense", color="#6366f1", icon="tag"
                        )
                        category_id = new_cat.id

                result = await budget_service.add_transaction(
                    session,
                    user_id=user_id,
                    amount=amount,
                    type=tx_type,
                    description=description,
                    category_id=category_id,
                    merchant=merchant,
                )
                logged.append({"id": result.id, "amount": amount, "description": description})
                logger.info(f"Logged transaction: {description} - ${amount}")
            except Exception as e:
                logger.warning(f"Failed to log transaction: {e}")

    return logged


async def run_indexer(user_message: str, assistant_reply: str):
    """
    Entry point — call this as a background task after every chat turn.
    Runs extract_and_index, append_daily_log, and extract_transactions concurrently.
    """
    # Extract transactions first (these go to budget, not memory)
    transactions = await extract_transactions(user_message)
    if transactions:
        await log_transactions(transactions)

    # Run memory indexing (for non-transaction content)
    await asyncio.gather(
        extract_and_index(user_message, assistant_reply),
        append_daily_log(user_message, assistant_reply),
        return_exceptions=True
    )
