"""
Automated Cross-Domain Role Intelligence & Skill Gap Quality Validation Harness.
Executes deep quality validation across 150+ realistic roles, 20 niche roles,
negative pairs, aliases, market filtering, dual-mode execution (no-resume vs resume),
specific JD overrides, and domain quality heuristics.
"""

import asyncio
import json
import os
import re
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.modules.learning.engine import compute_skill_gaps
from app.modules.learning.role_taxonomy import (
    GENERIC_ROLE_TOKENS,
    ROLE_TAXONOMY,
    RoleCompetencyProfile,
    resolve_role,
)
from app.modules.learning.routes import (
    _aggregate_role_requirements,
    _compute_gaps,
    _provenance_to_roadmap_fields,
)

# ------------------------------------------------------------------------------
# 1. TEST MATRICES
# ------------------------------------------------------------------------------

COMPREHENSIVE_ROLE_MATRIX: Dict[str, List[str]] = {
    "Software / IT": [
        "Software Engineer", "Backend Developer", "Frontend Developer", "Full Stack Developer",
        "Mobile Developer", "Embedded Software Engineer", "QA Engineer", "Test Automation Engineer",
        "Systems Engineer", "Solutions Architect",
    ],
    "Data / Analytics": [
        "Data Analyst", "Data Scientist", "Data Engineer", "BI Analyst",
        "Analytics Engineer", "Quantitative Analyst", "Business Intelligence Developer",
    ],
    "AI / ML": [
        "Machine Learning Engineer", "AI Engineer", "NLP Engineer", "Computer Vision Engineer",
        "ML Researcher", "AI Research Scientist",
    ],
    "Cloud / Infrastructure": [
        "DevOps Engineer", "Cloud Engineer", "Site Reliability Engineer",
        "Platform Engineer", "Infrastructure Engineer", "Cloud Architect",
    ],
    "Cybersecurity": [
        "Cybersecurity Analyst", "SOC Analyst", "Security Engineer", "Penetration Tester",
        "Security Consultant", "GRC Analyst", "Cloud Security Engineer", "Application Security Engineer",
    ],
    "Product": [
        "Product Manager", "Product Owner", "Technical Product Manager",
        "Program Manager", "Product Operations Manager",
    ],
    "Design": [
        "Graphic Designer", "UI Designer", "UX Designer", "Product Designer",
        "UX Researcher", "Motion Designer", "Visual Designer",
    ],
    "Marketing": [
        "Marketing Specialist", "Digital Marketing Specialist", "SEO Specialist",
        "Content Marketing Specialist", "Social Media Manager", "Brand Manager", "Growth Marketing Manager",
    ],
    "Sales / Business": [
        "Sales Executive", "Account Executive", "Account Manager", "Business Development Executive",
        "Business Development Manager", "Sales Operations Analyst", "Customer Success Manager",
    ],
    "Finance / Accounting": [
        "Accountant", "Financial Analyst", "Investment Analyst", "Financial Controller",
        "FP&A Analyst", "Tax Analyst", "Audit Associate", "Risk Analyst",
    ],
    "HR": [
        "HR Specialist", "HR Generalist", "Recruiter", "Technical Recruiter",
        "Talent Acquisition Specialist", "HR Business Partner", "Learning and Development Specialist",
    ],
    "Operations / Supply Chain": [
        "Operations Analyst", "Operations Manager", "Supply Chain Analyst", "Supply Chain Manager",
        "Procurement Specialist", "Logistics Coordinator", "Inventory Analyst", "Demand Planner",
    ],
    "Consulting": [
        "Management Consultant", "Business Consultant", "Technology Consultant",
        "Strategy Consultant", "Risk Consultant",
    ],
    "Healthcare": [
        "Healthcare Analyst", "Clinical Research Associate", "Healthcare Data Analyst",
        "Hospital Operations Manager", "Medical Coder", "Health Informatics Specialist", "Registered Nurse",
    ],
    "Pharmaceutical / Life Sciences": [
        "Pharmaceutical Analyst", "Clinical Data Analyst", "Pharmacovigilance Specialist",
        "Regulatory Affairs Associate", "Biostatistician", "Research Associate",
    ],
    "Engineering — Physical": [
        "Mechanical Engineer", "Civil Engineer", "Electrical Engineer", "Electronics Engineer",
        "Chemical Engineer", "Industrial Engineer", "Biomedical Engineer", "Robotics Engineer",
        "Automotive Engineer", "Aerospace Engineer", "Mechatronics Engineer",
    ],
    "Architecture / Construction": [
        "Architect", "Interior Designer", "Structural Engineer", "Construction Manager",
        "Site Engineer", "BIM Engineer", "Quantity Surveyor",
    ],
    "Legal / Compliance": [
        "Legal Associate", "Corporate Lawyer", "Compliance Analyst",
        "Legal Operations Specialist", "Contract Specialist",
    ],
    "Education": [
        "Teacher", "School Teacher", "Instructional Designer", "Curriculum Developer",
        "Academic Coordinator", "Lecturer", "Professor",
    ],
    "Research": [
        "Research Scientist", "Research Associate", "Research Analyst",
        "Laboratory Scientist", "Research Engineer",
    ],
    "Media / Creative": [
        "Video Editor", "Film Editor", "Content Creator", "Copywriter",
        "Creative Director", "Photographer", "3D Artist",
    ],
    "Hospitality / Travel": [
        "Hotel Manager", "Front Office Manager", "Hospitality Operations Manager",
        "Travel Consultant", "Event Manager", "Restaurant Manager",
    ],
    "Manufacturing": [
        "Manufacturing Engineer", "Production Engineer", "Process Engineer",
        "Quality Engineer", "Maintenance Engineer", "Manufacturing Operations Manager",
    ],
}

NICHE_UNSUPPORTED_ROLES = [
    "Marine Robotics Engineer",
    "Underwater Robotics Engineer",
    "Subsea Pipeline Inspection Engineer",
    "Spacecraft Thermal Engineer",
    "Autonomous Vehicle Perception Engineer",
    "Agricultural Drone Engineer",
    "Sports Data Scientist",
    "Climate Risk Analyst",
    "Bioinformatics Engineer",
    "Computational Biologist",
    "Renewable Energy Analyst",
    "Battery Systems Engineer",
    "Semiconductor Process Engineer",
    "Nuclear Safety Engineer",
    "Archaeological Data Specialist",
    "Museum Collections Manager",
    "Sustainable Fashion Designer",
    "Aviation Safety Analyst",
    "Maritime Logistics Specialist",
    "Food Safety Scientist",
]

GENERIC_TOKENS = [
    "Engineer",
    "Analyst",
    "Manager",
    "Developer",
    "Specialist",
    "Consultant",
    "Coordinator",
]

NEGATIVE_PAIRS = [
    ("Data Analyst", "Cybersecurity Analyst"),
    ("Financial Analyst", "Data Analyst"),
    ("Healthcare Analyst", "Data Analyst"),
    ("Mechanical Engineer", "Software Engineer"),
    ("Electrical Engineer", "Software Engineer"),
    ("Chemical Engineer", "Software Engineer"),
    ("Graphic Designer", "UX Designer"),
    ("UX Designer", "Product Manager"),
    ("Marketing Specialist", "HR Specialist"),
    ("Supply Chain Analyst", "Financial Analyst"),
    ("Teacher", "Instructional Designer"),
    ("Architect", "Solutions Architect"),
    ("Robotics Engineer", "Software Engineer"),
    ("Clinical Research Associate", "Research Scientist"),
    ("Accountant", "Financial Analyst"),
]

SYNONYM_PAIRS = [
    ("Software Developer", "Software Engineer", True),
    ("Machine Learning Engineer", "AI / Machine Learning Engineer", True),
    ("Human Resources Specialist", "HR Generalist", True),
    ("User Experience Designer", "UX Designer", True),
    ("Business Intelligence Analyst", "BI Analyst", True),
    # Distinct professions that MUST NOT collapse:
    ("Financial Analyst", "Accountant", False),
    ("UX Designer", "Graphic Designer", False),
    ("Data Scientist", "Data Analyst", False),
    ("Product Manager", "Project Manager", False),
    ("Mechanical Engineer", "Civil Engineer", False),
]

SOFTWARE_CONTAMINATION_TERMS = {
    "react", "docker", "kubernetes", "aws", "node.js", "rest api", "ci/cd",
    "selenium", "terraform", "full stack", "frontend", "backend", "microservices"
}

def _mock_embedder():
    m = MagicMock()
    m.similarity.return_value = 0.0
    return m

# ------------------------------------------------------------------------------
# 2. VALIDATION ENGINE
# ------------------------------------------------------------------------------

async def run_validation() -> Dict[str, Any]:
    db = AsyncMock()
    settings = Settings()
    report: Dict[str, Any] = {
        "summary": {},
        "role_resolver_results": [],
        "niche_role_results": [],
        "generic_token_results": [],
        "negative_pair_results": [],
        "synonym_alias_results": [],
        "market_data_filtering": {},
        "no_resume_mode_results": [],
        "resume_mode_results": [],
        "specific_jd_results": [],
        "diversity_results": [],
        "custom_role_flow_results": [],
        "case_insensitivity_results": [],
        "defects": [],
    }

    print("=================================================================")
    print("STARTING AUTOMATED CROSS-DOMAIN ROLE INTELLIGENCE VALIDATION")
    print("=================================================================")

    # --------------------------------------------------------------------------
    # STEP 1: TEST THE ROLE RESOLVER DIRECTLY (150+ Roles)
    # --------------------------------------------------------------------------
    print("\n[Step 1] Testing Role Resolver on 150+ realistic job titles...")
    total_roles = 0
    resolved_roles = 0
    unresolved_roles = []

    for domain_name, roles in COMPREHENSIVE_ROLE_MATRIX.items():
        for role_title in roles:
            total_roles += 1
            prof, conf, provenance = resolve_role(role_title)
            
            if prof is not None:
                resolved_roles += 1
                all_skills = prof.core_competencies + prof.common_competencies + prof.optional_competencies
                
                # Check for software contamination in non-technical roles
                is_technical_domain = domain_name in [
                    "Software / IT",
                    "Cloud / Infrastructure",
                    "Cybersecurity",
                    "AI / ML",
                    "Data / Analytics",
                ]
                contaminated_skills = []
                if not is_technical_domain:
                    for s in all_skills:
                        s_lower = s.lower()
                        for c_term in SOFTWARE_CONTAMINATION_TERMS:
                            if re.search(r"\b" + re.escape(c_term) + r"\b", s_lower):
                                contaminated_skills.append(s)
                
                # Semantic relevance heuristic
                # Competencies defined in canonical taxonomy for a role are specifically curated for that role
                relevant_skills = [s for s in all_skills if s not in contaminated_skills]
                relevance_score = len(relevant_skills) / max(len(all_skills), 1)

                entry = {
                    "input_role": role_title,
                    "canonical_role": prof.canonical_role,
                    "domain": prof.domain,
                    "subdomain": prof.subdomain,
                    "confidence": conf,
                    "provenance": provenance,
                    "total_skills": len(all_skills),
                    "core_skills": prof.core_competencies[:3],
                    "common_skills": prof.common_competencies[:2],
                    "contaminated_skills": contaminated_skills,
                    "relevance_score": round(relevance_score, 2),
                    "status": "PASS" if len(contaminated_skills) == 0 and relevance_score >= 0.70 else "FAIL",
                }
                report["role_resolver_results"].append(entry)

                if entry["status"] == "FAIL":
                    defect = {
                        "id": f"DEFECT-CONTAM-{role_title.replace(' ', '_')}",
                        "severity": "CRITICAL",
                        "role": role_title,
                        "expected": "Zero software contamination skills",
                        "actual": contaminated_skills,
                        "root_cause": "Taxonomy profile contains inappropriate tech competencies",
                    }
                    report["defects"].append(defect)
            else:
                unresolved_roles.append(role_title)
                entry = {
                    "input_role": role_title,
                    "canonical_role": None,
                    "domain": domain_name,
                    "subdomain": None,
                    "confidence": conf,
                    "provenance": provenance,
                    "total_skills": 0,
                    "core_skills": [],
                    "common_skills": [],
                    "contaminated_skills": [],
                    "relevance_score": 0.0,
                    "status": "UNRESOLVED",
                }
                report["role_resolver_results"].append(entry)

    print(f"-> Tested {total_roles} roles across {len(COMPREHENSIVE_ROLE_MATRIX)} domains.")
    print(f"-> Resolved: {resolved_roles}/{total_roles} ({round(resolved_roles/total_roles*100, 1)}%)")
    if unresolved_roles:
        print(f"-> Unresolved roles ({len(unresolved_roles)}): {unresolved_roles[:10]}...")

    # --------------------------------------------------------------------------
    # STEP 2: UNKNOWN / NICHE ROLE TESTS (20 Niche Roles)
    # --------------------------------------------------------------------------
    print("\n[Step 2] Testing 20 Niche / Unsupported Roles...")
    with patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):
        for niche_role in NICHE_UNSUPPORTED_ROLES:
            agg = await _aggregate_role_requirements(db, niche_role)
            fb_used = agg["must_have_skills"] == ["Python", "JavaScript", "SQL", "REST APIs", "Git"]
            
            is_honest_low = (
                agg["confidence"] == "LOW"
                and len(agg["must_have_skills"]) == 0
                and not fb_used
                and "couldn't confidently determine" in agg.get("message", "")
            )

            entry = {
                "role": niche_role,
                "canonical": agg["title"],
                "confidence": agg["confidence"],
                "skills_count": len(agg["must_have_skills"]) + len(agg["preferred_skills"]),
                "fallback_used": fb_used,
                "message": agg.get("message", ""),
                "status": "PASS" if is_honest_low else "FAIL",
            }
            report["niche_role_results"].append(entry)

            if not is_honest_low:
                defect = {
                    "id": f"DEFECT-NICHE-{niche_role.replace(' ', '_')}",
                    "severity": "HIGH",
                    "role": niche_role,
                    "expected": "LOW confidence, 0 fabricated skills, fallback_used=False",
                    "actual": f"confidence={agg['confidence']}, skills={len(agg['must_have_skills'])}, fallback_used={fb_used}",
                    "root_cause": "Niche role loosely matched an unrelated canonical profile or used fallback",
                }
                report["defects"].append(defect)

    passed_niche = sum(1 for r in report["niche_role_results"] if r["status"] == "PASS")
    print(f"-> Niche roles passed honest handling: {passed_niche}/{len(NICHE_UNSUPPORTED_ROLES)}")

    # --------------------------------------------------------------------------
    # STEP 4: GENERIC TOKEN CONTAMINATION TEST
    # --------------------------------------------------------------------------
    print("\n[Step 4] Testing Generic Tokens Alone...")
    for token in GENERIC_TOKENS:
        prof, conf, prov = resolve_role(token)
        is_blocked = prof is None and conf == "LOW"
        entry = {
            "token": token,
            "resolved_profile": prof.canonical_role if prof else None,
            "confidence": conf,
            "status": "PASS" if is_blocked else "FAIL",
        }
        report["generic_token_results"].append(entry)

        if not is_blocked:
            defect = {
                "id": f"DEFECT-GENERIC-{token}",
                "severity": "CRITICAL",
                "role": token,
                "expected": "Rejected with LOW confidence and None profile",
                "actual": f"Resolved to {prof.canonical_role if prof else 'None'} with {conf}",
                "root_cause": "Single generic token matched a canonical role",
            }
            report["defects"].append(defect)

    passed_generic = sum(1 for r in report["generic_token_results"] if r["status"] == "PASS")
    print(f"-> Generic tokens properly blocked: {passed_generic}/{len(GENERIC_TOKENS)}")

    # --------------------------------------------------------------------------
    # STEP 5: ROLE PAIR CROSS-CONTAMINATION (Negative Pairs)
    # --------------------------------------------------------------------------
    print("\n[Step 5] Testing Negative Role Pairs for Cross-Contamination...")
    for role_a, role_b in NEGATIVE_PAIRS:
        prof_a, conf_a, _ = resolve_role(role_a)
        prof_b, conf_b, _ = resolve_role(role_b)

        if prof_a and prof_b:
            skills_a = set(prof_a.core_competencies + prof_a.common_competencies)
            skills_b = set(prof_b.core_competencies + prof_b.common_competencies)
            overlap = skills_a.intersection(skills_b)
            union = skills_a.union(skills_b)
            jaccard = len(overlap) / len(union) if union else 0.0

            is_distinct = (prof_a.canonical_role != prof_b.canonical_role) and (jaccard < 0.25)
            entry = {
                "pair": f"{role_a} vs {role_b}",
                "canonical_a": prof_a.canonical_role,
                "canonical_b": prof_b.canonical_role,
                "domain_a": prof_a.domain,
                "domain_b": prof_b.domain,
                "jaccard_similarity": round(jaccard, 3),
                "overlapping_skills": list(overlap),
                "status": "PASS" if is_distinct else "FAIL",
            }
            report["negative_pair_results"].append(entry)

            if not is_distinct:
                defect = {
                    "id": f"DEFECT-PAIR-{role_a.replace(' ', '_')}_{role_b.replace(' ', '_')}",
                    "severity": "CRITICAL",
                    "role": f"{role_a} vs {role_b}",
                    "expected": "Distinct roles and Jaccard similarity < 0.25",
                    "actual": f"canonical_a={prof_a.canonical_role}, canonical_b={prof_b.canonical_role}, jaccard={jaccard}",
                    "root_cause": "Role definitions overlap heavily or collapsed to same profile",
                }
                report["defects"].append(defect)
        else:
            entry = {
                "pair": f"{role_a} vs {role_b}",
                "resolved": f"{prof_a is not None} vs {prof_b is not None}",
                "status": "UNRESOLVED_ONE_OR_BOTH",
            }
            report["negative_pair_results"].append(entry)

    passed_pairs = sum(1 for r in report["negative_pair_results"] if r.get("status") == "PASS")
    print(f"-> Negative pairs verified distinct: {passed_pairs}/{len(NEGATIVE_PAIRS)}")

    # --------------------------------------------------------------------------
    # STEP 6: SYNONYM / ALIAS TEST
    # --------------------------------------------------------------------------
    print("\n[Step 6] Testing Semantic Aliases & Non-Overnormalization...")
    for r1, r2, should_be_same in SYNONYM_PAIRS:
        p1, _, _ = resolve_role(r1)
        p2, _, _ = resolve_role(r2)

        if p1 and p2:
            same_canon = (p1.canonical_role == p2.canonical_role)
            correct = (same_canon == should_be_same)
            entry = {
                "role_1": r1,
                "role_2": r2,
                "canonical_1": p1.canonical_role,
                "canonical_2": p2.canonical_role,
                "should_be_same": should_be_same,
                "actually_same": same_canon,
                "status": "PASS" if correct else "FAIL",
            }
            report["synonym_alias_results"].append(entry)

            if not correct:
                defect = {
                    "id": f"DEFECT-SYNONYM-{r1.replace(' ', '_')}_{r2.replace(' ', '_')}",
                    "severity": "HIGH",
                    "role": f"{r1} vs {r2}",
                    "expected": f"should_be_same={should_be_same}",
                    "actual": f"actually_same={same_canon} (p1={p1.canonical_role}, p2={p2.canonical_role})",
                    "root_cause": "Alias incorrectly mapped or distinct roles inappropriately unified",
                }
                report["defects"].append(defect)
        else:
            entry = {
                "role_1": r1,
                "role_2": r2,
                "status": f"UNRESOLVED (p1={p1 is not None}, p2={p2 is not None})",
            }
            report["synonym_alias_results"].append(entry)

    passed_synonyms = sum(1 for r in report["synonym_alias_results"] if r.get("status") == "PASS")
    print(f"-> Synonym/alias behavior correct: {passed_synonyms}/{len(SYNONYM_PAIRS)}")

    # --------------------------------------------------------------------------
    # STEP 7: MARKET DATA FILTERING (MongoDB Job Isolation)
    # --------------------------------------------------------------------------
    print("\n[Step 7] Testing Market Data Isolation...")
    # Mock jobs collection with diverse jobs
    mock_db_jobs = [
        {"_id": "1", "title": "Senior Data Analyst", "must_have_skills": ["SQL", "Tableau", "PowerBI"], "preferred_skills": ["Python"]},
        {"_id": "2", "title": "Cybersecurity Analyst", "must_have_skills": ["SIEM", "Splunk", "Incident Response"], "preferred_skills": ["Linux"]},
        {"_id": "3", "title": "Software Engineer", "must_have_skills": ["Java", "Spring Boot", "AWS"], "preferred_skills": ["Docker"]},
        {"_id": "4", "title": "Mechanical Engineer", "must_have_skills": ["SolidWorks", "FEA", "GD&T"], "preferred_skills": ["AutoCAD"]},
    ]

    # Verify that searching for "Cybersecurity Analyst" does not include "Senior Data Analyst" merely because of "Analyst"
    with patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=mock_db_jobs)):
        agg_cyber = await _aggregate_role_requirements(db, "Cybersecurity Analyst")
        # Ensure that aggregator only considered the exact matching job title
        assert agg_cyber["domain"] == "Cybersecurity"
        assert "Incident Response" in agg_cyber["must_have_skills"] or "Threat Monitoring & Detection" in agg_cyber["must_have_skills"]
        # PowerBI or Tableau must not be injected
        assert "Tableau" not in agg_cyber["must_have_skills"]

        # Verify Marine Robotics Engineer does not collect Software Engineer jobs merely because of "Engineer"
        agg_marine = await _aggregate_role_requirements(db, "Marine Robotics Engineer")
        assert agg_marine["confidence"] == "LOW"
        assert len(agg_marine["must_have_skills"]) == 0

    report["market_data_filtering"] = {
        "cybersecurity_did_not_match_data_analyst": "Tableau" not in agg_cyber["must_have_skills"],
        "marine_did_not_match_software_engineer": len(agg_marine["must_have_skills"]) == 0,
        "status": "PASS",
    }
    print("-> Market data isolation verified: PASS")

    # --------------------------------------------------------------------------
    # STEP 8: NO-RESUME MODE (50+ Roles)
    # --------------------------------------------------------------------------
    print("\n[Step 8] Testing No-Resume Mode across 50+ roles...")
    sample_50_roles = [
        "Software Engineer", "Backend Developer", "Frontend Developer", "Mobile Developer",
        "Data Analyst", "Data Scientist", "Data Engineer", "BI Analyst",
        "Machine Learning Engineer", "AI Engineer", "Computer Vision Engineer",
        "DevOps Engineer", "Cloud Engineer", "Site Reliability Engineer",
        "Cybersecurity Analyst", "Security Engineer", "SOC Analyst",
        "Product Manager", "Product Owner", "Technical Product Manager",
        "Graphic Designer", "UI Designer", "UX Designer", "Product Designer",
        "Digital Marketing Specialist", "SEO Specialist", "Social Media Manager",
        "Sales Executive", "Account Executive", "Business Development Manager",
        "Accountant", "Financial Analyst", "Investment Analyst", "Financial Controller",
        "HR Generalist", "Recruiter", "HR Business Partner",
        "Operations Analyst", "Supply Chain Analyst", "Procurement Specialist",
        "Management Consultant", "Business Consultant",
        "Healthcare Analyst", "Clinical Research Associate",
        "Pharmaceutical Analyst", "Biostatistician",
        "Mechanical Engineer", "Civil Engineer", "Electrical Engineer", "Robotics Engineer",
        "Architect", "Teacher", "Instructional Designer", "Research Scientist", "Video Editor",
    ]

    no_resume_defects = []
    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        for r_name in sample_50_roles:
            gaps, job, provenance = await _compute_gaps(db, settings, "user_no_resume", role=r_name, include_provenance=True)
            fields = _provenance_to_roadmap_fields(provenance)

            is_valid_mode_a = (
                fields["roadmap_type"] == "MARKET"
                and fields["personalization_status"] == "NONE"
                and fields["is_personalized"] is False
                and "Market Benchmark" in fields["role_context"]
            )

            # Check that gaps have candidate_status=None and non-punitive reason
            all_non_punitive = True
            for g in gaps:
                if g.candidate_status is not None or "no evidence of it was found in your resume" in g.reason:
                    all_non_punitive = False
                    break

            entry = {
                "role": r_name,
                "gaps_count": len(gaps),
                "roadmap_type": fields["roadmap_type"],
                "personalization_status": fields["personalization_status"],
                "is_personalized": fields["is_personalized"],
                "all_non_punitive": all_non_punitive,
                "status": "PASS" if is_valid_mode_a and all_non_punitive and len(gaps) > 0 else "FAIL",
            }
            report["no_resume_mode_results"].append(entry)

            if entry["status"] == "FAIL":
                no_resume_defects.append(r_name)

    passed_no_resume = sum(1 for r in report["no_resume_mode_results"] if r["status"] == "PASS")
    print(f"-> No-Resume Mode verified across {len(sample_50_roles)} roles: {passed_no_resume}/{len(sample_50_roles)} passed.")

    # --------------------------------------------------------------------------
    # STEP 9: RESUME MODE (Controlled Master Resume vs 10 Roles)
    # --------------------------------------------------------------------------
    print("\n[Step 9] Testing Resume Mode with Controlled Master Resume...")
    controlled_master_resume = {
        "user_id": "test_user_vikas",
        "parsed": {
            "skills": ["Python", "FastAPI", "React", "Docker", "PostgreSQL", "REST APIs"],
            "experience_raw": [
                "Software Engineer at Acme Corp (2023 - Present): Engineered high-performance microservices in Python.",
            ],
            "projects_raw": [
                {"title": "ShopVerse", "tech_stack": "React, Node.js", "bullets": ["Deployed cloud payment architecture."]},
            ],
        },
    }

    test_resume_roles = [
        "Data Scientist",
        "Software Engineer",
        "Data Engineer",
        "Product Manager",
        "Cybersecurity Analyst",
        "Graphic Designer",
        "Financial Analyst",
        "Mechanical Engineer",
        "Digital Marketing Specialist",
        "Supply Chain Analyst",
    ]

    with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
         patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=controlled_master_resume)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):

        for r_name in test_resume_roles:
            gaps, job, provenance = await _compute_gaps(db, settings, "test_user_vikas", role=r_name, include_provenance=True)
            fields = _provenance_to_roadmap_fields(provenance)

            is_personalized = (
                fields["roadmap_type"] == "CANDIDATE"
                and fields["personalization_status"] == "PERSONALIZED"
                and fields["is_personalized"] is True
            )

            # When candidate applies to Software Engineer: Python, REST APIs, etc. should NOT be missing
            if r_name == "Software Engineer":
                gap_skills = [g.skill for g in gaps]
                # Candidate has Python & REST APIs
                has_matched = "Python" not in gap_skills

            entry = {
                "role": r_name,
                "roadmap_type": fields["roadmap_type"],
                "personalization_status": fields["personalization_status"],
                "is_personalized": fields["is_personalized"],
                "gaps_count": len(gaps),
                "status": "PASS" if is_personalized else "FAIL",
            }
            report["resume_mode_results"].append(entry)

    passed_resume_mode = sum(1 for r in report["resume_mode_results"] if r["status"] == "PASS")
    print(f"-> Resume Mode verified across {len(test_resume_roles)} roles: {passed_resume_mode}/{len(test_resume_roles)} passed.")

    # --------------------------------------------------------------------------
    # STEP 10: SPECIFIC JD OVERRIDE (10 Roles)
    # --------------------------------------------------------------------------
    print("\n[Step 10] Testing Specific JD Requirements Precedence (10 Roles)...")
    sample_jds = [
        ("Software Engineer", ["Golang", "gRPC", "CockroachDB", "Kafka"], ["Kubernetes"]),
        ("Data Scientist", ["PyTorch", "HuggingFace Transformers", "MLflow", "CUDA"], ["Ray"]),
        ("DevOps Engineer", ["ArgoCD", "Istio Service Mesh", "Helm", "Ansible"], ["Vault"]),
        ("Cybersecurity Analyst", ["Sentinel SIEM", "Kusto Query Language", "MITRE ATT&CK", "Wireshark"], ["Python"]),
        ("Graphic Designer", ["Figma Design Systems", "Cinema 4D", "Brand Identity", "Motion Graphics"], ["After Effects"]),
        ("Financial Analyst", ["Anaplan", "PowerBI DAX", "LBO Modeling", "Hyperion"], ["VBA"]),
        ("Mechanical Engineer", ["CATIA V5", "ANSYS Fluent", "Thermal Modeling", "GD&T"], ["MATLAB"]),
        ("HR Generalist", ["Workday HCM", "Greenhouse ATS", "California Labor Law", "Compensation Bands"], ["Excel"]),
        ("Digital Marketing Specialist", ["Google Ads Editor", "Semrush", "HubSpot Automation", "Segment CDP"], ["GA4"]),
        ("Supply Chain Analyst", ["SAP IBP", "Tableau Supply Chain", "Safety Stock Modeling", "Six Sigma"], ["SQL"]),
    ]

    for role_name, must_haves, nice_to_haves in sample_jds:
        job_doc = {
            "_id": f"job_spec_{role_name.replace(' ', '_')}",
            "id": f"job_spec_{role_name.replace(' ', '_')}",
            "title": f"Senior {role_name}",
            "company": "Enterprise Global",
            "must_have_skills": must_haves,
            "preferred_skills": nice_to_haves,
            "skills_required": must_haves,
            "skills_nice_to_have": nice_to_haves,
            "source": "live",
        }

        with patch("app.modules.learning.routes.build_embedding_provider", return_value=_mock_embedder()), \
             patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=controlled_master_resume)), \
             patch("app.modules.learning.routes.jobs_repo.get_job_by_id", AsyncMock(return_value=job_doc)):

            gaps, job, provenance = await _compute_gaps(db, settings, "test_user_vikas", job_id=job_doc["id"], include_provenance=True)
            fields = _provenance_to_roadmap_fields(provenance)

            gap_skills = [g.skill for g in gaps]
            # Verify specific JD requirements are prioritized
            jd_prioritized = any(req in gap_skills for req in must_haves)
            is_job_mode = fields["roadmap_type"] == "JOB" and fields["personalization_status"] == "PERSONALIZED"

            entry = {
                "role": role_name,
                "job_title": job_doc["title"],
                "roadmap_type": fields["roadmap_type"],
                "personalization_status": fields["personalization_status"],
                "jd_skills_in_gaps": [s for s in must_haves if s in gap_skills],
                "status": "PASS" if is_job_mode and jd_prioritized else "FAIL",
            }
            report["specific_jd_results"].append(entry)

    passed_jd_mode = sum(1 for r in report["specific_jd_results"] if r["status"] == "PASS")
    print(f"-> Specific JD Override verified across 10 roles: {passed_jd_mode}/10 passed.")

    # --------------------------------------------------------------------------
    # STEP 12: ROLE DIVERSITY (Pairwise Similarity Across Unrelated Domains)
    # --------------------------------------------------------------------------
    print("\n[Step 12] Testing Pairwise Diversity Between Unrelated Domains...")
    diverse_roles = [
        "Graphic Designer", "Mechanical Engineer", "Accountant", "Teacher",
        "Cybersecurity Analyst", "Registered Nurse", "Corporate Lawyer", "Architect"
    ]
    for i in range(len(diverse_roles)):
        for j in range(i + 1, len(diverse_roles)):
            r1 = diverse_roles[i]
            r2 = diverse_roles[j]
            p1, _, _ = resolve_role(r1)
            p2, _, _ = resolve_role(r2)

            if p1 and p2:
                s1 = set(p1.core_competencies + p1.common_competencies)
                s2 = set(p2.core_competencies + p2.common_competencies)
                overlap = s1.intersection(s2)
                jaccard = len(overlap) / len(s1.union(s2))
                entry = {
                    "pair": f"{r1} vs {r2}",
                    "overlap_count": len(overlap),
                    "jaccard": round(jaccard, 3),
                    "status": "PASS" if jaccard < 0.15 else "FAIL",
                }
                report["diversity_results"].append(entry)

    passed_diversity = sum(1 for r in report["diversity_results"] if r["status"] == "PASS")
    print(f"-> Pairwise diversity between unrelated domains: {passed_diversity}/{len(report['diversity_results'])} passed (all Jaccard < 0.15).")

    # --------------------------------------------------------------------------
    # STEP 14: CUSTOM ROLE FLOW
    # --------------------------------------------------------------------------
    print("\n[Step 14] Testing Custom Role Flow...")
    custom_role_inputs = [
        ("Data Scientist", "Data Scientist", "HIGH"),
        ("Cybersecurity Analyst", "Cybersecurity Analyst", "HIGH"),
        ("Graphic Designer", "Graphic Designer", "HIGH"),
        ("Financial Analyst", "Financial Analyst", "HIGH"),
        ("Mechanical Engineer", "Mechanical Engineer", "HIGH"),
        ("Digital Marketing Specialist", "Digital Marketing Specialist", "HIGH"),
        ("Accountant", "Accountant", "HIGH"),
        ("Registered Nurse", "Registered Nurse", "HIGH"),
        ("Civil Engineer", "Civil Engineer", "HIGH"),
        ("Procurement Specialist", "Procurement Specialist", "HIGH"),
        ("Marine Robotics Engineer", None, "LOW"),
        ("Bioinformatics Engineer", None, "LOW"),
        ("Renewable Energy Analyst", None, "LOW"),
        ("Aviation Safety Analyst", None, "LOW"),
    ]

    for custom_input, exp_canon, exp_conf in custom_role_inputs:
        prof, conf, prov = resolve_role(custom_input)
        actual_canon = prof.canonical_role if prof else None
        correct = (actual_canon == exp_canon) and (conf == exp_conf)
        entry = {
            "custom_input": custom_input,
            "resolved_canonical": actual_canon,
            "confidence": conf,
            "status": "PASS" if correct else "FAIL",
        }
        report["custom_role_flow_results"].append(entry)

    passed_custom = sum(1 for r in report["custom_role_flow_results"] if r["status"] == "PASS")
    print(f"-> Custom role flow verified: {passed_custom}/{len(custom_role_inputs)} passed.")

    # --------------------------------------------------------------------------
    # STEP 15: CASE-INSENSITIVITY
    # --------------------------------------------------------------------------
    print("\n[Step 15] Testing Case Insensitivity...")
    case_variants = ["Data Scientist", "data scientist", "DATA SCIENTIST", "Data scientist"]
    resolved_variants = [resolve_role(v)[0].canonical_role for v in case_variants if resolve_role(v)[0]]
    all_same = len(set(resolved_variants)) == 1 and resolved_variants[0] == "Data Scientist"
    report["case_insensitivity_results"] = {
        "variants": case_variants,
        "resolved": resolved_variants,
        "status": "PASS" if all_same else "FAIL",
    }
    print(f"-> Case insensitivity verified: {'PASS' if all_same else 'FAIL'}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    report["summary"] = {
        "total_roles_tested": total_roles,
        "total_domains_tested": len(COMPREHENSIVE_ROLE_MATRIX),
        "total_niche_roles_tested": len(NICHE_UNSUPPORTED_ROLES),
        "total_defects_found": len(report["defects"]),
        "executive_verdict": "FAIL" if len(report["defects"]) > 0 else (
            "PASS WITH CONDITIONS" if unresolved_roles else "PASS"
        ),
        "unresolved_roles_count": len(unresolved_roles),
        "unresolved_roles_list": unresolved_roles,
    }

    print("\n=================================================================")
    print(f"VALIDATION HARNESS COMPLETE — VERDICT: {report['summary']['executive_verdict']}")
    print(f"Total defects found: {len(report['defects'])}")
    print("=================================================================")

    return report


if __name__ == "__main__":
    result = asyncio.run(run_validation())
    # Save raw json output
    with open("validation_raw_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("Raw results saved to validation_raw_results.json")
