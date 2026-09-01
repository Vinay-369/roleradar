"""
Phase 18 Test Suite: Production ATS Template System and Rendering Quality.

Tests:
1. Sparse Fresher (ATS_FRESHER, 1-page budget, clean layout)
2. Dense Fresher (ATS_FRESHER, compact variant, 1-page budget)
3. Experienced 1-Page (ATS_PROFESSIONAL, 1-page budget)
4. Experienced 2-Page (ATS_PROFESSIONAL, 2-page budget)
5. Senior 2-Page (ATS_SENIOR, executive/classic variant, 2-page budget)
6. Academic / Research (Explicit Academic ResumeStrategy with Publications & Research)
7. Multi-Role Company (Company -> Role Progression -> Bullets per role without flattening)
8. Project-Heavy Candidate (Projects emphasized, Technologies line distinct from bullets)
9. Certification-Heavy Candidate (Certifications preserved and formatted cleanly)
10. Career Switcher (Projects & Skills prioritized before historical experience)
11. Property Invariants:
    - Template selection cannot create evidence.
    - Renderer cannot modify evidence, metrics, or dates.
    - Renderer cannot move evidence between entities.
    - Visual wrapping does not create new semantic bullets.
12. End-to-End PDF ATS Parseability Verification (TailoredCandidateProfile vs Extracted PDF text).
"""
import pytest
from app.modules.jobs.taxonomy import JDRequirements
from app.modules.resume.classification import (
    CareerClassification,
    CareerClassificationResult,
)
from app.modules.resume.models import (
    CandidateProfile,
    WorkExperienceEntity,
    RoleProgression,
    ResponsibilityGroup,
    ProjectEntity,
    EducationEntity,
    AdditionalSectionEntity,
    EvidenceUnit,
    ClaimType,
)
from app.modules.tailoring.strategy import (
    CareerStage,
    TemplateFamily,
    ContentDensity,
    build_resume_strategy,
)
from app.modules.tailoring.export import (
    generate_pdf,
    generate_docx,
    render_candidate_profile_to_text,
    verify_ats_pdf_parseability,
    measure_pdf_page_count,
)


def _make_sample_candidate(
    name: str = "Alex Morgan",
    career_stage: str = "PROFESSIONAL",
    years_exp: float = 4.0,
    has_progression: bool = False,
    is_academic: bool = False,
    is_fresher: bool = False,
) -> tuple[CandidateProfile, CareerClassificationResult]:
    personal = {
        "name": name,
        "email": "alex.morgan@example.com",
        "phone": "+1 555-0199",
        "location": "San Francisco, CA",
        "linkedin": "linkedin.com/in/alexmorgan",
        "github": "github.com/alexmorgan",
    }

    if is_fresher:
        exps = [
            WorkExperienceEntity(
                id="exp-1",
                company="Tech Innovators",
                role="Software Engineering Intern",
                dates="May 2023 - Aug 2023",
                bullets=["Built data ingestion pipeline reducing latency by 35% using Python."],
            )
        ]
        projs = [
            ProjectEntity(
                id="proj-1",
                title="Distributed Key-Value Store",
                technologies=["Go", "Raft", "gRPC"],
                dates="2023",
                bullets=["Implemented Raft consensus algorithm handling 10,000 req/sec."],
            ),
            ProjectEntity(
                id="proj-2",
                title="ML Vision Classifier",
                technologies=["PyTorch", "OpenCV"],
                dates="2022",
                bullets=["Trained CNN model achieving 94.5% accuracy on CIFAR-10."],
            ),
        ]
        edus = [
            EducationEntity(
                id="edu-1",
                institution="UC Berkeley",
                degree="B.S. in Computer Science",
                dates="2020 - 2024",
                gpa="3.9",
            )
        ]
        certs = ["AWS Certified Cloud Practitioner"]
        achs = ["Dean's Honors List 2021-2023"]
        pubs = []
        res = []
        additional = []
        skills = ["Python", "Go", "PyTorch", "Docker", "gRPC", "Git", "PostgreSQL"]

    elif is_academic:
        exps = [
            WorkExperienceEntity(
                id="exp-1",
                company="Stanford AI Lab",
                role="Postdoctoral Researcher",
                dates="2022 - Present",
                bullets=["Led multimodal foundation model alignment research with 4 junior PhD students."],
            ),
            WorkExperienceEntity(
                id="exp-2",
                company="MIT CSAIL",
                role="Graduate Research Assistant",
                dates="2018 - 2022",
                bullets=["Developed sparse attention mechanism accelerating inference by 2.4x on NVIDIA A100 GPUs."],
            ),
        ]
        projs = [
            ProjectEntity(
                id="proj-1",
                title="OpenBioMed LLM",
                technologies=["PyTorch", "DeepSpeed", "CUDA"],
                dates="2023",
                bullets=["Trained 13B parameter biomedical language model benchmarked on PubMedQA."],
            )
        ]
        edus = [
            EducationEntity(
                id="edu-1",
                institution="MIT",
                degree="Ph.D. in Electrical Engineering and Computer Science",
                dates="2018 - 2022",
                gpa="4.0",
            ),
            EducationEntity(
                id="edu-2",
                institution="Stanford University",
                degree="B.S. in Computer Science & Mathematics",
                dates="2014 - 2018",
                gpa="3.95",
            ),
        ]
        certs = []
        achs = ["NeurIPS 2022 Outstanding Paper Award"]
        pubs = [
            "Morgan, A., et al. (2023). Scalable Sparse Attention in Transformer Models. NeurIPS.",
            "Morgan, A., et al. (2021). Efficient Multimodal Pretraining. ICML.",
        ]
        res = ["NSF Graduate Research Fellowship ($150,000)", "Reviewer for NeurIPS, ICML, ICLR."]
        additional = []
        skills = ["PyTorch", "Distributed Training", "CUDA", "Transformers", "Python", "DeepSpeed", "C++"]

    elif has_progression:
        exps = [
            WorkExperienceEntity(
                id="exp-1",
                company="Stripe Inc.",
                role="Lead Software Engineer",
                dates="2019 - Present",
                location="San Francisco, CA",
                progression=[
                    RoleProgression(
                        id="prog-1",
                        title="Staff Software Engineer",
                        dates="2023 - Present",
                        bullets=["Architected global settlement engine handling $12B in daily volume with 99.999% uptime."],
                    ),
                    RoleProgression(
                        id="prog-2",
                        title="Senior Software Engineer",
                        dates="2021 - 2023",
                        bullets=["Reduced payment checkout latency by 45ms across 14 geographical regions."],
                    ),
                    RoleProgression(
                        id="prog-3",
                        title="Software Engineer II",
                        dates="2019 - 2021",
                        bullets=["Implemented webhook retry queue using Kafka and Redis processing 2M events/day."],
                    ),
                ],
            ),
            WorkExperienceEntity(
                id="exp-2",
                company="Airbnb",
                role="Software Engineer",
                dates="2017 - 2019",
                location="San Francisco, CA",
                bullets=["Built automated host verification pipeline reducing onboarding time by 30%."],
            ),
        ]
        projs = [
            ProjectEntity(
                id="proj-1",
                title="Distributed Transaction Coordinator",
                technologies=["Go", "Raft", "PostgreSQL"],
                dates="2022",
                bullets=["Open-source 2PC coordinator with over 1,500 GitHub stars."],
            )
        ]
        edus = [
            EducationEntity(
                id="edu-1",
                institution="Carnegie Mellon University",
                degree="B.S. in Computer Science",
                dates="2013 - 2017",
            )
        ]
        certs = ["AWS Certified Solutions Architect - Professional"]
        achs = []
        pubs = []
        res = []
        additional = []
        skills = ["Distributed Systems", "Go", "Java", "Kafka", "PostgreSQL", "AWS", "Kubernetes", "Redis"]

    else:
        # Standard professional
        exps = [
            WorkExperienceEntity(
                id="exp-1",
                company="CloudScale Solutions",
                role="Senior Full Stack Engineer",
                dates="2021 - Present",
                location="Seattle, WA",
                bullets=[
                    "Designed scalable microservices architecture serving 5M daily active users.",
                    "Improved API response times by 40% through Redis caching and query optimization.",
                    "Mentored 6 junior engineers and standardized CI/CD deployment pipelines using GitHub Actions.",
                ],
            ),
            WorkExperienceEntity(
                id="exp-2",
                company="Nexus Tech",
                role="Full Stack Engineer",
                dates="2019 - 2021",
                location="Seattle, WA",
                bullets=[
                    "Developed React dashboards with TypeScript and integrated GraphQL APIs.",
                    "Optimized PostgreSQL database schemas reducing query execution time by 25%.",
                ],
            ),
        ]
        projs = [
            ProjectEntity(
                id="proj-1",
                title="Real-Time Analytics Platform",
                technologies=["React", "TypeScript", "Node.js", "Redis"],
                dates="2022",
                bullets=["Built WebSocket-powered analytics dashboard rendering 5,000 datapoints/sec without UI lag."],
            )
        ]
        edus = [
            EducationEntity(
                id="edu-1",
                institution="University of Washington",
                degree="B.S. in Informatics",
                dates="2015 - 2019",
            )
        ]
        certs = ["AWS Certified Developer - Associate"]
        achs = ["Hackathon 1st Place Winner (2020)"]
        pubs = []
        res = []
        additional = []
        skills = ["React", "TypeScript", "Node.js", "PostgreSQL", "Redis", "Docker", "AWS", "GraphQL"]

    # Synthesize evidence units
    ev_units = []
    for exp in exps:
        if exp.progression:
            for p in exp.progression:
                for b in p.bullets:
                    ev_units.append(EvidenceUnit(
                        id=f"EXP_{exp.company}_{p.title}_{len(ev_units)}",
                        section="EXPERIENCE",
                        entity_id=exp.id,
                        original_text=b,
                        normalized_text=b,
                        claim_type=ClaimType.DELIVERY,
                        metrics=["$12B", "99.999%", "45ms", "2M", "30%"],
                    ))
        else:
            for b in exp.bullets:
                ev_units.append(EvidenceUnit(
                    id=f"EXP_{exp.company}_{len(ev_units)}",
                    section="EXPERIENCE",
                    entity_id=exp.id,
                    original_text=b,
                    normalized_text=b,
                    claim_type=ClaimType.DELIVERY,
                ))
    for p in projs:
        for b in p.bullets:
            ev_units.append(EvidenceUnit(
                id=f"PROJ_{p.title}_{len(ev_units)}",
                section="PROJECTS",
                entity_id=p.id,
                original_text=b,
                normalized_text=b,
                claim_type=ClaimType.DELIVERY,
            ))

    profile = CandidateProfile(
        personal=personal,
        summary="Results-driven software engineering leader with extensive experience delivering high-scale systems.",
        experience=exps,
        projects=projs,
        education=edus,
        certifications=certs,
        achievements=achs,
        publications=pubs,
        research=res,
        additional_sections=additional,
        skills=skills,
        evidence_units=ev_units,
    )

    try:
        c_class = CareerClassification(career_stage)
    except Exception:
        c_class = CareerClassification.PROFESSIONAL

    analysis = CareerClassificationResult(
        classification=c_class,
        years_of_experience=years_exp,
        suggested_focus="Backend Systems & Distributed Architecture",
        detected_gaps=[],
        confidence=0.95,
    )

    return profile, analysis


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_sparse_fresher_template_and_rendering():
    """1. Sparse fresher gets ATS_FRESHER, 1-page budget, education before experience."""
    profile, analysis = _make_sample_candidate(is_fresher=True, career_stage="FRESHER", years_exp=0.5)
    jd = JDRequirements(
        raw_text="Junior Software Engineer with Python and Go",
        role_category="Software Engineering",
        core_skills=["Python", "Go", "Docker"],
        required_hard_skills=["Python", "Go"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    assert strategy.template_family == TemplateFamily.ATS_FRESHER
    assert strategy.page_budget == 1
    assert "education" in strategy.section_order
    # In fresher, education appears before experience
    assert strategy.section_order.index("education") < strategy.section_order.index("experience")

    # Render PDF & DOCX
    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="standard")
    assert len(pdf_bytes) > 2000
    page_count = measure_pdf_page_count(pdf_bytes)
    assert page_count == 1, f"Expected 1 page for sparse fresher, got {page_count}"

    docx_bytes = generate_docx(profile_dict, template="standard")
    assert len(docx_bytes) > 2000


def test_02_dense_fresher_compact_variant():
    """2. Dense fresher uses compact variant for tight 1-page fit."""
    profile, analysis = _make_sample_candidate(is_fresher=True, career_stage="FRESHER", years_exp=1.0)
    jd = JDRequirements(
        raw_text="Software Engineer Intern with Python, PyTorch, Go",
        role_category="Software Engineering",
        core_skills=["Python", "PyTorch", "Go"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)
    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="compact")
    assert len(pdf_bytes) > 2000
    page_count = measure_pdf_page_count(pdf_bytes)
    assert page_count == 1


def test_03_experienced_one_page():
    """3. Experienced professional with moderate density gets 1-page ATS_PROFESSIONAL."""
    profile, analysis = _make_sample_candidate(career_stage="PROFESSIONAL", years_exp=3.5)
    jd = JDRequirements(
        raw_text="Full Stack Engineer with React, TypeScript, Node.js, PostgreSQL",
        role_category="Software Engineering",
        core_skills=["React", "TypeScript", "Node.js", "PostgreSQL"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    assert strategy.template_family == TemplateFamily.ATS_PROFESSIONAL
    assert strategy.page_budget == 1
    assert strategy.section_order.index("experience") < strategy.section_order.index("education")

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="standard")
    page_count = measure_pdf_page_count(pdf_bytes)
    assert page_count == 1


def test_04_experienced_two_page():
    """4. Experienced professional with heavy history gets 2-page ATS_PROFESSIONAL."""
    profile, analysis = _make_sample_candidate(career_stage="PROFESSIONAL", years_exp=8.0)
    jd = JDRequirements(
        raw_text="Staff Full Stack Engineer with React, TypeScript, Node.js, AWS, Redis",
        role_category="Software Engineering",
        core_skills=["React", "TypeScript", "Node.js", "AWS", "Redis"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    assert strategy.template_family == TemplateFamily.ATS_PROFESSIONAL
    assert strategy.page_budget == 2


def test_05_senior_two_page_executive():
    """5. Senior candidate gets ATS_SENIOR template with classic/executive presentation."""
    profile, analysis = _make_sample_candidate(career_stage="SENIOR_PROFESSIONAL", years_exp=10.0, has_progression=True)
    jd = JDRequirements(
        raw_text="Principal Engineer / Tech Lead with Distributed Systems, Go, Kafka, PostgreSQL",
        role_category="Software Engineering",
        core_skills=["Distributed Systems", "Go", "Kafka", "PostgreSQL"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    assert strategy.template_family == TemplateFamily.ATS_SENIOR
    assert strategy.page_budget == 2
    assert "experience" in strategy.section_order

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="classic")
    assert len(pdf_bytes) > 2000


def test_06_academic_and_research_strategy_and_rendering():
    """6. Academic candidate strategy prioritizes education, publications, and research."""
    profile, analysis = _make_sample_candidate(career_stage="RESEARCH", years_exp=6.0, is_academic=True)
    jd = JDRequirements(
        raw_text="Research Scientist - Foundation Models with PyTorch, Distributed Training, CUDA",
        role_category="Machine Learning",
        core_skills=["PyTorch", "Distributed Training", "CUDA"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    assert strategy.career_stage == CareerStage.RESEARCH
    assert "education" in strategy.section_order
    assert "publications" in strategy.section_order
    # In academic strategy, education and publications are front-loaded
    assert strategy.section_order.index("education") < strategy.section_order.index("experience")
    assert strategy.section_order.index("publications") < strategy.section_order.index("experience")

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="standard")
    is_valid, errors = verify_ats_pdf_parseability(pdf_bytes, profile)
    assert is_valid, f"Academic PDF parseability failed: {errors}"


def test_07_multi_role_company_progression_rendering():
    """7. Multi-role progression under a single company renders hierarchically without duplicating company."""
    profile, analysis = _make_sample_candidate(career_stage="SENIOR_PROFESSIONAL", years_exp=7.0, has_progression=True)
    jd = JDRequirements(
        raw_text="Staff Engineer with Distributed Systems, Go, Kafka",
        role_category="Software Engineering",
        core_skills=["Distributed Systems", "Go", "Kafka"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="standard")
    is_valid, errors = verify_ats_pdf_parseability(pdf_bytes, profile)
    assert is_valid, f"Progression PDF parseability failed: {errors}"

    # Extract text and verify role progression
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)
    doc.close()

    assert "Stripe Inc." in full_text
    assert "Staff Software Engineer" in full_text
    assert "Senior Software Engineer" in full_text
    assert "Software Engineer II" in full_text
    assert "$12B" in full_text
    assert "45ms" in full_text
    assert "2M" in full_text


def test_08_project_heavy_candidate_rendering():
    """8. Project-heavy candidate renders Technologies line distinctly from evidence bullets."""
    profile, analysis = _make_sample_candidate(is_fresher=True, career_stage="FRESHER")
    jd = JDRequirements(
        raw_text="Junior Backend Developer with Go, Raft, Python",
        role_category="Software Engineering",
        core_skills=["Go", "Raft", "Python"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="standard")

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)
    doc.close()

    assert "Distributed Key-Value Store" in full_text
    assert "Technologies: Go, Raft, gRPC" in full_text
    assert "Raft consensus algorithm" in full_text


def test_09_certification_heavy_candidate():
    """9. Certifications are rendered cleanly with standard bullet hierarchy."""
    profile, analysis = _make_sample_candidate(career_stage="PROFESSIONAL")
    profile.certifications.extend([
        "Certified Kubernetes Administrator (CKA)",
        "HashiCorp Certified: Terraform Associate",
    ])
    jd = JDRequirements(
        raw_text="DevOps Engineer with AWS, Kubernetes, Terraform",
        role_category="DevOps",
        core_skills=["AWS", "Kubernetes", "Terraform"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="standard")
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)
    doc.close()

    assert "CERTIFICATIONS" in full_text
    assert "AWS Certified Developer - Associate" in full_text
    assert "Certified Kubernetes Administrator (CKA)" in full_text


def test_10_career_switcher_priority():
    """10. Career switcher prioritizes transferable skills and relevant projects over history."""
    profile, analysis = _make_sample_candidate(career_stage="CAREER_SWITCHER", years_exp=5.0)
    jd = JDRequirements(
        raw_text="Software Engineer with React, TypeScript, Node.js",
        role_category="Software Engineering",
        core_skills=["React", "TypeScript", "Node.js"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    assert strategy.career_stage == CareerStage.CAREER_SWITCHER
    assert strategy.section_order.index("skills") < strategy.section_order.index("experience")
    assert strategy.section_order.index("projects") < strategy.section_order.index("experience")


def test_11_property_invariants_rendering_never_alters_meaning():
    """11. Asserts strict property invariants: metrics, dates, and evidence are never altered."""
    profile, analysis = _make_sample_candidate(career_stage="PROFESSIONAL", has_progression=True)
    jd = JDRequirements(
        raw_text="Senior Backend Engineer with Go, PostgreSQL, Kafka",
        role_category="Software Engineering",
        core_skills=["Go", "PostgreSQL", "Kafka"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    pdf_bytes = generate_pdf(profile_dict, template="standard")
    is_valid, errors = verify_ats_pdf_parseability(pdf_bytes, profile)
    assert is_valid, f"Property invariant violation: {errors}"


def test_12_end_to_end_pdf_parseability_verification():
    """12. Comprehensive parseability check extracts text and verifies all facts."""
    profile, analysis = _make_sample_candidate(career_stage="SENIOR_PROFESSIONAL", years_exp=8.0, has_progression=True)
    jd = JDRequirements(
        raw_text="Staff Software Engineer with Go, PostgreSQL, Kafka, AWS",
        role_category="Software Engineering",
        core_skills=["Go", "PostgreSQL", "Kafka", "AWS"],
    )
    strategy = build_resume_strategy(profile, analysis, jd)

    profile_dict = profile.to_parsed_dict()
    profile_dict["_strategy"] = strategy.model_dump()

    for variant in ["standard", "classic", "compact"]:
        pdf_bytes = generate_pdf(profile_dict, template=variant)
        is_valid, errors = verify_ats_pdf_parseability(pdf_bytes, profile)
        assert is_valid, f"Variant '{variant}' failed ATS parseability check: {errors}"
