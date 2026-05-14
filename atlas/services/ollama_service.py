import httpx
import os
import json
from typing import AsyncGenerator

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3:8b")


async def chat(messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """Send a chat request to Ollama and return the response text."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


async def chat_stream(messages: list[dict], model: str = DEFAULT_MODEL) -> AsyncGenerator[str, None]:
    """Stream chat tokens from Ollama one chunk at a time."""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue


async def list_models() -> list[str]:
    """Return names of all available Ollama models."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{OLLAMA_URL}/api/tags")
        response.raise_for_status()
        return [m["name"] for m in response.json()["models"]]
