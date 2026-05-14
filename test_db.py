import asyncio, asyncpg

async def test():
    conn = await asyncpg.connect("postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall")
    version = await conn.fetchval("SELECT version()")
    print(f"Connected to: {version}")
    await conn.close()

asyncio.run(test())
