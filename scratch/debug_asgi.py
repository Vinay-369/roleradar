import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx
from app.main import app
from app.db.mongo import connect_to_mongo, close_mongo_connection

async def test():
    await connect_to_mongo()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/health")
            print("Health response:", r.status_code, r.text)
            r2 = await client.get("/api/jobs")
            print("Jobs response:", r2.status_code, r2.text[:200])
    except Exception as e:
        print("Exception:", type(e), e)
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test())
