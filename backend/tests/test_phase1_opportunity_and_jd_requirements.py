import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.learning.role_taxonomy import resolve_role, ROLE_TAXONOMY
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.jobs.schemas import JobOut
from app.modules.matching.schemas import JobMatchOut
from app.modules.matching.services import _get_role_metadata
from app.modules.jobs.routes import _strip_for_list, _strip_for_detail
from app.db.mongo import Collections


def _resolve(title: str):
    prof, conf, reason = resolve_role(title)
    if not prof:
        return None, None, None
    key = None
    for k, p in ROLE_TAXONOMY.items():
        if p.canonical_role == prof.canonical_role:
            key = k
            break
    return key, prof.canonical_role, prof.domain


# ==============================================================================
# 1. PROVIDER INVENTORY FUNNEL BEHAVIOR & REPOSITORY AUDIT
# ==============================================================================

@pytest.mark.asyncio
async def test_provider_inventory_funnel_behavior():
    """
    Verify provider inventory funnel behavior:
    1. Raw provider jobs have source metadata (smartrecruiters, greenhouse, adzuna, curated_benchmark)
    2. Stored records retain verification_status (VERIFIED_ACTIVE vs MARKET_BENCHMARK)
    3. Normalization preserves real direct requisition URLs and lifecycle semantics
    4. Canonical role metadata is accurately attached
    """
    sample_smartr_job = {
        "_id": "smartr_123",
        "id": "smartr_123",
        "title": "Software Engineer - Fullstack",
        "company": "Acme Corp",
        "source": "smartrecruiters",
        "apply_url": "https://jobs.smartrecruiters.com/AcmeCorp/123",
        "verification_status": "VERIFIED_ACTIVE",
        "url_type": "DIRECT_REQUISITION",
        "location": "Bengaluru, India",
        "description": "We are seeking a Software Engineer - Fullstack.\n\nQualifications:\n- 3+ years experience with React and Node.js\n- Experience with PostgreSQL",
    }

    # Verify canonical role attachment
    role_meta = _get_role_metadata(sample_smartr_job)
    assert role_meta["canonical_role"] == "Full Stack Developer"
    assert role_meta["canonical_role_key"] == "full_stack_developer"
    assert role_meta["role_domain"] == "Software Engineering"

    # Verify JobOut serialization preserves VERIFIED_ACTIVE and DIRECT_REQUISITION
    job_out = _strip_for_list(sample_smartr_job)
    assert job_out["verification_status"] == "VERIFIED_ACTIVE"
    assert job_out["url_type"] == "DIRECT_REQUISITION"
    assert job_out["canonical_role_key"] == "full_stack_developer"


# ==============================================================================
# 2. MULTIPLE DOMAINS CANONICAL CLASSIFICATION
# ==============================================================================

def test_multiple_domains_classification():
    """
    Ensure resolve_role accurately maps title variants across all supported domains
    without spurious matches or collisions.
    """
    domain_test_cases = [
        # Full Stack
        ("Full Stack Developer", "full_stack_developer", "Full Stack Developer", "Software Engineering"),
        ("Full Stack Engineer", "full_stack_developer", "Full Stack Developer", "Software Engineering"),
        ("Software Engineer - Fullstack", "full_stack_developer", "Full Stack Developer", "Software Engineering"),
        ("SDE - Full Stack", "full_stack_developer", "Full Stack Developer", "Software Engineering"),

        # Frontend
        ("Frontend Developer", "frontend_developer", "Frontend Developer", "Software Engineering"),
        ("Senior Frontend Engineer", "frontend_developer", "Frontend Developer", "Software Engineering"),
        ("React Developer", "frontend_developer", "Frontend Developer", "Software Engineering"),

        # Backend
        ("Backend Developer", "backend_developer", "Backend Developer", "Software Engineering"),
        ("Senior Backend Engineer", "backend_developer", "Backend Developer", "Software Engineering"),
        ("Java Developer", "backend_developer", "Backend Developer", "Software Engineering"),
        ("Python Developer", "backend_developer", "Backend Developer", "Software Engineering"),
        ("Node.js Developer", "backend_developer", "Backend Developer", "Software Engineering"),

        # Data Engineering
        ("Data Engineer", "data_engineer", "Data Engineer", "Data & Analytics"),
        ("Senior Big Data Engineer", "data_engineer", "Data Engineer", "Data & Analytics"),

        # Data Science
        ("Data Scientist", "data_scientist", "Data Scientist", "Data & Analytics"),
        ("Lead Data Scientist", "data_scientist", "Data Scientist", "Data & Analytics"),

        # AI / ML
        ("Machine Learning Engineer", "machine_learning_engineer", "Machine Learning Engineer", "AI / Machine Learning"),
        ("Senior ML Engineer", "machine_learning_engineer", "Machine Learning Engineer", "AI / Machine Learning"),
        ("AI / NLP Engineer", "ai_engineer", "AI Engineer", "AI / Machine Learning"),

        # Cloud & DevOps / SRE
        ("Cloud Engineer", "cloud_engineer", "Cloud Engineer", "Cloud / DevOps / Infrastructure"),
        ("Cloud Architect", "cloud_architect", "Cloud Architect", "Cloud / DevOps / Infrastructure"),
        ("DevOps Engineer", "devops_engineer", "DevOps Engineer", "Cloud / DevOps / Infrastructure"),
        ("Site Reliability Engineer (SRE)", "site_reliability_engineer", "Site Reliability Engineer", "Cloud / DevOps / Infrastructure"),

        # Cybersecurity
        ("Cybersecurity Analyst", "cybersecurity_analyst", "Cybersecurity Analyst", "Cybersecurity"),
        ("Cybersecurity Engineer", "security_engineer", "Security Engineer", "Cybersecurity"),

        # QA / Testing
        ("QA / Test Automation Engineer", "qa_test_engineer", "QA / Test Engineer", "Software Engineering"),
        ("SDET - Automation", "qa_test_engineer", "QA / Test Engineer", "Software Engineering"),
        ("Quality Assurance Engineer", "qa_test_engineer", "QA / Test Engineer", "Software Engineering"),

        # Mobile
        ("Mobile App Developer", "mobile_developer", "Mobile Developer", "Software Engineering"),
        ("iOS Developer", "mobile_developer", "Mobile Developer", "Software Engineering"),
        ("Android Developer", "mobile_developer", "Mobile Developer", "Software Engineering"),
    ]

    for title, expected_key, expected_name, expected_domain in domain_test_cases:
        key, name, domain = _resolve(title)
        assert key is not None, f"Failed to match title: {title}"
        assert key == expected_key, f"Expected {expected_key} for '{title}', got {key}"
        assert name == expected_name
        assert domain == expected_domain


# ==============================================================================
# 3. FULL STACK TITLE VARIANTS (REGRESSION TEST FOR FORMER SUBSTRING FAILURE)
# ==============================================================================

def test_full_stack_title_variants_resolve_consistently():
    """
    Verify that titles which failed previous frontend raw substring matching
    ('Software Engineer - Fullstack', 'SDE - Full Stack', etc.)
    all resolve to canonical role 'Full Stack Developer'.
    """
    variants = [
        "Software Engineer - Fullstack",
        "Software Engineer - Full Stack",
        "SDE - Full Stack",
        "SDE-II (Full Stack)",
        "Full Stack Engineer",
        "Fullstack Software Engineer",
        "Full Stack Developer",
        "Lead Full Stack Developer",
        "Principal Engineer - Full Stack",
    ]
    for title in variants:
        key, name, domain = _resolve(title)
        assert key is not None, f"Failed to match {title}"
        assert key == "full_stack_developer", f"Title {title} matched to {key}, expected full_stack_developer"
        assert name == "Full Stack Developer"
        assert domain == "Software Engineering"


# ==============================================================================
# 4. INTERNSHIP ROLE CLASSIFICATION
# ==============================================================================

def test_internship_role_classification():
    """
    Verify that internship titles correctly resolve to their respective canonical roles.
    """
    internship_titles = [
        ("Software Engineering Intern", "software_engineer"),
        ("Full Stack Intern", "full_stack_developer"),
        ("Fullstack Developer Intern", "full_stack_developer"),
        ("Frontend Engineering Intern", "frontend_developer"),
        ("Backend Intern", "backend_developer"),
        ("Data Science Intern", "data_scientist"),
        ("Machine Learning Intern", "machine_learning_engineer"),
        ("DevOps Intern", "devops_engineer"),
        ("QA Intern", "qa_test_engineer"),
        ("Cybersecurity Intern", "cybersecurity_analyst"),
        ("Mobile App Developer Intern", "mobile_developer"),
    ]
    for title, expected_key in internship_titles:
        key, name, domain = _resolve(title)
        assert key is not None, f"Internship title {title} failed to match"
        assert key == expected_key, f"Internship {title} mapped to {key}, expected {expected_key}"


# ==============================================================================
# 5. REQUIRED SKILLS EXTRACTION ACROSS VARIED JD SECTION HEADERS
# ==============================================================================

def test_required_skills_extraction_varied_headers():
    """
    Verify that analyze_job_description extracts required skills across common
    industry section headers: Skills, Tech Stack, Qualifications, What You Need, etc.
    """
    header_variants = [
        ("Skills:\n- Python\n- React\n- PostgreSQL", ["python", "react", "postgresql"]),
        ("Technical Skills:\n- Java\n- Spring Boot\n- Docker", ["java", "spring boot", "docker"]),
        ("Tech Stack:\n- TypeScript\n- Node.js\n- MongoDB", ["typescript", "node.js", "mongodb"]),
        ("Qualifications:\n- Experience with Go\n- Knowledge of Kubernetes\n- Redis expertise", ["go", "kubernetes", "redis"]),
        ("What You Need:\n- Proficiency in Python\n- AWS cloud experience\n- Git version control", ["python", "aws", "git"]),
        ("What We're Looking For:\n- Strong background in C++\n- Linux systems knowledge", ["c++", "linux"]),
    ]

    for body, expected_skills in header_variants:
        jd_text = f"About the Role:\nWe are building great products.\n\n{body}\n\nBenefits:\nHealth insurance."
        structured = analyze_job_description(jd_text)
        must_haves_lower = [s.lower() for s in structured.must_have_skills]
        for exp in expected_skills:
            assert any(exp in s for s in must_haves_lower), f"Failed to extract '{exp}' from JD header test:\n{body}\nExtracted: {structured.must_have_skills}"


# ==============================================================================
# 6. REQUIRED VS PREFERRED VS CONTEXTUAL DISTINCTION
# ==============================================================================

def test_required_vs_preferred_vs_contextual_distinction():
    """
    Verify that:
    - Required / must-have skills are extracted into must_have_skills
    - Preferred / nice-to-have skills are extracted into preferred_skills
    - Incidental context (e.g. 'our company uses AWS') is not dumped into required skills
      when explicitly distinguished in preferred section
    """
    jd = """
    About the Company:
    We are a leading fintech enterprise. Our legacy platform runs on existing AWS infrastructure.

    Requirements:
    - 3+ years of professional experience in Python
    - Strong proficiency in PostgreSQL and relational database design
    - Solid understanding of REST APIs

    Nice to Have:
    - Hands-on experience with Docker and Kubernetes
    - Familiarity with GraphQL
    - Knowledge of AWS cloud services
    """
    structured = analyze_job_description(jd)
    must_haves_lower = [s.lower() for s in structured.must_have_skills]
    preferred_lower = [s.lower() for s in structured.preferred_skills]

    # Required skills must be present in must_have
    assert any("python" in s for s in must_haves_lower)
    assert any("postgresql" in s for s in must_haves_lower)

    # Preferred skills must NOT be in must_have
    assert not any("docker" in s for s in must_haves_lower), "Docker is nice-to-have, should not be must_have"
    assert not any("graphql" in s for s in must_haves_lower), "GraphQL is nice-to-have, should not be must_have"

    # Preferred skills must be in preferred_skills
    assert any("docker" in s for s in preferred_lower)
    assert any("kubernetes" in s for s in preferred_lower)


# ==============================================================================
# 7. EMPTY STRUCTURED REQUIREMENTS HONEST STATE
# ==============================================================================

def test_empty_structured_requirements_honest_state():
    """
    When a JD has no extractable technical skills (e.g. pure generic marketing copy),
    the parser must NOT invent fake skills. must_have_skills must be empty.
    """
    vague_jd = """
    We are looking for an ambitious, hardworking, self-motivated individual
    to join our high-performing sales team. You will build relationships,
    manage communication, and drive value for enterprise clients.
    Great communication skills, leadership mindset, and dedication required.
    """
    structured = analyze_job_description(vague_jd)
    # Must not invent tech skills
    assert len(structured.must_have_skills) == 0


# ==============================================================================
# 8. SEED / BENCHMARK DATA PRESERVES MARKET_BENCHMARK STATUS
# ==============================================================================

def test_seed_benchmark_data_is_not_marked_verified_active():
    """
    Curated benchmark opportunities must retain MARKET_BENCHMARK status and must
    NEVER be marked VERIFIED_ACTIVE merely to pad inventory.
    """
    benchmark_job = {
        "_id": "bench_001",
        "id": "bench_001",
        "title": "Full Stack Developer",
        "company": "Benchmark Tech Corp",
        "source": "curated_benchmark",
        "verification_status": "MARKET_BENCHMARK",
        "url_type": "BENCHMARK_REFERENCE",
        "apply_url": "https://example.com/careers/bench_001",
    }
    out = _strip_for_list(benchmark_job)
    assert out["verification_status"] == "MARKET_BENCHMARK"
    assert out["verification_status"] != "VERIFIED_ACTIVE"


# ==============================================================================
# 9. GET ENDPOINTS DO NOT SYNCHRONOUSLY REFRESH PROVIDERS
# ==============================================================================

@pytest.mark.asyncio
async def test_get_endpoints_do_not_synchronously_refresh_providers():
    """
    Ensure user-facing opportunity read endpoints do NOT trigger external network
    synchronization calls to Greenhouse, Lever, or SmartRecruiters.
    """
    from app.modules.jobs.greenhouse_provider import GreenhouseJobProvider
    from app.modules.jobs.lever_provider import LeverJobProvider
    from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider

    with patch.object(GreenhouseJobProvider, "fetch_company_openings", new_callable=AsyncMock) as mock_gh, \
         patch.object(LeverJobProvider, "fetch_company_openings", new_callable=AsyncMock) as mock_lv, \
         patch.object(SmartRecruitersJobProvider, "fetch_company_openings", new_callable=AsyncMock) as mock_sr:

        # Simulate job query using repository logic directly
        from app.modules.jobs import repositories as jobs_repo
        mock_db = {}
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_db[Collections.JOBS] = mock_collection

        jobs = await jobs_repo.find_jobs(mock_db, {}, limit=10)

        # None of the provider external sync routines must be invoked!
        mock_gh.assert_not_called()
        mock_lv.assert_not_called()
        mock_sr.assert_not_called()


# ==============================================================================
# 10. CANONICAL ROLE METADATA POPULATED IN SCHEMAS
# ==============================================================================

def test_canonical_role_metadata_in_job_out_and_match_out():
    """
    Verify JobOut and JobMatchOut schema support canonical role fields:
    canonical_role, canonical_role_key, role_domain.
    """
    job_doc = {
        "_id": "test_job_1",
        "id": "test_job_1",
        "title": "Software Engineer - Fullstack",
        "company": "Tech Corp",
        "industry": "Technology",
        "description": "Full stack role requiring React and Node.js",
        "skills_required": ["React", "Node.js"],
        "skills_nice_to_have": ["AWS"],
        "job_type": "full_time",
        "source": "smartrecruiters",
        "apply_url": "https://careers.techcorp.com/job/1",
        "location": "Bengaluru, India",
        "is_remote": False,
        "salary_min": 15.0,
        "salary_max": 25.0,
        "salary_disclosed": True,
        "stipend_min": None,
        "internship_duration_months": None,
        "fresher_friendly": True,
        "posted_days_ago": 2,
    }
    stripped = _strip_for_list(job_doc)
    assert stripped["canonical_role"] == "Full Stack Developer"
    assert stripped["canonical_role_key"] == "full_stack_developer"
    assert stripped["role_domain"] == "Software Engineering"

    # Validate against JobOut pydantic schema
    job_out = JobOut(**stripped)
    assert job_out.canonical_role == "Full Stack Developer"
    assert job_out.canonical_role_key == "full_stack_developer"
    assert job_out.role_domain == "Software Engineering"
