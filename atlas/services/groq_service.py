import httpx
import os
import json
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODELS = {
    "groq-llama4-scout": "meta-llama/llama-4-scout-17b-16e-instruct",
    "groq-llama3-70b": "llama-3.3-70b-versatile",
    "groq-llama3-8b": "llama-3.1-8b-instant",
}


async def chat(messages: list[dict], model: str = "groq-llama4-scout") -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in .env")
    api_model = MODELS.get(model, model)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": api_model, "messages": messages, "stream": False},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def chat_stream(messages: list[dict], model: str = "groq-llama4-scout") -> AsyncGenerator[str, None]:
    """Stream chat tokens from Groq using SSE."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in .env")
    api_model = MODELS.get(model, model)
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream(
            "POST",
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": api_model, "messages": messages, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    token = data["choices"][0].get("delta", {}).get("content", "")
                    if token:
                        yield token
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
