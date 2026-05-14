from fastapi import APIRouter
import os
from atlas.services.ollama_service import list_models as ollama_list
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/models", tags=["models"])

CLOUD_MODELS = [
    {"id": "deepseek-flash",      "name": "DeepSeek V3 Flash",       "provider": "deepseek", "speed": "fast",   "cost": "$0.14/M", "key_env": "DEEPSEEK_API_KEY"},
    {"id": "deepseek-pro",        "name": "DeepSeek V3 Pro",         "provider": "deepseek", "speed": "medium", "cost": "$1.74/M", "key_env": "DEEPSEEK_API_KEY"},
    {"id": "groq-llama4-scout",   "name": "Llama 4 Scout (Groq)",    "provider": "groq",     "speed": "fast",   "cost": "free",    "key_env": "GROQ_API_KEY"},
    {"id": "groq-llama3-70b",     "name": "Llama 3 70B (Groq)",      "provider": "groq",     "speed": "fast",   "cost": "free",    "key_env": "GROQ_API_KEY"},
    {"id": "groq-llama3-8b",      "name": "Llama 3 8B (Groq)",       "provider": "groq",     "speed": "fast",   "cost": "free",    "key_env": "GROQ_API_KEY"},
]


@router.get("")
async def list_all_models():
    try:
        local_names = await ollama_list()
        local = [
            {"id": m, "name": m, "provider": "ollama", "speed": "slow" if "8b" in m else "medium", "cost": "free", "available": True}
            for m in local_names if "embed" not in m
        ]
    except Exception:
        local = []

    cloud = [
        {**m, "available": bool(os.getenv(m["key_env"]))}
        for m in CLOUD_MODELS
    ]

    return {"local": local, "cloud": cloud}
