"""
Phase 2 Semantic Resume Reconstruction & CandidateProfile Integrity Test Suite.
Verifies canonical structured entity preservation across Experience, Projects,
Education, Internships, Skills, Summary, and Provenance Tracking without lossy reparsing.
"""
import pytest
from app.modules.resume.models import (
    CandidateProfile,
    ClaimType,
    EducationEntity,
    EvidenceUnit,
    ProjectEntity,
    WorkExperienceEntity,
)
from app.modules.resume.parsing.structurer import (
    extract_candidate_profile,
    structure_resume_text,
    parse_experience_section,
    parse_projects_section,
    parse_education_section,
)


# ── A. Three separate employers remain three entities ──────────────────────────

def test_a_three_separate_employers_remain_three_entities():
    resume_text = """
Jane Doe
jane@example.com | 555-0100 | Austin, TX

EXPERIENCE
Acme Corporation
Senior Backend Engineer | Jan 2022 - Present
• Designed distributed caching service using Redis and Go, cutting API latency by 40%.
• Mentored 4 engineers in concurrency patterns.

Beta Technologies
Software Engineer | Jun 2019 - Dec 2021
• Built event-driven data ingestion pipeline processing 2M daily events via Apache Kafka.
• Optimized PostgreSQL database queries, reducing p99 response time by 30%.

Gamma Labs
Junior Developer | Aug 2017 - May 2019
• Developed REST APIs with Python and Flask.
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.experience) == 3, f"Expected 3 distinct employers, got {len(profile.experience)}"
    companies = [e.company.lower() for e in profile.experience]
    assert any("acme" in c for c in companies), "Acme Corporation missing"
    assert any("beta" in c for c in companies), "Beta Technologies missing"
    assert any("gamma" in c for c in companies), "Gamma Labs missing"

    # Verify roles and dates are preserved with respective employers
    acme_exp = next(e for e in profile.experience if "acme" in e.company.lower())
    assert "Senior Backend Engineer" in acme_exp.role
    assert "2022" in (acme_exp.dates or "")
    assert len(acme_exp.bullets) == 2

    beta_exp = next(e for e in profile.experience if "beta" in e.company.lower())
    assert "Software Engineer" in beta_exp.role
    assert "2019" in (beta_exp.dates or "")
    assert len(beta_exp.bullets) == 2


# ── B. Multiple roles at one employer remain separate roles ───────────────────

def test_b_multiple_roles_at_one_employer_remain_separate_roles():
    resume_text = """
John Smith
john@example.com | Seattle, WA

EXPERIENCE
Enterprise Cloud Corp
Lead Architect (2022 - Present)
• Spearheaded multi-cloud migration architecture across 50+ services.
Senior Systems Engineer (2019 - 2022)
• Built Kubernetes deployment automation saving 20 hours per sprint.
Systems Engineer (2017 - 2019)
• Maintained Linux server infrastructure with 99.9% uptime.
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.experience) == 1, f"Expected 1 employer with promotions, got {len(profile.experience)}"
    ent = profile.experience[0]
    assert "Enterprise Cloud" in ent.company
    assert len(ent.progression) == 3, f"Expected 3 progression roles, got {len(ent.progression)}"
    roles = [p.title for p in ent.progression]
    assert "Lead Architect" in roles[0]
    assert "Senior Systems Engineer" in roles[1]
    assert "Systems Engineer" in roles[2]


# ── C. Education works when degree appears before institution ─────────────────

def test_c_education_degree_before_institution():
    resume_text = """
Alice Walker
alice@example.com

EDUCATION
Master of Science in Computer Science
Stanford University, Stanford, CA
GPA: 3.9/4.0 | Sep 2020 - Jun 2022
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.education) == 1
    edu = profile.education[0]
    assert "Master of Science" in edu.degree, f"Expected degree to contain 'Master of Science', got {edu.degree!r}"
    assert "Stanford" in edu.institution, f"Expected institution to contain 'Stanford', got {edu.institution!r}"
    assert edu.gpa is not None and "3.9" in edu.gpa
    assert edu.dates is not None and "2020" in edu.dates


# ── D. Education works when institution appears before degree ─────────────────

def test_d_education_institution_before_degree():
    resume_text = """
Bob Vance
bob@example.com

EDUCATION
University of Texas at Austin
Bachelor of Science in Electrical Engineering
Dates: Aug 2016 - May 2020 | CGPA: 3.85 / 4.0
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.education) == 1
    edu = profile.education[0]
    assert "University of Texas" in edu.institution, f"Expected institution to contain 'University of Texas', got {edu.institution!r}"
    assert "Bachelor of Science" in edu.degree, f"Expected degree to contain 'Bachelor of Science', got {edu.degree!r}"
    assert edu.gpa is not None and "3.85" in edu.gpa
    assert edu.dates is not None and "2016" in edu.dates


# ── E. GPA/date/minor can occur on different lines ────────────────────────────

def test_e_gpa_date_minor_on_different_lines():
    resume_text = """
Carol Danvers
carol@example.com

EDUCATION
Embry-Riddle Aeronautical University, Daytona Beach, FL
Bachelor of Science in Aerospace Engineering
Minor: Applied Mathematics
GPA: 3.95/4.0
Graduation: May 2018
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.education) == 1
    edu = profile.education[0]
    assert "Embry-Riddle" in edu.institution
    assert "Bachelor of Science" in edu.degree
    assert edu.gpa is not None and "3.95" in edu.gpa
    assert edu.dates is not None and "2018" in edu.dates


# ── F. Multiple degrees remain separate ───────────────────────────────────────

def test_f_multiple_degrees_remain_separate():
    resume_text = """
David Miller
david@example.com

EDUCATION
Master of Science in Cybersecurity
Georgia Institute of Technology
GPA: 4.0 | 2021 - 2023

Bachelor of Science in Computer Science
University of Florida
GPA: 3.75 | 2017 - 2021
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.education) == 2, f"Expected 2 degrees, got {len(profile.education)}"
    d1, d2 = profile.education[0], profile.education[1]
    assert "Master" in d1.degree
    assert "Georgia" in d1.institution
    assert "Bachelor" in d2.degree
    assert "Florida" in d2.institution


# ── G. Internship entities survive into CandidateProfile ───────────────────────

def test_g_internship_entities_survive_into_candidate_profile():
    resume_text = """
Eva Green
eva@example.com

INTERNSHIPS
NASA Langley Research Center
Software Engineering Intern | May 2023 - Aug 2023
• Developed Python automation scripts for aerodynamic telemetry validation.
• Reduced data processing pipeline runtime by 50%.
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.internships) == 1, f"Expected 1 internship entity, got {len(profile.internships)}"
    intern = profile.internships[0]
    assert "NASA" in intern.company
    assert "Software Engineering Intern" in intern.role
    assert len(intern.bullets) == 2
    # Verify internship evidence units are present in ledger
    intern_evs = [ev for ev in profile.evidence_units if "NASA" in ev.id or "INTERN" in ev.section.upper() or "50%" in ev.text]
    assert len(intern_evs) >= 1, "Internship evidence units missing from ledger"


# ── H. Multi-line summary survives wrapping ───────────────────────────────────

def test_h_multiline_summary_survives_wrapping():
    resume_text = """
Frank Castle
frank@example.com | New York, NY

Experienced full stack developer with 7+ years of experience
architecting resilient cloud-native systems for high-growth
startups and established financial enterprises.

SKILLS
Python, Go, Java, Docker, AWS
"""
    profile = extract_candidate_profile(resume_text)

    assert profile.summary is not None, "Summary was not extracted from multi-line preamble"
    assert "7+ years" in profile.summary
    assert "cloud-native" in profile.summary
    assert "financial enterprises" in profile.summary


# ── I. Explicit skills do not get polluted by arbitrary body text ─────────────

def test_i_explicit_skills_not_polluted_by_body_text():
    resume_text = """
Grace Hopper
grace@example.com

SKILLS
Languages: COBOL, Fortran, C

EXPERIENCE
Navy Computing Lab
Director | 1955 - 1970
• Managed development of language compilers while consulting on TypeScript, React, and Kubernetes for modern radar systems.
"""
    profile = extract_candidate_profile(resume_text)

    # Candidate explicitly declared only COBOL, Fortran, C in Skills section
    declared = [s.lower() for s in (profile.skills_explicit or profile.skills)]
    assert "cobol" in declared
    assert "fortran" in declared
    assert "c" in declared

    # TypeScript / React were only mentioned in experience body, not declared in skills section
    if profile.skills_explicit:
        assert "typescript" not in [s.lower() for s in profile.skills_explicit]
        assert "react" not in [s.lower() for s in profile.skills_explicit]


# ── J. Inferred skills remain distinguishable from explicit skills ─────────────

def test_j_inferred_skills_distinguishable_from_explicit_skills():
    resume_text = """
Hannah Abbott
hannah@example.com

SKILLS
Python, SQL

EXPERIENCE
FinTech Corp
Engineer | 2021 - 2023
• Deployed microservices using Docker and Amazon AWS.
"""
    profile = extract_candidate_profile(resume_text)

    explicit = [s.lower() for s in profile.skills_explicit]
    assert "python" in explicit
    assert "sql" in explicit

    inferred = [s.lower() for s in profile.skills_inferred]
    assert any("docker" in s or "aws" in s for s in inferred) or "docker" in [s.lower() for s in profile.skills]


# ── K. Project title/technology/evidence remain attached ──────────────────────

def test_k_project_title_technology_evidence_remain_attached():
    resume_text = """
Ian Malcolm
ian@example.com

PROJECTS
Smart Logistics Dispatcher
Technologies: Go, gRPC, Redis, PostgreSQL
• Engineered real-time route optimization service handling 10,000 requests/sec.
• Reduced delivery scheduling conflicts by 35% through genetic routing algorithm.
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.projects) == 1
    proj = profile.projects[0]
    assert "Smart Logistics Dispatcher" in proj.title
    assert proj.tech_stack is not None and "Go" in proj.tech_stack
    assert len(proj.bullets) == 2
    assert any("10,000" in b for b in proj.bullets)
    assert any("35%" in b for b in proj.bullets)
    assert len(proj.evidence_units) == 2


# ── L. Two identical role titles do not produce evidence ID collisions ────────

def test_l_two_identical_role_titles_no_evidence_id_collisions():
    resume_text = """
Julia Roberts
julia@example.com

EXPERIENCE
Company One
Software Engineer | 2022 - Present
• Built data ingestion pipeline in Go.

Company Two
Software Engineer | 2020 - 2022
• Developed REST APIs in Python.
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.experience) == 2
    all_ev_ids = [ev.id for ev in profile.evidence_units]
    assert len(all_ev_ids) == len(set(all_ev_ids)), f"Duplicate Evidence IDs detected: {all_ev_ids}"


# ── M. Two identical project titles do not produce evidence ID collisions ─────

def test_m_two_identical_project_titles_no_evidence_id_collisions():
    resume_text = """
Kevin Bacon
kevin@example.com

PROJECTS
Mobile App
Technologies: Flutter, Dart
• Built cross-platform client app with 5,000 downloads.

Mobile App
Technologies: React Native, TypeScript
• Developed offline-first inventory tracker.
"""
    profile = extract_candidate_profile(resume_text)

    assert len(profile.projects) == 2
    all_ev_ids = [ev.id for ev in profile.evidence_units]
    assert len(all_ev_ids) == len(set(all_ev_ids)), f"Duplicate Evidence IDs detected: {all_ev_ids}"


# ── N. Missing optional fields do not cause crashes ───────────────────────────

def test_n_missing_optional_fields_do_not_crash():
    minimal_resume = """
Minimalist Dev
dev@example.com

EXPERIENCE
Some Company
• Built some feature.
"""
    profile = extract_candidate_profile(minimal_resume)

    assert isinstance(profile, CandidateProfile)
    assert profile.personal["email"] == "dev@example.com"
    assert len(profile.experience) == 1
    assert len(profile.experience[0].bullets) == 1
    assert profile.summary is None
    assert len(profile.education) == 0
    assert len(profile.projects) == 0


# ── O. Real stress-test resume end-to-end verification ────────────────────────

def test_o_stress_test_resume_full_fidelity():
    stress_resume = """Elisabeth Enricks
Washington, DC  |  +1 555-555-5555  |  eenricks@example.com  |  linkedin.com/in/eenricks

Experienced software engineer with 8+ years developing enterprise Java full-stack
applications for government and financial clients.

EDUCATION
Master of Science in Computer Science
Embry-Riddle Aeronautical University, Daytona Beach, FL
GPA: 3.9/4.0  |  Dec 2015

Bachelor of Science in Computer Science
Embry-Riddle Aeronautical University, Daytona Beach, FL
Minor: Mathematics  |  GPA: 3.8/4.0  |  May 2014

PROFESSIONAL EXPERIENCE

Capco
Senior Java Developer   |  Jan 2021 - Present
- Architected microservices-based trading platform processing 10M+ daily transactions
- Led migration of monolithic Oracle systems to distributed Spring Boot microservices
- Reduced deployment time by 40% using CI/CD pipelines with Jenkins and Docker
- Mentored team of 6 junior developers in TDD and Agile best practices

Sikorsky Aircraft Corporation
Full Stack Java Developer  |  Jun 2018 - Dec 2020
- Developed JSF/PrimeFaces web UIs for aircraft maintenance tracking systems
- Integrated REST APIs with Oracle DB using Hibernate ORM and Spring MVC
- Implemented role-based access control (RBAC) using Spring Security

Central Intelligence Agency
Software Engineer  |  Aug 2016 - May 2018
- Built classified data pipelines for intelligence analysts using Java EE and Oracle
- Developed C++ components for high-throughput signal processing system
- Clearance: TS/SCI with Full Scope Polygraph

INTERNSHIPS
NASA Langley Research Center
Software Engineering Intern  |  May 2015 - Aug 2015
- Developed Python automation scripts for aerodynamic data processing

PROJECTS
Enterprise Trading Dashboard
Technologies: Java, Spring Boot, Angular, Oracle DB, Kafka
- Built real-time trading analytics dashboard with sub-100ms latency
- Integrated Kafka streams for live market data processing

Classified Data Reconciler (Python, Oracle)
- Designed fault-tolerant ETL pipeline reconciling 500K+ records daily

SKILLS
Languages: Java, Python, C++, JavaScript, SQL
Frameworks: Spring Boot, Spring MVC, JSF, Hibernate, Angular
Databases: Oracle DB, PostgreSQL, MySQL
Platforms: AWS, Jenkins, Docker, Kubernetes, Linux

CERTIFICATIONS
Oracle Certified Professional Java SE 11 Developer
AWS Solutions Architect Associate

SECURITY CLEARANCE
TS/SCI with Full Scope Polygraph (Active)
"""
    profile = extract_candidate_profile(stress_resume)

    # 1. Personal & Summary
    assert profile.personal["name"] == "Elisabeth Enricks"
    assert profile.personal["location"] == "Washington, DC"
    assert profile.summary is not None and "8+ years" in profile.summary

    # 2. Education (2 degrees, correct degree & institution mapping, GPA, Dates)
    assert len(profile.education) == 2, f"Expected 2 degrees, got {len(profile.education)}"
    m_deg = next(e for e in profile.education if "Master" in e.degree)
    assert "Embry-Riddle" in m_deg.institution
    assert m_deg.gpa is not None and "3.9" in m_deg.gpa
    assert m_deg.dates is not None and "2015" in m_deg.dates

    b_deg = next(e for e in profile.education if "Bachelor" in e.degree)
    assert "Embry-Riddle" in b_deg.institution
    assert b_deg.gpa is not None and "3.8" in b_deg.gpa
    assert b_deg.dates is not None and "2014" in b_deg.dates

    # 3. Experience (3 distinct employers)
    assert len(profile.experience) == 3, f"Expected 3 employers, got {len(profile.experience)}"
    companies = [e.company for e in profile.experience]
    assert any("Capco" in c for c in companies)
    assert any("Sikorsky" in c for c in companies)
    assert any("Central Intelligence" in c or "CIA" in c for c in companies)

    # 4. Internships (1 internship entity)
    assert len(profile.internships) == 1, f"Expected 1 internship, got {len(profile.internships)}"
    assert "NASA" in profile.internships[0].company

    # 5. Projects (2 projects with tech stacks)
    assert len(profile.projects) == 2
    p1 = next(p for p in profile.projects if "Enterprise Trading" in p.title)
    assert len(p1.bullets) == 2
    assert "Kafka" in (p1.tech_stack or "")

    # 6. Additional sections (Security Clearance preserved)
    assert len(profile.additional_sections) >= 1
    assert any("SECURITY" in s.heading.upper() or "CLEARANCE" in s.heading.upper() for s in profile.additional_sections)

    # 7. Evidence Units & Unique IDs
    ev_ids = [ev.id for ev in profile.evidence_units]
    assert len(ev_ids) == len(set(ev_ids)), f"Duplicate Evidence IDs found: {ev_ids}"
    assert len(profile.evidence_units) >= 10
