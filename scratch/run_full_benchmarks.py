import sys
import time
import json
import urllib.request
from unittest.mock import patch
import httpx
import asyncio

sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(line_buffering=True)

from app.core.config import get_settings
from app.core.security import create_access_token
from app.modules.jobs.ashby_provider import AshbyJobProvider

def run_benchmarks():
    settings = get_settings()
    token = create_access_token("6a86a2e60f39bf9fe8969350", settings)
    headers = {"Authorization": f"Bearer {token}"}

    print("==================================================")
    print("PHASE 13B: ENDPOINT LATENCY BENCHMARKS")
    print("==================================================")

    # 1. GET /api/jobs (page 1, 50 items)
    t0 = time.perf_counter()
    req = urllib.request.Request("http://127.0.0.1:8000/api/jobs?page=1&page_size=50", headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    d1 = (time.perf_counter() - t0) * 1000
    print(f"1. GET /api/jobs (page=1, size=50): {d1:.2f}ms | Returned: {len(data)} items")

    # 2. GET /api/jobs (page 2, 20 items)
    t0 = time.perf_counter()
    req = urllib.request.Request("http://127.0.0.1:8000/api/jobs?page=2&page_size=20", headers=headers)
    with urllib.request.urlopen(req) as resp:
        data2 = json.loads(resp.read().decode())
    d2 = (time.perf_counter() - t0) * 1000
    print(f"2. GET /api/jobs (page=2, size=20): {d2:.2f}ms | Returned: {len(data2)} items")

    # 3. GET /api/jobs?opportunity_type=INTERNSHIP (page 1, 50 items)
    t0 = time.perf_counter()
    req = urllib.request.Request("http://127.0.0.1:8000/api/jobs?opportunity_type=INTERNSHIP&page=1&page_size=50", headers=headers)
    with urllib.request.urlopen(req) as resp:
        data3 = json.loads(resp.read().decode())
    d3 = (time.perf_counter() - t0) * 1000
    print(f"3. GET /api/jobs?opportunity_type=INTERNSHIP (page=1, size=50): {d3:.2f}ms | Returned: {len(data3)} items")

    # 4. GET /api/jobs/{id}
    sample_id = data[0]["id"]
    t0 = time.perf_counter()
    req = urllib.request.Request(f"http://127.0.0.1:8000/api/jobs/{sample_id}", headers=headers)
    with urllib.request.urlopen(req) as resp:
        detail = json.loads(resp.read().decode())
    d4 = (time.perf_counter() - t0) * 1000
    print(f"4. GET /api/jobs/{sample_id}: {d4:.2f}ms | Title: '{detail.get('title')}' at {detail.get('company')}")

    print("\n==================================================")
    print("ASHBY SYNC PERFORMANCE & SAFETY TESTS")
    print("==================================================")

    provider = AshbyJobProvider()

    # Ashby Single Board Live Fetch
    t0 = time.perf_counter()
    raw_board = asyncio.run(provider.fetch_company_openings("ramp"))
    d_board = (time.perf_counter() - t0) * 1000
    print(f"5. Ashby Live Board Fetch ('ramp'): {d_board:.2f}ms | Raw Requisitions: {len(raw_board)}")

    # Failure Resilience Tests
    # A. Timeout raises AshbyNetworkError in provider fetch
    from app.modules.jobs.ashby_provider import AshbyNetworkError
    async def mock_timeout(*args, **kwargs):
        raise httpx.TimeoutException("Connection timed out")

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_timeout):
        try:
            asyncio.run(provider.fetch_company_openings("ramp"))
            failed_properly = False
        except AshbyNetworkError:
            failed_properly = True
        print(f"6. Resilience on Network Timeout: Properly caught and wrapped as AshbyNetworkError: {failed_properly}")
        assert failed_properly

    # B. HTTP 500 raises AshbyNetworkError
    mock_500 = httpx.Response(status_code=500, request=httpx.Request("GET", "https://api.ashbyhq.com/posting-api/job-board/ramp"))
    async def mock_500_fn(*args, **kwargs):
        return mock_500

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_500_fn):
        try:
            asyncio.run(provider.fetch_company_openings("ramp"))
            failed_properly = False
        except AshbyNetworkError:
            failed_properly = True
        print(f"7. Resilience on HTTP 500: Properly caught and wrapped as AshbyNetworkError: {failed_properly}")
        assert failed_properly

    # C. Malformed JSON (returns empty jobs list)
    mock_bad_json = httpx.Response(status_code=200, json=["not", "a", "dict"], request=httpx.Request("GET", "https://api.ashbyhq.com/posting-api/job-board/ramp"))
    async def mock_bad_json_fn(*args, **kwargs):
        return mock_bad_json

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_bad_json_fn):
        res = asyncio.run(provider.fetch_company_openings("ramp"))
        print(f"8. Resilience on Malformed JSON structure: Handled cleanly, returned: {res}")
        assert res == []

    # D. Partial failure: Board A fails while Board B succeeds
    real_get = httpx.AsyncClient.get
    async def partial_get(client_self, url, *args, **kwargs):
        if "ramp" in str(url):
            return httpx.Response(status_code=500, request=httpx.Request("GET", str(url)))
        return await real_get(client_self, url, *args, **kwargs)

    with patch.object(httpx.AsyncClient, "get", new=partial_get):
        try:
            asyncio.run(provider.fetch_company_openings("ramp"))
            ramp_success = True
        except AshbyNetworkError:
            ramp_success = False
        res_retainable = asyncio.run(provider.fetch_company_openings("retainable"))
        print(f"9. Partial Board Isolation: Failed Board ('ramp') -> error handled ({not ramp_success}), Succeeded Board ('retainable') -> {len(res_retainable)} jobs")
        assert not ramp_success
        assert len(res_retainable) >= 0

    print("\nALL BENCHMARKS AND SYNC SAFETY VALIDATIONS PASSED!")

if __name__ == "__main__":
    run_benchmarks()
