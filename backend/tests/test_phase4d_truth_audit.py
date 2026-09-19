import pytest
import html
from mongomock_motor import AsyncMongoMockClient

from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider, _clean_html_description as sr_clean
from app.modules.jobs.lever_provider import LeverJobProvider, _clean_html_description as lever_clean
from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider, _clean_html_description as gh_clean
from app.modules.jobs.providers import CuratedJobProvider
from app.modules.jobs.verification import OpportunityLifecycleStatus
from app.modules.jobs.url_classifier import ApplicationUrlType
from app.modules.jobs.lever_provider import is_internship_opportunity as is_lever_intern
from app.modules.jobs.smartrecruiters_provider import is_internship_opportunity as is_sr_intern
from app.modules.jobs.classification import classify_opportunity
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.jobs.schemas import JobOut


# ---------------------------------------------------------------------------
# A & B: Provider Field Preservation & HTML Entity Unescaping
# ---------------------------------------------------------------------------

def test_html_entity_unescape_smartrecruiters():
    raw_html = "<p>Qualifications:&#xa0;8+ years experience &amp; knowledge of Python &quot;expert&quot;&#xa0;level.</p>"
    cleaned = sr_clean(raw_html)
    assert "&#xa0;" not in cleaned
    assert "\u00a0" in cleaned or " " in cleaned
    assert "&amp;" not in cleaned
    assert "&" in cleaned
    assert "&quot;" not in cleaned
    assert '"' in cleaned


def test_html_entity_unescape_lever():
    raw_html = "<div>Responsibilities:&#xa0;Build scalable systems &amp; lead sprints.</div>"
    cleaned = lever_clean(raw_html)
    assert "&#xa0;" not in cleaned
    assert "&amp;" not in cleaned
    assert "&" in cleaned


def test_html_entity_unescape_greenhouse():
    raw_html = "<p>About the role:&#xa0;We are hiring a Software Engineer&#xa0;&amp; Tech Lead.</p>"
    cleaned = gh_clean(raw_html)
    assert "&#xa0;" not in cleaned
    assert "&amp;" not in cleaned
    assert "&" in cleaned


def test_smartrecruiters_normalization_field_preservation():
    provider = SmartRecruitersJobProvider()
    raw = {
        "id": "sr_744000147425379",
        "name": "Software Engineer - Backend",
        "company": {"name": "Bosch Group"},
        "location": {
            "city": "Bengaluru",
            "region": "Karnataka",
            "country": "in",
            "remote": False,
        },
        "releasedDate": "2026-09-01T10:00:00.000Z",
        "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/744000147425379",
        "applyUrl": "https://jobs.smartrecruiters.com/BoschGroup/744000147425379/apply",
        "typeOfEmployment": {"id": "full_time", "label": "Full-time"},
        "experienceLevel": {"id": "mid_senior_level", "label": "Mid-Senior"},
        "industry": {"label": "Automotive"},
        "function": {"label": "Engineering"},
    }
    normalized = provider.normalize_smartrecruiters_job(raw, "BoschGroup")

    assert normalized["id"] == "smartrecruiters_boschgroup_sr_744000147425379"
    assert normalized["title"] == "Software Engineer - Backend"
    assert normalized["company"] == "Bosch Group"
    assert "Bengaluru" in normalized["location"]
    assert normalized["country"] == "India"
    assert normalized["job_type"] == "full_time"
    assert normalized["apply_url"] == "https://jobs.smartrecruiters.com/BoschGroup/744000147425379/apply"
    assert normalized["is_direct_apply"] is True
    assert normalized["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    # Assert zero compensation fabrication
    assert normalized["salary_min"] is None
    assert normalized["salary_max"] is None
    assert normalized["salary_disclosed"] is False


def test_lever_normalization_field_preservation():
    provider = LeverJobProvider()
    raw = {
        "id": "lever_paytm_12345",
        "text": "Frontend Engineer",
        "categories": {
            "location": "Noida, Uttar Pradesh",
            "commitment": "Full Time",
            "department": "Engineering",
            "team": "Consumer Web",
        },
        "createdAt": 1756713600000,  # Valid epoch ms
        "hostedUrl": "https://jobs.lever.co/paytm/lever_paytm_12345",
        "applyUrl": "https://jobs.lever.co/paytm/lever_paytm_12345/apply",
        "workplaceType": "hybrid",
        "opening": "<p>Join Paytm consumer payments team.</p>",
        "lists": [
            {
                "text": "What you'll do",
                "content": "<ul><li>Develop React components</li><li>Optimize Core Web Vitals</li></ul>",
            },
            {
                "text": "What you'll need",
                "content": "<ul><li>3+ years in JavaScript, React, TypeScript</li></ul>",
            },
        ],
    }
    normalized = provider.normalize_lever_job(raw, "paytm", company_name="Paytm")

    assert normalized["id"] == "lever_paytm_lever_paytm_12345"
    assert normalized["title"] == "Frontend Engineer"
    assert normalized["company"] == "Paytm"
    assert "Noida" in normalized["location"]
    assert normalized["country"] == "India"
    assert normalized["job_type"] == "full_time"
    assert normalized["apply_url"] == "https://jobs.lever.co/paytm/lever_paytm_12345/apply"
    assert normalized["is_direct_apply"] is True
    assert normalized["verification_status"] == OpportunityLifecycleStatus.VERIFIED_ACTIVE.value
    # Verify description preserves the lists
    assert "What you'll do" in normalized["description"]
    assert "React" in normalized["description"]
    # Verify skills extracted
    assert any("react" in s.lower() for s in normalized["skills_required"])


# ---------------------------------------------------------------------------
# C: Required Skill Provenance (Section 8)
# ---------------------------------------------------------------------------

def test_skills_provenance_explicit_vs_contextual():
    # Case 1: Job with explicit Requirements section
    jd_with_reqs = """
    We are seeking a Backend Developer.
    
    Requirements:
    - Must have 3+ years experience in Python and PostgreSQL.
    - Strong knowledge of Docker.
    
    Nice to have:
    - Familiarity with Kubernetes.
    
    About our team:
    We also occasionally interact with Redis and AWS.
    """
    reqs = analyze_job_description(jd_with_reqs, "Backend Developer")
    must_have = list(reqs.must_have_skills)
    nice_to_have = list(reqs.preferred_skills)

    # Must-have skills must strictly come from the Requirements section
    assert any("python" in s.lower() for s in must_have)
    assert any("postgres" in s.lower() for s in must_have)
    assert any("docker" in s.lower() for s in must_have)
    # Nice-to-have strictly from nice-to-have section
    assert any("kubernetes" in s.lower() for s in nice_to_have)


def test_skills_provenance_no_fabrication_when_requirements_absent():
    # Case 2: Sparse/informal JD with NO requirements section
    jd_sparse = """
    Operations Assistant needed for warehouse logistics.
    Candidate will manage day to day scheduling and inventory counts.
    Contact hr@example.com to apply.
    """
    reqs = analyze_job_description(jd_sparse, "Operations Assistant")
    # Assert zero skills fabricated
    assert len(reqs.must_have_skills) == 0
    assert len(reqs.preferred_skills) == 0


def test_meesho_marketing_prose_spark_leak_prevented():
    """Verify company marketing prose ('spark of inspiration') is never extracted as candidate skill."""
    from app.modules.jobs.skill_vocabulary import extract_skills_from_text
    
    marketing_text = (
        "Welcome to Meesho, where every story begins with a spark of inspiration and a dash of entrepreneurship. "
        "We are on a mission to democratize internet commerce in India."
    )
    # Raw vocabulary extraction must not match idiom
    extracted = extract_skills_from_text(marketing_text)
    assert "Spark" not in extracted
    assert len(extracted) == 0

    # Taxonomy analysis must not elevate marketing prose into must_have_skills
    reqs = analyze_job_description(marketing_text, "Senior Associate - Monetisation")
    assert "Spark" not in reqs.must_have_skills
    assert "Spark" not in reqs.required_skills
    assert len(reqs.must_have_skills) == 0


def test_technical_spark_skill_preserved():
    """Verify legitimate technical Apache Spark requirements continue to be extracted accurately."""
    from app.modules.jobs.skill_vocabulary import extract_skills_from_text
    
    tech_jd = """
    We are seeking a Senior Data Engineer.
    Requirements:
    - 4+ years of experience with Apache Spark, Hadoop, and Kafka.
    - Proficiency in PySpark and SQL.
    - Deep understanding of distributed systems.
    """
    extracted = extract_skills_from_text(tech_jd)
    assert "Spark" in extracted
    assert "Kafka" in extracted
    assert "Hadoop" in extracted

    reqs = analyze_job_description(tech_jd, "Senior Data Engineer")
    assert any("spark" in s.lower() for s in reqs.must_have_skills)


# ---------------------------------------------------------------------------
# D: Compensation Grounding (Section 9)
# ---------------------------------------------------------------------------

def test_compensation_grounding_no_fabrication():
    # If source does not disclose salary, fields must remain None
    provider = LeverJobProvider()
    raw = {
        "id": "lever_no_sal",
        "text": "Data Analyst",
        "categories": {"location": "Bengaluru", "commitment": "Full Time"},
        "createdAt": 1756713600000,
        "applyUrl": "https://jobs.lever.co/company/lever_no_sal/apply",
    }
    normalized = provider.normalize_lever_job(raw, "company")
    assert normalized["salary_min"] is None
    assert normalized["salary_max"] is None
    assert normalized["salary_disclosed"] is False
    assert normalized["stipend_min"] is None


# ---------------------------------------------------------------------------
# E & F: Internship Classification & Experience (Sections 10 & 11)
# ---------------------------------------------------------------------------

def test_internship_classification_accuracy():
    # Valid internships on Lever
    assert is_lever_intern("Software Engineer Intern") is True
    assert is_lever_intern("Data Science Trainee") is True
    assert is_lever_intern("Product Management Intern - Payments") is True

    # Valid internships on SmartRecruiters
    assert is_sr_intern("Software Engineer- Intern") is True
    assert is_sr_intern("Web Content Writer- Intern") is True
    assert is_sr_intern("Graphic Designer- Intern") is True

    # Disqualify senior/leadership listings on SmartRecruiters even if title contains words
    assert is_sr_intern("Senior Software Engineer") is False
    assert is_sr_intern("Engineering Manager") is False
    assert is_sr_intern("Lead Architect") is False


# ---------------------------------------------------------------------------
# G & H: Pagination & Deduplication Truth (Sections 12 & 13)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pagination_and_zero_duplicate_overlap():
    client = AsyncMongoMockClient()
    db = client["test_pagination_db"]

    # Insert 50 deterministic verified active jobs
    docs = []
    for i in range(50):
        docs.append({
            "id": f"job_{i:03d}",
            "title": f"Engineer {i}",
            "company": f"TechCorp {i % 5}",
            "location": "Bengaluru, Karnataka, India",
            "country": "India",
            "job_type": "full_time",
            "opportunity_type": "FULL_TIME",
            "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
            "url_type": ApplicationUrlType.DIRECT_REQUISITION.value,
            "apply_url": f"https://techcorp.com/jobs/{i}",
            "posted_days_ago": i,
            "skills_required": ["Python"],
            "skills_nice_to_have": [],
            "source": "lever",
            "source_job_id": f"id_{i}",
            "salary_disclosed": False,
            "salary_min": None,
            "salary_max": None,
            "stipend_min": None,
            "is_remote": False,
            "fresher_friendly": True,
            "description": "Standard engineering role.",
            "industry": "Technology",
        })
    await db["jobs"].insert_many(docs)

    provider = CuratedJobProvider(db)

    # Page 1: 20 items
    p1 = await provider.search({
        "limit": 20,
        "skip": 0,
        "region": "india",
        "job_type": "full_time",
        "active_discovery_only": True,
        "direct_apply_only": True,
    })
    # Page 2: 20 items
    p2 = await provider.search({
        "limit": 20,
        "skip": 20,
        "region": "india",
        "job_type": "full_time",
        "active_discovery_only": True,
        "direct_apply_only": True,
    })

    assert len(p1) == 20
    assert len(p2) == 20

    p1_ids = [j["id"] for j in p1]
    p2_ids = [j["id"] for j in p2]

    # Verify ZERO overlap across pages
    overlap = set(p1_ids).intersection(set(p2_ids))
    assert len(overlap) == 0, f"Found overlapping IDs across pages: {overlap}"


# ---------------------------------------------------------------------------
# M: Live vs Benchmark Isolation (Section 18)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_vs_benchmark_strict_separation():
    client = AsyncMongoMockClient()
    db = client["test_benchmark_isolation_db"]

    # 1 live verified active job
    await db["jobs"].insert_one({
        "id": "live_job_001",
        "title": "Backend Engineer",
        "company": "Live ATS Employer",
        "location": "Bengaluru, India",
        "country": "India",
        "job_type": "full_time",
        "verification_status": OpportunityLifecycleStatus.VERIFIED_ACTIVE.value,
        "url_type": ApplicationUrlType.DIRECT_REQUISITION.value,
        "apply_url": "https://employer.com/live/1",
        "posted_days_ago": 1,
        "skills_required": ["Go"],
        "skills_nice_to_have": [],
        "source": "smartrecruiters",
        "source_job_id": "1",
        "salary_disclosed": False,
        "is_remote": False,
        "fresher_friendly": False,
        "description": "Live opening.",
        "industry": "Technology",
    })

    # 1 market benchmark job
    await db["jobs"].insert_one({
        "id": "benchmark_job_001",
        "title": "Backend Engineer Benchmark",
        "company": "Market Benchmark",
        "location": "Bengaluru, India",
        "country": "India",
        "job_type": "full_time",
        "verification_status": OpportunityLifecycleStatus.MARKET_BENCHMARK.value,
        "url_type": ApplicationUrlType.CORPORATE_PORTAL.value,
        "apply_url": "https://market.example.com",
        "posted_days_ago": 30,
        "skills_required": ["Go", "Kubernetes"],
        "skills_nice_to_have": [],
        "source": "curated_benchmark",
        "source_job_id": "bm_1",
        "salary_disclosed": False,
        "is_remote": False,
        "fresher_friendly": False,
        "description": "Benchmark reference.",
        "industry": "Technology",
    })

    provider = CuratedJobProvider(db)

    # Active discovery search (include_benchmarks = False)
    active_results = await provider.search({
        "region": "india",
        "job_type": "full_time",
        "active_discovery_only": True,
        "direct_apply_only": True,
    })

    assert len(active_results) == 1
    assert active_results[0]["id"] == "live_job_001"
    assert active_results[0]["verification_status"] == "VERIFIED_ACTIVE"
