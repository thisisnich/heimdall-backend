import httpx
import os
import json
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

MODELS = {
    "deepseek-flash": "deepseek-chat",
    "deepseek-pro": "deepseek-reasoner",
}


async def chat(messages: list[dict], model: str = "deepseek-flash") -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set in .env")
    api_model = MODELS.get(model, model)
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": api_model, "messages": messages, "stream": False},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def chat_stream(messages: list[dict], model: str = "deepseek-flash") -> AsyncGenerator[str, None]:
    """Stream chat tokens from DeepSeek using SSE."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set in .env")
    api_model = MODELS.get(model, model)
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
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
