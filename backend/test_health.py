import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10) as client:
        r = await client.get("/health")
        print("Health:", r.json())
        
        r2 = await client.get("/api/materials")
        print("Materials count:", len(r2.json()))

asyncio.run(test())
