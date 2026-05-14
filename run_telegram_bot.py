"""Run Telegram bot in polling mode."""
import asyncio
from atlas.services.telegram_service import create_application

async def main():
    """Run the bot with polling."""
    application = create_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("Telegram bot started in polling mode. Press Ctrl+C to stop.")
    
    try:
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        print("Bot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
