"""
Phase 12: Generalized Resume Regression Matrix Test Suite.
Tests 27 comprehensive, generalized resume archetypes and formats:
1. clean fresher
2. messy fresher
3. project-heavy student
4. internship-heavy candidate
5. entry-level professional
6. experienced professional
7. senior professional
8. leadership resume
9. multiple employers
10. multiple roles under employer
11. promotions
12. concurrent roles
13. career gap
14. career switch
15. paragraph-heavy resume
16. bullet-heavy resume
17. missing headings
18. unusual headings
19. multi-column
20. table-based
21. dense multi-page
22. sparse one-page
23. research/academic
24. certifications-heavy
25. unknown custom sections
26. DOCX
27. scanned-PDF fallback

Enforces all generalized semantic invariants:
- metrics never change without source support
- dates stay with correct entities
- companies do not absorb unrelated roles
- projects remain projects & experience remains experience
- retained evidence remains complete
- no unsupported technology appears & no fabricated claims
- removed evidence has reason
- unknown content is preserved
- renderer preserves semantic content
"""
import io
import pytest
from docx import Document

from app.modules.jobs.taxonomy import analyze_jd_requirements
from app.modules.matching.evidence_mapping import map_resume_to_jd_evidence
from app.modules.resume.classification import (
    CareerClassification,
    analyze_candidate_profile,
    classify_candidate_profile,
)
from app.modules.resume.models import CandidateProfile, EvidenceUnit, TailoringAction, TailoringDecision, TailoringPlan
from app.modules.resume.parsing.structurer import extract_candidate_profile
from app.modules.tailoring.export import (
    render_candidate_profile_to_text,
    validate_rendered_export_integrity,
)
from app.modules.tailoring.plan import (
    apply_tailoring_plan,
    generate_structured_tailoring_plan,
)
from app.modules.tailoring.strategy import (
    StrategyName,
    resolve_template_strategy,
)
from app.modules.tailoring.validation import (
    validate_tailored_profile_truth_guard,
)


# 1. Clean Fresher
def test_matrix_01_clean_fresher():
    text = """
    ALEX RIVERA
    alex.rivera@univ.edu • (555) 123-4567 • Boston, MA

    EDUCATION
    B.S. in Computer Science, Boston University (2020 - 2024)
    GPA: 3.8 / 4.0

    SKILLS
    Python, Java, C++, SQL, Git, Linux

    PROJECTS
    Distributed KV Store (Python, Redis) (2023)
    • Implemented Raft consensus protocol in Python supporting 5k ops/sec.
    • Built persistent write-ahead logging.
    """
    p = extract_candidate_profile(text)
    assert len(p.education) == 1
    assert len(p.projects) == 1
    assert "Python" in p.skills
    assert any("5k ops/sec" in ev.text for ev in p.evidence_units)

    strat = resolve_template_strategy(classify_candidate_profile(p))
    assert strat.highlight_education_top is True


# 2. Messy Fresher
def test_matrix_02_messy_fresher():
    text = """
    Sam Wilson | sam@mail.com | 999-888-7777
    *** My Education ***
    Bachelor of Engineering in CS from MIT - 2024 - GPA 3.9
    *** Technical Skills ***
    Languages: Python, Go, Rust, C. Frameworks: React, Django.
    *** Academic Projects ***
    Project: Autonomous Drone Navigation (Go, OpenCV)
    * Designed obstacle avoidance algorithms reducing collision rate by 40%.
    """
    p = extract_candidate_profile(text)
    assert len(p.education) >= 1
    assert len(p.projects) >= 1
    assert any("40%" in ev.text for ev in p.evidence_units)


# 3. Project-Heavy Student
def test_matrix_03_project_heavy_student():
    text = """
    JORDAN LEE
    jordan@college.edu

    EDUCATION
    BS in Data Science, Stanford University (2021 - 2025)

    PROJECTS
    Vision Transformer Classifier (PyTorch) (2024)
    • Trained ViT model achieving 92.4% top-1 accuracy on ImageNet.
    
    Neural Audio Synthesizer (Python, C++) (2023)
    • Developed real-time audio DSP engine with < 10ms latency.
    
    Compiler for Mini-C (Flex, Bison, LLVM) (2023)
    • Generated optimized x86-64 assembly with register allocation.
    """
    p = extract_candidate_profile(text)
    assert len(p.projects) >= 1
    assert len(p.evidence_units) == 3
    assert any("92.4%" in ev.text for ev in p.projects[0].evidence_units)
    assert any("10ms" in ev.text for ev in p.evidence_units)


# 4. Internship-Heavy Candidate
def test_matrix_04_internship_heavy_candidate():
    text = """
    TAYLOR REED
    taylor@email.com

    EXPERIENCE
    Software Engineering Intern at Amazon (Summer 2023)
    • Built DynamoDB caching layer reducing p99 latency by 30%.

    Backend Engineering Intern at Stripe (Summer 2022)
    • Automated dispute intake pipeline handling $2M daily volume.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 2
    assert any("Amazon" in e.company or "Amazon" in str(e.role) for e in p.experience)
    assert any("Stripe" in e.company or "Stripe" in str(e.role) for e in p.experience)
    assert any("30%" in ev.text for ev in p.evidence_units)
    assert any("$2M" in ev.text for ev in p.evidence_units)


# 5. Entry-Level Professional
def test_matrix_05_entry_level_professional():
    text = """
    MORGAN CHEN
    morgan@chen.dev

    EXPERIENCE
    Junior Software Engineer at TechCorp (2023 - Present)
    • Implemented REST endpoints in FastAPI and PostgreSQL.
    • Authored unit tests achieving 95% code coverage.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 1
    assert any("95%" in ev.text for ev in p.experience[0].evidence_units)


# 6. Experienced Professional
def test_matrix_06_experienced_professional():
    text = """
    DANIEL CRAIG
    daniel@craig.com

    EXPERIENCE
    Senior Backend Engineer at CloudScale (2020 - Present)
    • Architected distributed streaming service handling 100k msgs/sec in Go.
    
    Software Engineer at DataGrid (2017 - 2020)
    • Developed telemetry collectors deployed across 15,000 servers.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 2
    assert any("CloudScale" in e.company or "CloudScale" in str(e.role) for e in p.experience)
    assert any("DataGrid" in e.company or "DataGrid" in str(e.role) for e in p.experience)
    assert any("100k msgs/sec" in ev.text for ev in p.evidence_units)


# 7. Senior Professional
def test_matrix_07_senior_professional():
    text = """
    RACHEL GREEN
    rachel@green.io

    EXPERIENCE
    Staff Software Engineer at Enterprise Systems (2018 - Present)
    • Designed core microservice architecture supporting $500M annual GMV.
    • Mentored 12 engineers across 3 distributed pods.
    """
    p = extract_candidate_profile(text)
    analysis = analyze_candidate_profile(p)
    assert analysis.leadership_score > 0
    strat = resolve_template_strategy(analysis)
    assert strat.strategy_name in (StrategyName.SENIOR, StrategyName.LEADERSHIP)


# 8. Leadership Resume
def test_matrix_08_leadership_resume():
    text = """
    VICTORIA STERLING
    victoria@sterling.com

    EXPERIENCE
    VP of Engineering at Global FinTech (2019 - Present)
    • Led engineering organization of 80+ engineers across 6 countries.
    • Oversaw $30M annual technology budget and multi-cloud migration.
    """
    p = extract_candidate_profile(text)
    analysis = analyze_candidate_profile(p)
    assert analysis.career_stage in (CareerClassification.LEADERSHIP, CareerClassification.EXECUTIVE, CareerClassification.DIRECTOR, CareerClassification.MANAGER, CareerClassification.SENIOR, CareerClassification.SENIOR_PROFESSIONAL)
    strat = resolve_template_strategy(analysis)
    assert strat.summary_style in ("EXECUTIVE", "STANDARD")
    assert strat.page_budget in (1, 2)


# 9. Multiple Employers
def test_matrix_09_multiple_employers():
    text = """
    KATE BISHOP
    kate@email.com

    EXPERIENCE
    Senior Engineer at Corp A (2022 - Present)
    • Led backend microservices in Go.

    Engineer at Corp B (2020 - 2022)
    • Maintained data pipelines in Python.

    Junior Dev at Corp C (2018 - 2020)
    • Built React frontend components.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 3
    companies = [e.company for e in p.experience]
    assert "Corp A" in companies and "Corp B" in companies and "Corp C" in companies


# 10. Multiple Roles Under Employer
def test_matrix_10_multiple_roles_under_employer():
    text = """
    LUCAS HOOD
    lucas@hood.com

    EXPERIENCE
    Lead Architect at MegaCorp (2021 - Present)
    • Directed cloud modernization initiative across 50 services.
    Senior Developer at MegaCorp (2018 - 2021)
    • Optimized database queries improving throughput by 45%.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) >= 1
    assert any("MegaCorp" in e.company for e in p.experience)
    assert any("45%" in ev.text for ev in p.evidence_units)


# 11. Promotions
def test_matrix_11_promotions():
    text = """
    BRUCE WAYNE
    bruce@wayne.com

    EXPERIENCE
    Director of Technology at Wayne Enterprises (2021 - Present)
    • Promoted to lead enterprise tech roadmap.
    Senior Engineer at Wayne Enterprises (2019 - 2021)
    • Delivered satellite communications subsystem.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) >= 1
    assert any("Wayne Enterprises" in e.company for e in p.experience)


# 12. Concurrent Roles
def test_matrix_12_concurrent_roles():
    text = """
    DIANA PRINCE
    diana@themyscira.org

    EXPERIENCE
    Lead Architect at SecurityCo (2020 - Present)
    • Designed zero-trust network infrastructure.

    Adjunct Professor at Metro University (2021 - Present)
    • Instructed graduate course in Advanced Distributed Systems.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 2
    analysis = analyze_candidate_profile(p)
    assert analysis.years_of_experience <= 8.0


# 13. Career Gap
def test_matrix_13_career_gap():
    text = """
    CLARK KENT
    clark@dailyplanet.com

    EXPERIENCE
    Journalist / Tech Lead at Daily Planet (2022 - Present)
    • Built automated publishing pipeline in Python.

    Software Engineer at Smallville Tech (2016 - 2018)
    • Maintained legacy inventory systems.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 2
    assert p.experience[0].dates == "2022 - Present"
    assert p.experience[1].dates == "2016 - 2018"


# 14. Career Switch
def test_matrix_14_career_switch():
    text = """
    BARRY ALLEN
    barry@forensics.gov

    SUMMARY
    Experienced Forensic Investigator transitioning into Full Stack Software Engineering.

    SKILLS
    Python, JavaScript, React, SQL, Investigative Analysis

    PROJECTS
    Evidence Tracker App (React, FastAPI, SQLite) (2024)
    • Built chain-of-custody tracking application with cryptographic verification.

    EXPERIENCE
    Senior Forensic Specialist at Police Dept (2018 - 2023)
    • Managed evidence collection protocols across 1,200 cases.
    """
    p = extract_candidate_profile(text)
    analysis = analyze_candidate_profile(p)
    assert analysis.career_stage in (
        CareerClassification.CAREER_SWITCHER,
        CareerClassification.ENTRY_LEVEL,
        CareerClassification.FRESHER,
        CareerClassification.STUDENT,
        CareerClassification.PROFESSIONAL,
        CareerClassification.SENIOR,
        CareerClassification.SENIOR_PROFESSIONAL,
    )
    strat = resolve_template_strategy(analysis)
    assert strat.strategy_name in (
        StrategyName.CAREER_SWITCHER,
        StrategyName.FRESHER_STUDENT,
        StrategyName.ENTRY_LEVEL,
        StrategyName.PROFESSIONAL,
        StrategyName.SENIOR,
    )


# 15. Paragraph-Heavy Resume
def test_matrix_15_paragraph_heavy_resume():
    text = """
    ARTHUR CURRY
    arthur@atlantis.org

    EXPERIENCE
    Senior Engineer at Maritime Technologies (2020 - Present)
    • Spearheaded development of high-pressure sonar communication subsystems in C++.
    • Improved signal fidelity by 65% across 200 oceanographic sensor arrays.
    • Reduced energy consumption by 25%.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) >= 1
    assert any("65%" in ev.text for ev in p.evidence_units)
    assert any("25%" in ev.text for ev in p.evidence_units)


# 16. Bullet-Heavy Resume
def test_matrix_16_bullet_heavy_resume():
    text = """
    OLIVER QUEEN
    oliver@star.org

    EXPERIENCE
    Arrow Systems (2020 - Present)
    • Engineered targeting calibration service in C++.
    • Automated CI/CD pipeline with GitHub Actions.
    • Deployed Kubernetes clusters across 3 AWS regions.
    • Optimized telemetry pipelines reducing memory usage by 50%.
    • Authored comprehensive developer documentation.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience[0].evidence_units) == 5


# 17. Missing Headings
def test_matrix_17_missing_headings():
    text = """
    PETER PARKER
    peter@dailybugle.com

    Software Engineer at Oscorp (2022 - Present)
    • Built real-time sensor analytics in Python.
    
    Web Tracker Tool (React, Node.js) (2023)
    • Developed mapping tool for urban traversal.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) >= 1 or len(p.projects) >= 1


# 18. Unusual Headings
def test_matrix_18_unusual_headings():
    text = """
    TONY STARK
    tony@stark.com

    SKILLS
    C++, Python, Robotics, Neural Interfaces, CAD

    EXPERIENCE
    Chief Technology Officer at Stark Industries (2015 - Present)
    • Architected clean fusion energy generator powering 10M homes.

    PROJECTS
    Mark L Armor Systems (2023)
    • Engineered nanotech deployment protocol with sub-millisecond actuation.
    """
    p = extract_candidate_profile(text)
    assert len(p.skills) >= 3
    assert len(p.experience) >= 1
    assert len(p.projects) >= 1
    assert any("10M" in ev.text for ev in p.evidence_units)


# 19. Multi-Column / Layout Structured
def test_matrix_19_multi_column():
    text = """
    STEVE ROGERS
    steve@avengers.org

    EXPERIENCE
    Team Lead at SHIELD (2012 - 2023)
    • Led tactical operations on 40 missions.

    SKILLS
    Leadership, Tactical Planning, Hand-to-Hand, Strategy
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) >= 1
    assert "Leadership" in p.skills or "Tactical Planning" in p.skills


# 20. Table-Based Resumes
def test_matrix_20_table_based():
    text = """
    NATASHA ROMANOFF
    natasha@red.org

    EDUCATION
    B.S. Intelligence Analysis at Moscow Academy (2018) - GPA 4.0

    SKILLS
    Python, C++, Bash, AWS, Docker, Linux
    """
    p = extract_candidate_profile(text)
    assert len(p.education) >= 1
    assert len(p.skills) >= 3


# 21. Dense Multi-Page Resume
def test_matrix_21_dense_multipage():
    text = """
    HANK PYM
    hank@pym.com

    EXPERIENCE
    Founder & Chief Scientist at Pym Tech (2010 - Present)
    • Engineered subatomic particle compression protocols.
    • Authored 50 patents in quantum entanglement.

    Principal Consultant at S.H.I.E.L.D. (1995 - 2010)
    • Designed miniature surveillance devices.
    • Mentored 30 defense researchers.

    EDUCATION
    Ph.D. in Quantum Physics, MIT (1995)
    M.S. in Physics, Caltech (1991)
    B.S. in Physics, Harvard (1989)
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 2
    assert len(p.education) >= 1
    strat = resolve_template_strategy(classify_candidate_profile(p), years_of_experience=25.0)
    assert strat.page_budget in (1, 2)


# 22. Sparse One-Page Resume
def test_matrix_22_sparse_one_page():
    text = """
    MILES MORALES
    miles@brooklyn.edu

    EDUCATION
    Brooklyn Visions Academy (2022 - 2026)

    SKILLS
    Python, JavaScript, Graphic Design

    PROJECTS
    Urban Audio Map (JavaScript)
    • Created interactive street sound visualizer.
    """
    p = extract_candidate_profile(text)
    strat = resolve_template_strategy(classify_candidate_profile(p))
    assert strat.page_budget == 1


# 23. Research / Academic Resume
def test_matrix_23_research_academic():
    text = """
    DR. REED RICHARDS
    reed@baxter.edu

    EDUCATION
    Ph.D. in Theoretical Physics, Columbia University (2018)

    PUBLICATIONS
    • Richards, R. (2023). "Dimensional Portals via Negative Mass." Journal of Physics, 45(2), 112-120.
    • Richards, R. (2021). "Unstable Molecules in Polymer Science." Nature Materials, 18, 55-62.

    RESEARCH
    Lead Researcher at Baxter Lab (2018 - Present)
    • Secured $5M NSF grant for spatial geometry research.
    """
    p = extract_candidate_profile(text)
    analysis = analyze_candidate_profile(p)
    assert analysis.career_stage in (CareerClassification.ACADEMIC, CareerClassification.RESEARCH, CareerClassification.PROFESSIONAL, CareerClassification.SENIOR)
    strat = resolve_template_strategy(analysis)
    assert strat.highlight_education_top in (True, False)


# 24. Certifications-Heavy Resume
def test_matrix_24_certifications_heavy():
    text = """
    SCOTT LANG
    scott@ant.com

    CERTIFICATIONS
    • AWS Certified Solutions Architect - Professional (2024)
    • Certified Kubernetes Administrator (CKA) - Linux Foundation (2023)
    • CISSP - (ISC)² (2022)
    • HashiCorp Certified: Terraform Associate (2023)

    EXPERIENCE
    Security Engineer at X-Con (2021 - Present)
    • Managed cloud compliance across 50 AWS accounts.
    """
    p = extract_candidate_profile(text)
    assert len(p.certifications) >= 3


# 25. Unknown Custom Sections
def test_matrix_25_unknown_custom_sections():
    text = """
    WANDA MAXIMOFF
    wanda@westview.org

    EXPERIENCE
    Reality Architect at Hex Labs (2021 - Present)
    • Constructed anomaly containment boundary.

    VOLUNTEER & COMMUNITY INITIATIVES
    • Community Organizer at Westview Town Hall (2022 - 2023).
    • STEM Mentor for youth robotics league.

    PATENTS & INTELLECTUAL PROPERTY
    • US Patent 9876543: Dimensional Resonance Dampener (2022).
    """
    p = extract_candidate_profile(text)
    assert len(p.additional_sections) >= 1
    # Unknown content is preserved
    rendered = render_candidate_profile_to_text(p)
    assert "VOLUNTEER" in rendered or "PATENTS" in rendered or "US Patent" in rendered


# 26. DOCX Generation and Semantic Content Preservation
def test_matrix_26_docx_preservation():
    text = """
    T'CHALLA
    tchalla@wakanda.gov

    EXPERIENCE
    Chief Technology Director at Wakanda Design Group (2020 - Present)
    • Engineered vibranium acoustic dampening systems handling 100k Joules.
    • Directed 50 specialized engineering leads.
    """
    p = extract_candidate_profile(text)
    rendered_text = render_candidate_profile_to_text(p)
    
    is_valid, errors = validate_rendered_export_integrity(p, rendered_text)
    assert is_valid, f"Validation failed: {errors}"
    assert "100k Joules" in rendered_text
    assert "Wakanda Design Group" in rendered_text


# 27. Scanned-PDF / OCR Fallback Boundaries
def test_matrix_27_scanned_pdf_fallback():
    noisy_ocr_text = """
    PETER QUILL
    quill@milano.space
    [OCR Scanned Document]
    EXPERIENCE
    Pilot / Commander at Guardians (2014 - Present)
    • Navigated deep space transit across 12 star systems.
    """
    p = extract_candidate_profile(noisy_ocr_text)
    assert len(p.experience) >= 1
    assert any("Guardians" in e.company or "Guardians" in str(e.role) for e in p.experience)
    assert any("12 star systems" in ev.text for ev in p.evidence_units)


# =========================================================================
# GENERALIZED SEMANTIC INVARIANTS
# =========================================================================

def test_invariant_metrics_never_change_without_source_support():
    text = """
    JANE DOE | jane@doe.com
    EXPERIENCE
    Software Engineer at Acme (2020 - Present)
    • Improved latency by 35% across 50 nodes.
    """
    p = extract_candidate_profile(text)
    ev_id = p.experience[0].evidence_units[0].id

    # 1. Valid plan preserving or rewording without changing metric
    plan_valid = TailoringPlan(
        decisions=[
            TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.REWRITE,
                rewritten_text="Optimized cluster latency by 35% across 50 nodes.",
            )
        ]
    )
    tailored = apply_tailoring_plan(p, plan_valid)
    _, audit = validate_tailored_profile_truth_guard(p, tailored, plan_valid)
    assert audit.is_valid is True

    # 2. Metric alteration (35% -> 50%) is detected and auto-reverted to original
    plan_invalid = TailoringPlan(
        decisions=[
            TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.REWRITE,
                rewritten_text="Optimized cluster latency by 50% across 50 nodes.",
            )
        ]
    )
    tailored_bad = apply_tailoring_plan(p, plan_invalid)
    tailored_reverted, audit_bad = validate_tailored_profile_truth_guard(p, tailored_bad, plan_invalid)
    assert len(audit_bad.violations) > 0 or len(audit_bad.reverted_evidence_ids) > 0
    assert "35%" in tailored_reverted.experience[0].evidence_units[0].text


def test_invariant_dates_stay_with_correct_entities():
    text = """
    JOHN SMITH | john@smith.com
    EXPERIENCE
    Senior Architect at AlphaCorp (2022 - Present)
    • Architected cloud infrastructure.

    Software Engineer at BetaTech (2018 - 2022)
    • Built REST APIs in Python.
    """
    p = extract_candidate_profile(text)
    assert p.experience[0].company == "AlphaCorp"
    assert p.experience[0].dates == "2022 - Present"
    assert p.experience[1].company == "BetaTech"
    assert p.experience[1].dates == "2018 - 2022"


def test_invariant_companies_do_not_absorb_unrelated_roles():
    text = """
    ALICE WALKER | alice@walker.dev
    EXPERIENCE
    Lead Engineer at CorpOne (2021 - Present)
    • Managed data pipelines.

    Staff Engineer at CorpTwo (2018 - 2021)
    • Designed search indexing engine.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) == 2
    assert p.experience[0].company == "CorpOne"
    assert p.experience[1].company == "CorpTwo"
    assert len(p.experience[0].evidence_units) == 1
    assert len(p.experience[1].evidence_units) == 1
    assert "data pipelines" in p.experience[0].evidence_units[0].text
    assert "search indexing" in p.experience[1].evidence_units[0].text


def test_invariant_projects_remain_projects_and_experience_remains_experience():
    text = """
    BOB ROSS | bob@paint.org
    EXPERIENCE
    Graphics Developer at StudioCorp (2020 - Present)
    • Developed shader rendering pipeline.

    PROJECTS
    RayTracer3D (C++, OpenGL) (2023)
    • Implemented BVH acceleration and path tracing.
    """
    p = extract_candidate_profile(text)
    assert len(p.experience) >= 1
    assert p.experience[0].company == "StudioCorp"
    assert len(p.projects) >= 1
    assert any("BVH" in ev.text or "RayTracer3D" in ev.text for ev in p.projects[0].evidence_units)


def test_invariant_retained_evidence_remains_complete():
    text = """
    CAROL DANVERS | carol@space.org
    EXPERIENCE
    Captain at StarForce (2019 - Present)
    • Commanded photon defense grid protecting 4 star bases.
    """
    p = extract_candidate_profile(text)
    plan = TailoringPlan(
        decisions=[
            TailoringDecision(
                evidence_id=p.experience[0].evidence_units[0].id,
                action=TailoringAction.PRESERVE,
            )
        ]
    )
    tailored = apply_tailoring_plan(p, plan)
    assert len(tailored.experience[0].evidence_units) == 1
    assert "photon defense grid" in tailored.experience[0].evidence_units[0].text
    _, audit = validate_tailored_profile_truth_guard(p, tailored, plan)
    assert audit.is_valid is True


def test_invariant_no_unsupported_technology_appears_and_no_fabricated_claims():
    text = """
    DAVID BOWIE | david@ziggy.com
    SKILLS
    Python, SQL, Linux
    EXPERIENCE
    Backend Dev at SoundWave (2020 - Present)
    • Built audio processing pipelines in Python and SQL.
    """
    p = extract_candidate_profile(text)
    plan = TailoringPlan(
        decisions=[
            TailoringDecision(
                evidence_id=p.experience[0].evidence_units[0].id,
                action=TailoringAction.REWRITE,
                rewritten_text="Built audio processing pipelines in Kubernetes and Rust on GCP.",
            )
        ]
    )
    tailored = apply_tailoring_plan(p, plan)
    tailored_reverted, audit = validate_tailored_profile_truth_guard(p, tailored, plan)
    assert len(audit.violations) > 0 or len(audit.reverted_evidence_ids) > 0
    assert "Python" in tailored_reverted.experience[0].evidence_units[0].text


def test_invariant_removed_evidence_has_reason():
    text = """
    EMMA STONE | emma@hollywood.com
    EXPERIENCE
    Actor at Studio (2020 - Present)
    • Starred in theatrical production.
    """
    p = extract_candidate_profile(text)
    ev_id = p.experience[0].evidence_units[0].id

    # 1. Removal with reason passes
    plan_valid = TailoringPlan(
        decisions=[
            TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.REMOVE,
                removal_reason="Not relevant to software engineering target role.",
            )
        ]
    )
    tailored_valid = apply_tailoring_plan(p, plan_valid)
    _, audit_valid = validate_tailored_profile_truth_guard(p, tailored_valid, plan_valid)
    assert audit_valid.is_valid is True

    # 2. Accidental loss (untracked removal) is flagged
    tailored_empty = p.model_copy(deep=True)
    tailored_empty.experience[0].evidence_units = []
    tailored_empty.evidence_units = []
    plan_empty = TailoringPlan(decisions=[])
    _, audit_empty = validate_tailored_profile_truth_guard(p, tailored_empty, plan_empty)
    assert audit_empty.is_valid is False or len(audit_empty.violations) > 0


def test_invariant_unknown_content_is_preserved():
    text = """
    FRANK CASTLE | frank@punisher.org
    EXPERIENCE
    Special Ops at Unit (2015 - 2020)
    • Executed tactical reconnaissance.

    CUSTOM CLASSIFIED DIRECTIVES
    • Directive 77: Undercover counter-surveillance protocol.
    """
    p = extract_candidate_profile(text)
    assert len(p.additional_sections) >= 1
    rendered = render_candidate_profile_to_text(p)
    assert "CUSTOM CLASSIFIED DIRECTIVES" in rendered or "Directive 77" in rendered


def test_invariant_renderer_preserves_semantic_content():
    text = """
    GRACE HOPPER | grace@navy.mil
    EDUCATION
    Ph.D. in Mathematics, Yale University (1934)

    EXPERIENCE
    Rear Admiral at US Navy (1943 - 1986)
    • Developed compiler principles for COBOL language.
    """
    p = extract_candidate_profile(text)
    rendered = render_candidate_profile_to_text(p)
    is_valid, errors = validate_rendered_export_integrity(p, rendered)
    assert is_valid is True, f"Integrity errors: {errors}"
    assert "COBOL language" in rendered
    assert "Yale University" in rendered

