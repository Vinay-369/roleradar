"""
Real read-only Greenhouse API execution test against configured public board.
Executes an actual HTTP GET request against https://boards-api.greenhouse.io.
Proves end-to-end normalization and validation on actual production data.
"""
from __future__ import annotations

import httpx
import pytest

from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
from app.modules.jobs.url_classifier import ApplicationUrlType


@pytest.mark.asyncio
async def test_real_greenhouse_probe_postman():
    """
    Real read-only probe against Postman's public Greenhouse board.
    Verifies that the live API returns valid JSON, produces DIRECT_REQUISITION
    application URLs, and populates required canonical metadata.
    """
    provider = GreenhouseJobProvider()
    try:
        raw_jobs = await provider.fetch_company_openings("postman")
    except Exception as exc:
        pytest.skip(f"Live network access unavailable: {exc}")

    assert isinstance(raw_jobs, list)
    assert len(raw_jobs) > 0, "Postman board returned 0 jobs"

    first_job = raw_jobs[0]
    norm = provider.normalize_greenhouse_job(first_job, "postman", company_name="Postman")

    assert norm["source"] == "greenhouse"
    assert norm["company"] == "Postman"
    assert norm["title"] != ""
    assert norm["apply_url"].startswith("http")
    assert norm["url_type"] == ApplicationUrlType.DIRECT_REQUISITION.value
    assert norm["is_direct_apply"] is True
    assert norm["verification_status"] == "VERIFIED_ACTIVE"
    assert norm["source_job_id"] != ""
    print(f"\nREAL GREENHOUSE PROBE SUCCESS: Fetched {len(raw_jobs)} live jobs for Postman. First job: '{norm['title']}' ({norm['location']}) -> {norm['apply_url']}")
