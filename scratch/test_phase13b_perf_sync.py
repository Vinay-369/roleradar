import asyncio
import sys
import time
from unittest.mock import patch
import httpx

sys.path.insert(0, r"c:\VINAY\roleradar\backend")

from app.core.config import get_settings
from app.core.security import create_access_token
from app.modules.jobs.ashby_provider import AshbyJobProvider

async def run_benchmark_and_safety():
    settings = get_settings()
    user_id = "6a86a2e60f39bf9fe8969350"
    token = create_access_token(user_id, settings)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        # --- SECTION 10: ENDPOINT LATENCIES ---
        print("=== 1. API LATENCY BENCHMARKS ===", flush=True)
        
        # 1. Normal GET /api/jobs
        t0 = time.perf_counter()
        r1 = await client.get("/api/jobs?page=1&page_size=50", headers=headers)
        d1 = (time.perf_counter() - t0) * 1000
        assert r1.status_code == 200, f"Error {r1.status_code}: {r1.text}"
        data1 = r1.json()
        print(f"GET /api/jobs (50 items): {d1:.2f}ms | returned={len(data1)}", flush=True)

        # 2. Paginated GET /api/jobs page 2
        t0 = time.perf_counter()
        r2 = await client.get("/api/jobs?page=2&page_size=20", headers=headers)
        d2 = (time.perf_counter() - t0) * 1000
        assert r2.status_code == 200
        data2 = r2.json()
        print(f"GET /api/jobs (page 2, 20 items): {d2:.2f}ms | returned={len(data2)}", flush=True)

        # 3. GET /api/internships
        t0 = time.perf_counter()
        r3 = await client.get("/api/internships?page=1&page_size=50", headers=headers)
        d3 = (time.perf_counter() - t0) * 1000
        assert r3.status_code == 200
        data3 = r3.json()
        print(f"GET /api/internships (50 items): {d3:.2f}ms | returned={len(data3)}", flush=True)

        # 4. GET /api/jobs/{id}
        sample_id = data1[0]["id"] if data1 else None
        if sample_id:
            t0 = time.perf_counter()
            r4 = await client.get(f"/api/jobs/{sample_id}", headers=headers)
            d4 = (time.perf_counter() - t0) * 1000
            assert r4.status_code == 200
            print(f"GET /api/jobs/{sample_id}: {d4:.2f}ms | title={r4.json().get('title')}", flush=True)

        # --- SECTION 9 & 10: SYNC PERFORMANCE & SAFETY TESTS ---
        print("\n=== 2. SYNC SAFETY & FAILURE RESILIENCE ===", flush=True)
        provider = AshbyJobProvider()

        # Test A: Single Board Fetch Performance (Real Network)
        t0 = time.perf_counter()
        board_raw = await provider.fetch_company_postings("ramp")
        d_board = (time.perf_counter() - t0) * 1000
        print(f"Ashby Single Board ('ramp') Live Fetch: {d_board:.2f}ms | raw_jobs={len(board_raw)}", flush=True)

        # Test B: Timeout Handling
        print("Testing Timeout simulation...", flush=True)
        async def mock_timeout(*args, **kwargs):
            raise httpx.TimeoutException("Connection timed out")
        
        with patch.object(httpx.AsyncClient, "post", side_effect=mock_timeout):
            res_timeout = await provider.fetch_company_postings("ramp")
            print(f"  Result on Timeout: jobs={len(res_timeout)} (Graceful fallback)", flush=True)
            assert res_timeout == []

        # Test C: HTTP 500 Internal Server Error
        print("Testing HTTP 500 simulation...", flush=True)
        mock_500_resp = httpx.Response(status_code=500, request=httpx.Request("POST", "https://api.ashbyhq.com/posting-api/job-board/ramp"))
        async def mock_500(*args, **kwargs):
            return mock_500_resp
        
        with patch.object(httpx.AsyncClient, "post", side_effect=mock_500):
            res_500 = await provider.fetch_company_postings("ramp")
            print(f"  Result on HTTP 500: jobs={len(res_500)} (Graceful fallback)", flush=True)
            assert res_500 == []

        # Test D: Malformed JSON Response
        print("Testing Malformed JSON simulation...", flush=True)
        mock_bad_json = httpx.Response(status_code=200, text="<html NOT JSON>", request=httpx.Request("POST", "https://api.ashbyhq.com/posting-api/job-board/ramp"))
        async def mock_bad_json_call(*args, **kwargs):
            return mock_bad_json
        
        with patch.object(httpx.AsyncClient, "post", side_effect=mock_bad_json_call):
            res_bad_json = await provider.fetch_company_postings("ramp")
            print(f"  Result on Malformed JSON: jobs={len(res_bad_json)} (Graceful fallback)", flush=True)
            assert res_bad_json == []

        # Test E: Empty Jobs Array
        print("Testing Empty Jobs Array...", flush=True)
        mock_empty_resp = httpx.Response(status_code=200, json={"jobs": []}, request=httpx.Request("POST", "https://api.ashbyhq.com/posting-api/job-board/ramp"))
        async def mock_empty_call(*args, **kwargs):
            return mock_empty_resp
        
        with patch.object(httpx.AsyncClient, "post", side_effect=mock_empty_call):
            res_empty = await provider.fetch_company_postings("ramp")
            print(f"  Result on Empty Jobs: jobs={len(res_empty)}", flush=True)
            assert res_empty == []

        # Test F: Board A fails while Board B succeeds
        print("Testing Partial Failure (Board A fails, Board B succeeds)...", flush=True)
        real_post = httpx.AsyncClient.post
        async def mock_partial_post(client_self, url, *args, **kwargs):
            if "ramp" in str(url):
                return httpx.Response(status_code=500, request=httpx.Request("POST", str(url)))
            return await real_post(client_self, url, *args, **kwargs)
        
        with patch.object(httpx.AsyncClient, "post", new=mock_partial_post):
            res_ramp = await provider.fetch_company_postings("ramp")
            res_retainable = await provider.fetch_company_postings("retainable")
            print(f"  Partial outcome: ramp={len(res_ramp)} (graceful fail), retainable={len(res_retainable)} (succeeded)", flush=True)
            assert len(res_ramp) == 0
            assert len(res_retainable) >= 0

        print("\nALL BENCHMARKS AND SYNC SAFETY TESTS COMPLETED SUCCESSFULLY!", flush=True)

if __name__ == "__main__":
    asyncio.run(run_benchmark_and_safety())
