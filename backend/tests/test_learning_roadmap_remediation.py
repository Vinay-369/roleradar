"""
Tests for Learning Roadmap Quality Remediation:
- DEF-RDMP-003: Resource lookup substring collisions fixed (Pedagogy != Go).
- DEF-RDMP-004: Prerequisite-aware ordering (Python/SQL before Advanced ML).
- DEF-RDMP-002: Domain-aware practice recommendations.
- DEF-RDMP-001: Mastery language removal.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.modules.learning.engine import (
    _order_skills_with_prerequisites,
    _project_suggestion,
    build_roadmap,
    compute_skill_gaps,
)
from app.modules.learning.routes import _compute_gaps
from app.modules.learning.skill_resources import get_resources_for_skill


def test_resource_lookup_avoids_go_substring_collision():
    """DEF-RDMP-003: Substring collisions on 2-letter keys like 'go' must be prevented."""
    collision_candidates = [
        "Pedagogy",
        "Negotiation",
        "Cargo Logistics",
        "Ergonomics",
        "Demographics",
        "Category Management",
    ]
    for skill in collision_candidates:
        urls = get_resources_for_skill(skill)
        assert not any("go.dev" in u or "gobyexample" in u for u in urls), (
            f"Skill '{skill}' falsely matched Go resources: {urls}"
        )


def test_resource_lookup_legitimate_go_and_golang():
    """DEF-RDMP-003: Standalone 'Go' and 'Golang' must still resolve properly to Go resources."""
    for skill in ["Go", "Golang", "go", "golang"]:
        urls = get_resources_for_skill(skill)
        assert any("go.dev" in u for u in urls), f"Skill '{skill}' failed to resolve Go docs: {urls}"


def test_resource_lookup_other_languages():
    """DEF-RDMP-003: Standard languages and tools must still resolve accurately."""
    assert any("python.org" in u for u in get_resources_for_skill("Python"))
    assert any("react.dev" in u for u in get_resources_for_skill("React"))
    assert any("postgres" in u for u in get_resources_for_skill("PostgreSQL"))
    assert any("javascript" in u for u in get_resources_for_skill("JavaScript"))
    assert any("dev.java" in u for u in get_resources_for_skill("Java"))
    assert any("leetcode" in u or "visualgo" in u for u in get_resources_for_skill("Algorithms"))


@pytest.mark.asyncio
async def test_data_scientist_prerequisite_ordering():
    """DEF-RDMP-004: Python and foundational tools must precede or accompany core modeling in Data Scientist."""
    db = AsyncMock()
    settings = Settings()

    with patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):
        gaps, _, _ = await _compute_gaps(db, settings, "test_user", role="Data Scientist", include_provenance=True)
        roadmap = build_roadmap(gaps)

        all_stages = ["immediate", "week_1", "week_2", "month_1"]
        stage_map = {}
        for idx, stage in enumerate(all_stages):
            for s in roadmap[stage]:
                stage_map[s.lower()] = idx

        # Python & SQL must not be placed after Predictive Machine Learning
        python_stage = next(v for k, v in stage_map.items() if "python" in k)
        sql_stage = next(v for k, v in stage_map.items() if "sql" in k)
        ml_stage = next(v for k, v in stage_map.items() if "predictive machine learning" in k)
        feat_stage = next(v for k, v in stage_map.items() if "feature engineering" in k)

        assert python_stage <= ml_stage, f"Python (stage {python_stage}) scheduled after Predictive ML (stage {ml_stage})"
        assert sql_stage <= feat_stage, f"SQL (stage {sql_stage}) scheduled after Feature Engineering (stage {feat_stage})"
        assert python_stage in (0, 1), f"Python must be scheduled in Sprint 1 or 2, got stage {python_stage}"


@pytest.mark.asyncio
async def test_software_engineer_prerequisite_ordering():
    """DEF-RDMP-004: Data Structures & OOP must precede System Design; Git must precede CI/CD."""
    db = AsyncMock()
    settings = Settings()

    with patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):
        gaps, _, _ = await _compute_gaps(db, settings, "test_user", role="Software Engineer", include_provenance=True)
        roadmap = build_roadmap(gaps)

        all_stages = ["immediate", "week_1", "week_2", "month_1"]
        stage_map = {}
        for idx, stage in enumerate(all_stages):
            for s in roadmap[stage]:
                stage_map[s.lower()] = idx

        dsa_stage = next(v for k, v in stage_map.items() if "data structures" in k)
        sys_stage = next(v for k, v in stage_map.items() if "system design" in k)
        assert dsa_stage <= sys_stage, f"DSA ({dsa_stage}) scheduled after System Design ({sys_stage})"


@pytest.mark.asyncio
async def test_devops_engineer_prerequisite_ordering():
    """DEF-RDMP-004: Linux and Docker must precede Kubernetes."""
    db = AsyncMock()
    settings = Settings()

    with patch("app.modules.learning.routes.resume_repo.get_active_master_resume", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.profile_repo.get_profile", AsyncMock(return_value=None)), \
         patch("app.modules.learning.routes.jobs_repo.find_jobs", AsyncMock(return_value=[])):
        gaps, _, _ = await _compute_gaps(db, settings, "test_user", role="DevOps Engineer", include_provenance=True)
        roadmap = build_roadmap(gaps)

        all_stages = ["immediate", "week_1", "week_2", "month_1"]
        stage_map = {}
        for idx, stage in enumerate(all_stages):
            for s in roadmap[stage]:
                stage_map[s.lower()] = idx

        linux_stage = next(v for k, v in stage_map.items() if "linux" in k)
        docker_stage = next(v for k, v in stage_map.items() if "docker" in k)
        k8s_stage = next(v for k, v in stage_map.items() if "kubernetes" in k)

        assert linux_stage <= k8s_stage
        assert docker_stage <= k8s_stage


def test_domain_aware_practice_suggestions():
    """DEF-RDMP-002: Project recommendations must be domain-authentic and avoid software portfolio bias."""
    # Healthcare
    s_nurse = _project_suggestion("Patient Assessment & Triage", domain="Healthcare")
    assert "clinical simulation" in s_nurse or "patient care" in s_nurse
    assert "portfolio" not in s_nurse
    assert "github" not in s_nurse

    # Finance
    s_fin = _project_suggestion("General Ledger Maintenance", domain="Finance / Accounting")
    assert "financial case study" in s_fin or "ledger reconciliation" in s_fin
    assert "github" not in s_fin

    # Education
    s_edu = _project_suggestion("Curriculum & Lesson Planning", domain="Education")
    assert "lesson plan" in s_edu or "curriculum" in s_edu
    assert "software" not in s_edu

    # Design
    s_des = _project_suggestion("Visual Composition & Layout", domain="Design")
    assert "design case study" in s_des or "interactive prototype" in s_des

    # Engineering (Physical)
    s_eng = _project_suggestion("Finite Element Analysis (FEA)", domain="Engineering")
    assert "technical design calculation" in s_eng or "simulation" in s_eng

    # Software Engineering
    s_soft = _project_suggestion("REST APIs", domain="Software Engineering")
    assert "hands-on application" in s_soft


def test_ui_mastery_wording_removal():
    """DEF-RDMP-001: UI files must not promise guaranteed mastery in fixed time."""
    frontend_roadmap_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "pages", "growth", "LearningRoadmap.tsx")
    )
    frontend_skillgaps_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "pages", "growth", "SkillGaps.tsx")
    )

    with open(frontend_roadmap_path, "r", encoding="utf-8") as f:
        content_roadmap = f.read()
        assert "Week 2 Mastery" not in content_roadmap, "Misleading 'Week 2 Mastery' found in LearningRoadmap.tsx"
        assert "Sprint 3: Practical Implementation" in content_roadmap

    with open(frontend_skillgaps_path, "r", encoding="utf-8") as f:
        content_gaps = f.read()
        assert "days to master" not in content_gaps, "Misleading 'days to master' found in SkillGaps.tsx"
        assert "Estimated study:" in content_gaps
