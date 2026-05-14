# init_db.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from atlas.db.models import Base
import os
from dotenv import load_dotenv
load_dotenv()

async def init():
    engine = create_async_engine(os.getenv("DATABASE_URL"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

asyncio.run(init())