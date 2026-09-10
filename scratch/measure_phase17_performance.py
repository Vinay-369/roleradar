import time
import requests
import statistics

BASE_URL = "http://127.0.0.1:8000"

# Verify backend is responding
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"Backend health check: {r.status_code}")
except Exception as e:
    print(f"Health check failed: {e}")

# 1. Initial page (GET /jobs?limit=20&skip=0&region=india&active_discovery_only=true&direct_apply_only=true)
initial_times = []
for _ in range(5):
    t0 = time.perf_counter()
    r = requests.get(f"{BASE_URL}/jobs?limit=20&skip=0&region=india&active_discovery_only=true&direct_apply_only=true")
    dt = (time.perf_counter() - t0) * 1000
    if r.status_code == 200:
        initial_times.append(dt)

# 2. Next page (GET /jobs?limit=20&skip=20&region=india&active_discovery_only=true&direct_apply_only=true)
next_times = []
for _ in range(5):
    t0 = time.perf_counter()
    r = requests.get(f"{BASE_URL}/jobs?limit=20&skip=20&region=india&active_discovery_only=true&direct_apply_only=true")
    dt = (time.perf_counter() - t0) * 1000
    if r.status_code == 200:
        next_times.append(dt)

# 3. Role filtering (GET /jobs?limit=20&skip=0&role=software_engineer&region=india&active_discovery_only=true&direct_apply_only=true)
role_times = []
for _ in range(5):
    t0 = time.perf_counter()
    r = requests.get(f"{BASE_URL}/jobs?limit=20&skip=0&role=software_engineer&region=india&active_discovery_only=true&direct_apply_only=true")
    dt = (time.perf_counter() - t0) * 1000
    if r.status_code == 200:
        role_times.append(dt)

# 4. Internships endpoint (GET /internships?limit=20&skip=0&region=india&active_discovery_only=true&direct_apply_only=true)
intern_times = []
for _ in range(5):
    t0 = time.perf_counter()
    r = requests.get(f"{BASE_URL}/internships?limit=20&skip=0&region=india&active_discovery_only=true&direct_apply_only=true")
    dt = (time.perf_counter() - t0) * 1000
    if r.status_code == 200:
        intern_times.append(dt)

print("\n--- PERFORMANCE BENCHMARK RESULTS ---")
if initial_times:
    print(f"Initial Page:    avg={statistics.mean(initial_times):.1f}ms, min={min(initial_times):.1f}ms, p95={sorted(initial_times)[-1]:.1f}ms")
if next_times:
    print(f"Next Page:       avg={statistics.mean(next_times):.1f}ms, min={min(next_times):.1f}ms, p95={sorted(next_times)[-1]:.1f}ms")
if role_times:
    print(f"Role Filtering:  avg={statistics.mean(role_times):.1f}ms, min={min(role_times):.1f}ms, p95={sorted(role_times)[-1]:.1f}ms")
if intern_times:
    print(f"Internships:     avg={statistics.mean(intern_times):.1f}ms, min={min(intern_times):.1f}ms, p95={sorted(intern_times)[-1]:.1f}ms")
