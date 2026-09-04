"""
End-to-End Runtime Verification Script for Greenhouse Direct Live Opportunity Provider.
Executes real Greenhouse API sync, validates MongoDB persistence, checks pre-resume
discovery mode, and validates personalized matching enrichment.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mongomock_motor import AsyncMongoMockClient
from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
from app.modules.jobs.services import search_jobs
from app.modules.matching.services import get_or_compute_matches


async def run_runtime_verification():
    settings = get_settings()
    settings.GREENHOUSE_ENABLED = True

    client = AsyncMongoMockClient()
    db = client["roleradar_test"]

    print("=== STEP A & B: Syncing real Greenhouse board ('postman') ===")
    provider = GreenhouseJobProvider(settings)
    stats = await provider.sync_company_openings(db, "postman")
    print(f"Sync Result: {stats}")
    assert stats["fetched"] > 0
    assert stats["verified_active"] > 0
    assert stats["errors"] == []

    print("\n=== STEP C: Inspecting actual MongoDB records ===")
    cursor = db[Collections.JOBS].find({"source": "greenhouse"})
    jobs = await cursor.to_list(length=100)
    print(f"Total stored Greenhouse jobs in DB: {len(jobs)}")
    assert len(jobs) > 0

    sample = jobs[0]
    print("Sample Document Verification:")
    print(f"  id: {sample['id']}")
    print(f"  source: {sample['source']}")
    print(f"  source_job_id: {sample['source_job_id']}")
    print(f"  title: {sample['title']}")
    print(f"  company: {sample['company']}")
    print(f"  apply_url: {sample['apply_url']}")
    print(f"  url_type: {sample['url_type']}")
    print(f"  is_direct_apply: {sample['is_direct_apply']}")
    print(f"  verification_status: {sample['verification_status']}")
    print(f"  last_verified_at: {sample['last_verified_at']}")

    assert sample["source"] == "greenhouse"
    assert bool(sample["source_job_id"])
    assert "greenhouse.io" in sample["apply_url"]
    assert sample["url_type"] == "DIRECT_REQUISITION"
    assert sample["is_direct_apply"] is True
    assert sample["verification_status"] == "VERIFIED_ACTIVE"
    assert bool(sample["last_verified_at"])

    print("\n=== STEP D: Public Discovery Mode (No Resume) ===")
    discovered = await search_jobs(db, {"active_discovery_only": True, "direct_apply_only": True})
    print(f"Discovered jobs in feed (no resume): {len(discovered)}")
    assert len(discovered) == stats["verified_active"]
    for d in discovered[:3]:
        print(f"  - {d['title']} ({d['location']}) | URL: {d['apply_url']}")

    print("\n=== STEP E & F: Personalized Matching (With Resume) ===")
    user_id = "test_verified_user"
    resume = {
        "version": 1,
        "parsed": {"skills": ["python", "backend", "api", "docker"]},
    }
    candidate = {
        "user_id": user_id,
        "skills": ["python", "backend", "api", "docker"],
        "target_roles": ["Software Engineer"],
        "experience_years": 2,
    }

    mock_embedder = MagicMock()
    mock_embedder.similarity.return_value = 0.85

    matches = await get_or_compute_matches(db, user_id, resume, candidate, discovered, settings)
    print(f"Computed matches count: {len(matches)}")
    # The inventory count remains identical (not shrunk/replaced)
    assert len(matches) == len(discovered)
    assert matches[0]["has_match"] is True
    assert matches[0]["overall_score"] is not None
    print(f"Top match: {matches[0]['job_title']} | Score: {matches[0]['overall_score']} | Direct apply: {matches[0]['is_direct_apply']}")

    match_map = {m["job_id"]: m for m in matches}
    for d in discovered:
        m = match_map[d["id"]]
        assert m["apply_url"] == d["apply_url"]
        assert "greenhouse.io" in m["apply_url"]
        assert m["is_direct_apply"] is True

    print(f"Apply URL verified across all {len(matches)} jobs: e.g. {matches[0]['apply_url']}")

    print("\nALL RUNTIME VERIFICATION CHECKS PASSED CLEANLY!")


if __name__ == "__main__":
    asyncio.run(run_runtime_verification())
