"""Telegram bot API endpoints."""
from fastapi import APIRouter, Request, HTTPException
from atlas.services.telegram_service import handle_webhook

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates."""
    try:
        update = await request.json()
        await handle_webhook(update)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/info")
async def webhook_info():
    """Get webhook information."""
    return {
        "message": "Telegram webhook endpoint",
        "endpoint": "/telegram/webhook",
        "method": "POST",
    }
