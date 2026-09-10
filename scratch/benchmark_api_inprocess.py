import asyncio
import time
import statistics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx
from app.main import app
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.modules.auth.dependencies import get_current_user

async def run_benchmarks():
    await connect_to_mongo()
    app.dependency_overrides[get_current_user] = lambda: {"_id": "test_bench_user", "email": "bench@example.com", "role": "candidate"}
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Warm-up
            await client.get("/api/health")
            
            # 2. Initial Page
            initial_latencies = []
            for _ in range(5):
                t0 = time.perf_counter()
                r = await client.get("/api/jobs?limit=20&skip=0&region=india&active_discovery_only=true&direct_apply_only=true")
                dt = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    initial_latencies.append(dt)

            # 3. Next Page (skip=20)
            next_latencies = []
            for _ in range(5):
                t0 = time.perf_counter()
                r = await client.get("/api/jobs?limit=20&skip=20&region=india&active_discovery_only=true&direct_apply_only=true")
                dt = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    next_latencies.append(dt)

            # 4. Role Filtering (Software Engineer)
            role_latencies = []
            for _ in range(5):
                t0 = time.perf_counter()
                r = await client.get("/api/jobs?limit=20&skip=0&role=software_engineer&region=india&active_discovery_only=true&direct_apply_only=true")
                dt = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    role_latencies.append(dt)

            # 5. Internships Endpoint
            intern_latencies = []
            for _ in range(5):
                t0 = time.perf_counter()
                r = await client.get("/api/jobs?limit=20&skip=0&job_type=internship&region=india&active_discovery_only=true&direct_apply_only=true")
                dt = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    intern_latencies.append(dt)

        print("\n--- IN-PROCESS API BENCHMARK RESULTS ---")
        if initial_latencies:
            print(f"Initial Page:    avg={statistics.mean(initial_latencies):.1f}ms, min={min(initial_latencies):.1f}ms, p95={sorted(initial_latencies)[-1]:.1f}ms")
        if next_latencies:
            print(f"Next Page:       avg={statistics.mean(next_latencies):.1f}ms, min={min(next_latencies):.1f}ms, p95={sorted(next_latencies)[-1]:.1f}ms")
        if role_latencies:
            print(f"Role Filtering:  avg={statistics.mean(role_latencies):.1f}ms, min={min(role_latencies):.1f}ms, p95={sorted(role_latencies)[-1]:.1f}ms")
        if intern_latencies:
            print(f"Internships:     avg={statistics.mean(intern_latencies):.1f}ms, min={min(intern_latencies):.1f}ms, p95={sorted(intern_latencies)[-1]:.1f}ms")
    finally:
        app.dependency_overrides.clear()
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
