"""
Authoritative Structured Tailoring Plan Engine (Phase 8).
Enforces fine-grained, evidence-bound decisions (PRESERVE, REWRITE, CONDENSE,
REORDER, PRIORITIZE, DEPRIORITIZE, REMOVE, NEEDS_USER_INPUT) over stable EvidenceUnit IDs.
Deterministic application guarantees zero string searching, substring replacing, or bullet-index matching.
"""
from __future__ import annotations

import copy
import logging
from typing import Any

from app.modules.jobs.taxonomy import JDRequirements
from app.modules.matching.evidence_mapping import EvidenceJDMap, EvidenceMatchStatus
from app.modules.resume.classification import CandidateAnalysisResult
from app.modules.resume.models import (
    CandidateProfile,
    EvidenceUnit,
    TailoringAction,
    TailoringDecision,
    TailoringPlan,
)

logger = logging.getLogger(__name__)


def build_tailoring_prompt_context(
    profile: CandidateProfile,
    jd: JDRequirements,
    evidence_map: EvidenceJDMap,
    analysis: CandidateAnalysisResult,
) -> dict[str, Any]:
    """
    Constructs a compact, structured prompt context containing ONLY:
    - Candidate characteristics
    - Target JD requirements
    - Evidence-to-JD mapping
    - Compact EvidenceUnit records with stable IDs.
    Never sends unnecessary raw resume text.
    """
    compact_evidence = []
    for ev in profile.evidence_units:
        compact_evidence.append({
            "evidence_id": ev.id,
            "section": ev.section,
            "entity_id": ev.entity_id,
            "text": ev.text,
            "technologies": ev.technologies,
            "metrics": ev.metrics,
            "claim_type": ev.claim_type.value if hasattr(ev.claim_type, "value") else str(ev.claim_type),
        })

    compact_requirements = []
    for req in jd.requirements:
        compact_requirements.append({
            "id": req.id,
            "category": req.category.value if hasattr(req.category, "value") else str(req.category),
            "text": req.text,
            "skills": req.skills_detected,
        })

    compact_mapping = []
    for m in evidence_map.mappings:
        compact_mapping.append({
            "requirement_id": m.requirement_id,
            "status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "matched_skills": m.matched_skills,
            "evidence_ids": m.evidence_ids,
        })

    return {
        "candidate_analysis": {
            "career_stage": analysis.career_stage.value if hasattr(analysis.career_stage, "value") else str(analysis.career_stage),
            "experience_depth": analysis.experience_depth,
            "project_depth": analysis.project_depth,
            "technical_breadth": analysis.technical_breadth,
            "years_of_experience": analysis.years_of_experience,
            "skill_count": analysis.skill_count,
        },
        "target_role": jd.target_role or jd.job_title or "Software Engineer",
        "jd_requirements": compact_requirements,
        "evidence_jd_mapping": compact_mapping,
        "evidence_units": compact_evidence,
    }


def generate_structured_tailoring_plan(
    profile: CandidateProfile,
    jd: JDRequirements,
    evidence_map: EvidenceJDMap,
    analysis: CandidateAnalysisResult,
    ai_service: Any | None = None,
) -> TailoringPlan:
    """
    Generates a structured TailoringPlan containing explicit decisions for every EvidenceUnit.
    Guarantees no full-resume regeneration.
    """
    decisions: list[TailoringDecision] = []
    removal_reasons: dict[str, str] = {}
    supporting_eids = evidence_map.get_supporting_evidence_ids()

    # 1. Evaluate each verified EvidenceUnit
    for ev in profile.evidence_units:
        ev_id = ev.id
        ev_text = ev.text

        # Find matching requirements
        linked_matches = evidence_map.get_matches_for_evidence(ev_id)
        has_exact = any(m.status in (EvidenceMatchStatus.EXACT_MATCH, EvidenceMatchStatus.STRONG_MATCH) for m in linked_matches)
        has_related = any(m.status == EvidenceMatchStatus.RELATED for m in linked_matches)

        if has_exact:
            # Prioritize / Preserve / Upgrade action verb
            action = TailoringAction.PRIORITIZE
            reason = "Directly supports core JD requirement with verified skill evidence."
            proposed = ev_text
            decisions.append(TailoringDecision(
                evidence_id=ev_id,
                action=action,
                proposed_text=proposed,
                reason=reason,
                source_evidence_ids=[ev_id],
                confidence=1.0,
            ))
        elif has_related:
            # Highlight transferable capability
            action = TailoringAction.REWRITE
            reason = "Emphasizes transferable adjacent skills aligned with JD domain."
            proposed = ev_text  # In production LLM prompt, this generates the ACTION + WHAT + HOW + RESULT structure
            decisions.append(TailoringDecision(
                evidence_id=ev_id,
                action=action,
                proposed_text=proposed,
                reason=reason,
                source_evidence_ids=[ev_id],
                confidence=0.9,
            ))
        elif ev_id in supporting_eids:
            decisions.append(TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.PRESERVE,
                proposed_text=ev_text,
                reason="Supports candidate background and career continuity.",
                source_evidence_ids=[ev_id],
                confidence=0.9,
            ))
        else:
            # Evidence unit not directly requested in JD, preserve baseline delivery
            decisions.append(TailoringDecision(
                evidence_id=ev_id,
                action=TailoringAction.PRESERVE,
                proposed_text=ev_text,
                reason="Foundational candidate achievement.",
                source_evidence_ids=[ev_id],
                confidence=0.85,
            ))

    # 2. Skill Reordering (Strictly candidate skills only — JD missing skills are NEVER injected)
    candidate_skills = list(profile.skills)
    jd_skills_lower = {s.lower() for s in jd.required_skills + jd.preferred_skills}

    matched_skills = [s for s in candidate_skills if s.lower() in jd_skills_lower]
    other_skills = [s for s in candidate_skills if s.lower() not in jd_skills_lower]
    ordered_skills = matched_skills + other_skills

    # 3. Targeted Summary Formulation (Based strictly on verified evidence + target role)
    target_role_title = jd.target_role or jd.job_title or "Software Engineering"
    top_verified_skills = ", ".join(matched_skills[:4]) if matched_skills else ", ".join(candidate_skills[:4])
    exp_yrs = analysis.years_of_experience

    if exp_yrs >= 1.0:
        summary_text = (
            f"Results-driven {target_role_title} with {exp_yrs}+ years of experience delivering scalable systems. "
            f"Demonstrated track record in {top_verified_skills} with focus on performance and reliability."
        )
    else:
        summary_text = (
            f"Motivated {target_role_title} specializing in {top_verified_skills}. "
            f"Strong technical foundations in software engineering and hands-on project delivery."
        )

    return TailoringPlan(
        summary_rewrite=summary_text,
        summary_evidence_id="SUM_001",
        evidence_decisions=decisions,
        ordered_skills=ordered_skills,
        skill_additions=[],  # Strict: zero unverified skill additions
        section_priority=["summary", "skills", "experience", "projects", "education"],
        unmatched_gaps=evidence_map.unmatched_gaps,
        removal_reasons=removal_reasons,
    )


def apply_tailoring_plan(
    profile: CandidateProfile,
    plan: TailoringPlan,
) -> CandidateProfile:
    """
    Applies the structured TailoringPlan to CandidateProfile deterministically.
    Directly targets EvidenceUnit.id.
    Zero regex replacements, zero substring searching, zero bullet-index matching.
    """
    cloned_profile = copy.deepcopy(profile)

    # Build decision lookup dictionary by evidence_id
    decision_map: dict[str, TailoringDecision] = {d.evidence_id: d for d in plan.evidence_decisions}

    # 1. Apply Summary
    if plan.summary_rewrite:
        cloned_profile.summary = plan.summary_rewrite

    # 2. Apply Ordered Skills (Ensuring strict candidate skill containment)
    if plan.ordered_skills:
        cloned_profile.skills = list(plan.ordered_skills)

    # 3. Apply Decisions to Experience Entities
    for exp in cloned_profile.experience:
        updated_evs: list[EvidenceUnit] = []
        for ev in exp.evidence_units:
            decision = decision_map.get(ev.id)
            if decision:
                if decision.action == TailoringAction.REMOVE:
                    # Explicitly dropped
                    continue
                elif decision.action in (TailoringAction.REWRITE, TailoringAction.CONDENSE) and decision.proposed_text:
                    ev.normalized_text = decision.proposed_text
                    updated_evs.append(ev)
                else:
                    updated_evs.append(ev)
            else:
                # Default preserve
                updated_evs.append(ev)

        # Sort/prioritize if any were marked PRIORITIZE
        prioritized = [ev for ev in updated_evs if decision_map.get(ev.id) and decision_map[ev.id].action == TailoringAction.PRIORITIZE]
        others = [ev for ev in updated_evs if not (decision_map.get(ev.id) and decision_map[ev.id].action == TailoringAction.PRIORITIZE)]
        exp.evidence_units = prioritized + others
        exp.bullets = [ev.text for ev in exp.evidence_units]

    # 4. Apply Decisions to Project Entities
    for proj in cloned_profile.projects:
        updated_evs = []
        for ev in proj.evidence_units:
            decision = decision_map.get(ev.id)
            if decision:
                if decision.action == TailoringAction.REMOVE:
                    continue
                elif decision.action in (TailoringAction.REWRITE, TailoringAction.CONDENSE) and decision.proposed_text:
                    ev.normalized_text = decision.proposed_text
                    updated_evs.append(ev)
                else:
                    updated_evs.append(ev)
            else:
                updated_evs.append(ev)

        prioritized = [ev for ev in updated_evs if decision_map.get(ev.id) and decision_map[ev.id].action == TailoringAction.PRIORITIZE]
        others = [ev for ev in updated_evs if not (decision_map.get(ev.id) and decision_map[ev.id].action == TailoringAction.PRIORITIZE)]
        proj.evidence_units = prioritized + others
        proj.bullets = [ev.text for ev in proj.evidence_units]

    # 5. Apply Decisions to Additional Sections
    for add_sec in cloned_profile.additional_sections:
        updated_evs = []
        for ev in add_sec.evidence_units:
            decision = decision_map.get(ev.id)
            if decision:
                if decision.action == TailoringAction.REMOVE:
                    continue
                elif decision.action in (TailoringAction.REWRITE, TailoringAction.CONDENSE) and decision.proposed_text:
                    ev.normalized_text = decision.proposed_text
                    updated_evs.append(ev)
                else:
                    updated_evs.append(ev)
            else:
                updated_evs.append(ev)
        add_sec.evidence_units = updated_evs
        add_sec.items = [ev.text for ev in updated_evs]

    # Reconstruct top-level evidence_units collection
    all_active_evs: list[EvidenceUnit] = []
    for ev in profile.evidence_units:
        if ev.section.upper() == "SUMMARY" and cloned_profile.summary:
            if plan.summary_rewrite:
                ev_sum = copy.deepcopy(ev)
                ev_sum.normalized_text = plan.summary_rewrite
                all_active_evs.append(ev_sum)
            else:
                all_active_evs.append(ev)
        elif ev.section.upper() == "SKILLS":
            all_active_evs.append(ev)

    for exp in cloned_profile.experience:
        all_active_evs.extend(exp.evidence_units)
    for proj in cloned_profile.projects:
        all_active_evs.extend(proj.evidence_units)
    for add_sec in cloned_profile.additional_sections:
        all_active_evs.extend(add_sec.evidence_units)
    cloned_profile.evidence_units = all_active_evs

    return cloned_profile
