"""
Test Telegram bot integration.
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def test_bot():
    """Test sending a message to Telegram."""
    from telegram import Bot
    from telegram.constants import ParseMode
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in environment")
        return
    
    if not chat_id:
        print("ERROR: TELEGRAM_CHAT_ID not set in environment")
        return
    
    print(f"Sending test message to chat_id: {chat_id}")
    
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text="🤖 **Heimdall Brain System**\n\n"
            "Telegram bot integration is working!\n\n"
            "The brain scheduler and reminder system are now active:\n"
            "- Memory consolidation every 6 hours\n"
            "- Memory linking every 1 hour\n"
            "- Vault indexing every 30 minutes\n"
            "- Temporal reminders enabled\n"
            "- Proactive check-ins enabled\n\n"
            "You'll receive reminders for:\n"
            "- Tasks scheduled at specific times\n"
            "- Goals and progress check-ins\n"
            "- Learning opportunities\n"
            "- Information gaps to fill",
            parse_mode=ParseMode.MARKDOWN
        )
        print("✓ Test message sent successfully")
    except Exception as e:
        print(f"✗ Error sending message: {e}")


if __name__ == "__main__":
    asyncio.run(test_bot())
