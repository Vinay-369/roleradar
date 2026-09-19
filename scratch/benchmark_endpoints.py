import asyncio
import sys
import time

sys.path.insert(0, r"c:\VINAY\roleradar\backend")

from httpx import AsyncClient, ASGITransport
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.mongo import connect_to_mongo
from app.main import app


async def main():
    await connect_to_mongo()
    settings = get_settings()
    token = create_access_token({"sub": "test_perf_user@roleradar.internal", "role": "user"}, settings)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/jobs (20 items)
        t0 = time.perf_counter()
        resp1 = await client.get("/api/jobs?limit=20", headers=headers)
        d1 = (time.perf_counter() - t0) * 1000
        assert resp1.status_code == 200, f"Error {resp1.status_code}: {resp1.text}"
        data1 = resp1.json()
        print(f"GET /api/jobs (20 items): {d1:.2f}ms | total={data1.get('total')} | items={len(data1.get('items', []))}")

        # 2. Paginated jobs page 2
        t0 = time.perf_counter()
        resp2 = await client.get("/api/jobs?skip=20&limit=20", headers=headers)
        d2 = (time.perf_counter() - t0) * 1000
        assert resp2.status_code == 200
        data2 = resp2.json()
        print(f"GET /api/jobs page 2: {d2:.2f}ms | items={len(data2.get('items', []))}")

        # 3. GET /api/internships
        t0 = time.perf_counter()
        resp3 = await client.get("/api/internships?limit=20", headers=headers)
        d3 = (time.perf_counter() - t0) * 1000
        assert resp3.status_code == 200
        data3 = resp3.json()
        print(f"GET /api/internships: {d3:.2f}ms | total={data3.get('total')} | items={len(data3.get('items', []))}")

        # 4. GET /api/jobs/{id}
        items = data1.get("items", [])
        if items:
            sample_id = items[0]["id"]
            t0 = time.perf_counter()
            resp4 = await client.get(f"/api/jobs/{sample_id}", headers=headers)
            d4 = (time.perf_counter() - t0) * 1000
            assert resp4.status_code == 200
            print(f"GET /api/jobs/{sample_id}: {d4:.2f}ms | title={resp4.json().get('title')}")


if __name__ == "__main__":
    asyncio.run(main())
