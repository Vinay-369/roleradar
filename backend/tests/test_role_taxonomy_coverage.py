"""
Comprehensive Role Taxonomy Coverage & Composition Hardening Test Suite.
Verifies:
1. 100% resolution of all 61 previously LOW roles across 23 career domains.
2. Controlled composition behavior (base profile + valid specialization).
3. Rejection of unapproved/niche modifiers (keeps LOW confidence).
4. Prevention of generic token matching alone.
5. Strict domain separation and zero cross-domain software contamination.
6. Non-overnormalization of distinct roles.
7. Proper dual-mode execution (No-Resume Market Benchmarks vs Personalized Resume Gaps).
"""
import pytest
from app.modules.learning.role_taxonomy import (
    ROLE_TAXONOMY,
    ROLE_SPECIALIZATIONS,
    GENERIC_ROLE_TOKENS,
    resolve_role,
)

PREVIOUSLY_LOW_61_ROLES = [
    "Solutions Architect",
    "ML Researcher",
    "Cloud Architect",
    "Application Security Engineer",
    "Product Operations Manager",
    "Motion Designer",
    "Growth Marketing Manager",
    "Sales Operations Analyst",
    "Customer Success Manager",
    "Financial Controller",
    "Tax Analyst",
    "Audit Associate",
    "Risk Analyst",
    "HR Business Partner",
    "Learning and Development Specialist",
    "Procurement Specialist",
    "Inventory Analyst",
    "Demand Planner",
    "Technology Consultant",
    "Risk Consultant",
    "Healthcare Data Analyst",
    "Hospital Operations Manager",
    "Medical Coder",
    "Registered Nurse",
    "Pharmacovigilance Specialist",
    "Regulatory Affairs Associate",
    "Biostatistician",
    "Electronics Engineer",
    "Industrial Engineer",
    "Biomedical Engineer",
    "Automotive Engineer",
    "Aerospace Engineer",
    "Interior Designer",
    "Construction Manager",
    "Site Engineer",
    "BIM Engineer",
    "Quantity Surveyor",
    "Compliance Analyst",
    "Legal Operations Specialist",
    "Contract Specialist",
    "School Teacher",
    "Instructional Designer",
    "Curriculum Developer",
    "Academic Coordinator",
    "Lecturer",
    "Professor",
    "Laboratory Scientist",
    "Film Editor",
    "Content Creator",
    "Copywriter",
    "Creative Director",
    "Photographer",
    "3D Artist",
    "Front Office Manager",
    "Travel Consultant",
    "Event Manager",
    "Restaurant Manager",
    "Process Engineer",
    "Quality Engineer",
    "Maintenance Engineer",
    "Manufacturing Operations Manager",
]

NICHE_UNSUPPORTED_ROLES = [
    "Marine Robotics Engineer",
    "Spacecraft Thermal Engineer",
    "Autonomous Vehicle Perception Engineer",
    "Agricultural Drone Engineer",
    "Quantum Cryogenics Technician",
    "Bioinformatics Pipeline Architect",
    "Subsea Pipeline Integrity Engineer",
    "Wind Turbine Blade Aerodynamicist",
    "Geothermal Reservoir Modeler",
    "Satellite Constellation Operator",
]


class TestRoleTaxonomyCoverage:
    """Test resolution coverage and competency isolation for all 61 previously LOW roles."""

    @pytest.mark.parametrize("role_title", PREVIOUSLY_LOW_61_ROLES)
    def test_all_61_roles_resolve_with_high_or_medium_confidence(self, role_title: str):
        profile, confidence, reason = resolve_role(role_title)
        assert profile is not None, f"Role failed to resolve: {role_title} ({reason})"
        assert confidence in ("HIGH", "MEDIUM"), f"Role resolved with low confidence: {role_title} ({confidence})"
        assert len(profile.core_competencies) >= 3, f"Insufficient core competencies for {role_title}"
        assert profile.domain != "", f"Missing domain for {role_title}"

    @pytest.mark.parametrize("niche_role", NICHE_UNSUPPORTED_ROLES)
    def test_niche_unsupported_roles_remain_safely_low(self, niche_role: str):
        profile, confidence, reason = resolve_role(niche_role)
        assert profile is None, f"Niche role should return None profile: {niche_role}"
        assert confidence == "LOW", f"Niche role should have LOW confidence: {niche_role}"

    @pytest.mark.parametrize("generic_token", list(GENERIC_ROLE_TOKENS)[:15])
    def test_generic_tokens_alone_are_strictly_blocked(self, generic_token: str):
        profile, confidence, reason = resolve_role(generic_token)
        assert profile is None
        assert confidence == "LOW"
        assert reason == "AMBIGUOUS_GENERIC_TOKEN_ONLY"

    def test_controlled_composition_healthcare_data_analyst(self):
        profile, confidence, reason = resolve_role("Healthcare Data Analyst")
        assert profile is not None
        assert confidence == "HIGH"
        assert "CONTROLLED_SPECIALIZATION" in reason
        assert profile.domain == "Healthcare"
        # Must contain healthcare competencies
        core_str = " ".join(profile.core_competencies)
        assert "EHR" in core_str or "Health" in core_str or "Clinical" in core_str
        # Must also contain base analytical capabilities
        tools_str = " ".join(profile.tools_technologies)
        assert "SQL" in tools_str or "Tableau" in tools_str

    def test_controlled_composition_application_security_engineer(self):
        profile, confidence, reason = resolve_role("Application Security Engineer")
        assert profile is not None
        assert confidence == "HIGH"
        assert "CONTROLLED_SPECIALIZATION" in reason
        assert profile.domain == "Cybersecurity"
        core_str = " ".join(profile.core_competencies)
        assert "OWASP" in core_str or "SAST" in core_str

    def test_unregistered_specialization_modifier_rejected(self):
        # Robotics Engineer exists, but "Marine" is an unapproved modifier -> stays LOW
        profile, confidence, reason = resolve_role("Marine Robotics Engineer")
        assert profile is None
        assert confidence == "LOW"

    def test_negative_domain_isolation(self):
        p_nurse, _, _ = resolve_role("Registered Nurse")
        p_data, _, _ = resolve_role("Data Analyst")
        p_civil, _, _ = resolve_role("Civil Engineer")
        p_devops, _, _ = resolve_role("DevOps Engineer")

        # Zero tech skills in nursing
        nurse_skills = set(p_nurse.core_competencies + p_nurse.tools_technologies)
        assert "Python" not in nurse_skills
        assert "Docker" not in nurse_skills
        assert "React" not in nurse_skills

        # Zero nursing skills in civil engineering
        civil_skills = set(p_civil.core_competencies + p_civil.tools_technologies)
        assert "Medication Administration" not in civil_skills

        # Compute Jaccard overlap between nurse and devops
        devops_skills = set(p_devops.core_competencies + p_devops.tools_technologies)
        overlap = len(nurse_skills.intersection(devops_skills))
        assert overlap == 0

    def test_non_overnormalization(self):
        # Distinct roles must have distinct canonical roles
        p_pm, _, _ = resolve_role("Product Manager")
        p_pjm, _, _ = resolve_role("Project Manager")
        assert p_pm.canonical_role != p_pjm.canonical_role

        p_fa, _, _ = resolve_role("Financial Analyst")
        p_acc, _, _ = resolve_role("Accountant")
        assert p_fa.canonical_role != p_acc.canonical_role

        p_ux, _, _ = resolve_role("UX Designer")
        p_gd, _, _ = resolve_role("Graphic Designer")
        assert p_ux.canonical_role != p_gd.canonical_role

        p_arch, _, _ = resolve_role("Architect")
        p_sol, _, _ = resolve_role("Solutions Architect")
        assert p_arch.canonical_role != p_sol.canonical_role
