from collections import Counter
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.embeddings.factory import build_embedding_provider
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs import repositories as jobs_repo
from app.modules.jobs.services import get_canonical_job_requirements
from app.modules.learning.engine import (
    build_roadmap,
    compute_skill_gaps,
    evaluate_career_competencies,
    determine_competency_tier,
    SkillGap,
)
from app.modules.learning.schemas import (
    RoadmapOut,
    SkillGapOut,
    CareerAlignmentOut,
    CareerAlignmentSummary,
    CanonicalRoleOut,
    _MIN_SKILLS_FOR_PERSONALIZATION,
)
from app.modules.profile import repositories as profile_repo
from app.modules.resume import repositories as resume_repo
from app.modules.resume.models import CandidateProfile
from app.modules.learning.skill_resources import get_resources_for_skill
from app.modules.matching.evidence_mapping import (
    map_resume_to_jd_evidence,
    EvidenceMatchStatus,
    RequirementCategory,
)
from app.modules.learning.role_taxonomy import (
    ROLE_TAXONOMY,
    match_canonical_role,
    resolve_role,
    _normalize_role_input,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Internal: provenance descriptor produced by _compute_gaps
# ---------------------------------------------------------------------------

@dataclass
class _RoadmapProvenance:
    """Captures why a roadmap has its current personalization status."""
    resume_found: bool         # Was an active master resume present?
    sufficient_evidence: bool  # Did the resume have >= _MIN_SKILLS_FOR_PERSONALIZATION skills?
    job_is_specific: bool      # Is the job context a real DB job (True) or market aggregate (False)?
    role_context: str          # Human-readable label, e.g. "Frontend Developer — Market Benchmark"
    role_confidence: str = "HIGH"
    provenance_source: str = "ROLE_TAXONOMY"
    message: str | None = None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _aggregate_role_requirements(db: AsyncIOMotorDatabase, target_role: str) -> dict:
    """
    Aggregates skill requirements deterministically using the canonical role taxonomy
    and relevant MongoDB market postings. Never injects arbitrary software fallbacks.
    """
    profile, confidence, match_reason = resolve_role(target_role)
    target_lower = target_role.lower().strip()

    # If unknown / low confidence, return clean limited-data state without fabricating generic tech skills
    if confidence == "LOW" or profile is None:
        return {
            "id": f"role_{target_lower.replace(' ', '_')}",
            "title": target_role,
            "company": "Market Standard",
            "must_have_skills": [],
            "preferred_skills": [],
            "skills_required": [],
            "skills_nice_to_have": [],
            "description": f"Limited market data available for {target_role}.",
            "jd_text": f"Target Role: {target_role}.",
            "experience_min": 0,
            "experience_max": 5,
            "job_type": "full_time",
            "location": "Any",
            "is_remote": True,
            "domain": "Unknown",
            "subdomain": "Specialized / Niche",
            "confidence": "LOW",
            "provenance": "LOW_CONFIDENCE",
            "message": "We couldn't confidently determine role-specific skill requirements for this role. Add a job description for a more precise analysis.",
        }

    # Canonical taxonomy base skills
    core_skills = list(profile.core_competencies)
    common_skills = list(profile.common_competencies) + [t for t in profile.tools_technologies if t not in profile.core_competencies][:3]
    optional_skills = list(profile.optional_competencies)

    # Search MongoDB jobs strictly matching this canonical role or known aliases
    # Disallows single generic token matching (e.g. 'analyst' or 'engineer')
    all_jobs = await jobs_repo.find_jobs(db, {}, limit=200)
    matching_jobs = []

    valid_titles_lower = {profile.canonical_role.lower().strip()} | {a.lower().strip() for a in profile.aliases}

    for j in all_jobs:
        job_title_norm = _normalize_role_input(j.get("title", ""))
        for vt in valid_titles_lower:
            vt_norm = _normalize_role_input(vt)
            if vt_norm == job_title_norm or (len(vt_norm.split()) >= 2 and vt_norm in job_title_norm):
                matching_jobs.append(j)
                break

    provenance = "ROLE_TAXONOMY"
    req_counter: Counter = Counter()
    nice_counter: Counter = Counter()

    if matching_jobs:
        provenance = "ROLE_TAXONOMY_AND_MARKET"
        for j in matching_jobs:
            if j.get("must_have_skills"):
                for s in j["must_have_skills"]:
                    req_counter[s] += 1
            else:
                for s in j.get("skills_required", []):
                    req_counter[s] += 1

            if j.get("preferred_skills"):
                for s in j["preferred_skills"]:
                    nice_counter[s] += 1
            else:
                for s in j.get("skills_nice_to_have", []):
                    nice_counter[s] += 1

    # Base weighting from taxonomy so domain integrity is strictly preserved
    for idx, s in enumerate(core_skills):
        req_counter[s] += (len(core_skills) - idx + 10)

    for idx, s in enumerate(common_skills):
        nice_counter[s] += (len(common_skills) - idx + 5)

    for s in optional_skills:
        nice_counter[s] += 2

    top_required = [s for s, _ in req_counter.most_common(8)]
    top_nice = [s for s, _ in nice_counter.most_common(6) if s not in top_required]

    return {
        "id": f"role_{target_lower.replace(' ', '_')}",
        "title": profile.canonical_role,
        "company": "Market Standard",
        "must_have_skills": top_required,
        "preferred_skills": top_nice,
        "skills_required": top_required,
        "skills_nice_to_have": top_nice,
        "description": f"Aggregated requirements for {profile.canonical_role} ({profile.domain} - {profile.subdomain}).",
        "jd_text": f"Target Role: {profile.canonical_role}. Required skills: {', '.join(top_required)}. Nice to have: {', '.join(top_nice)}.",
        "experience_min": 0,
        "experience_max": 5,
        "job_type": "full_time",
        "location": "Any",
        "is_remote": True,
        "domain": profile.domain,
        "subdomain": profile.subdomain,
        "confidence": confidence,
        "provenance": provenance,
        "message": None,
    }


async def _resolve_job_for_context(
    db: AsyncIOMotorDatabase,
    user_id: str,
    job_id: str | None = None,
    role: str | None = None,
) -> tuple[dict, bool]:
    """
    Returns (job_dict, job_is_specific).
    job_is_specific=True  → job is a real DB posting (JOB-type personalization).
    job_is_specific=False → job is a market aggregate (MARKET or CANDIDATE type).
    """
    if job_id:
        job = await jobs_repo.get_job_by_id(db, job_id)
        if job is not None:
            if job.get("source") == "custom" and job.get("user_id") and job.get("user_id") != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
            return job, True

    profile = await profile_repo.get_profile(db, user_id)
    target_role = role
    if not target_role and profile and profile.get("target_roles"):
        target_role = profile["target_roles"][0]

    job_agg = await _aggregate_role_requirements(db, target_role or "Software Engineer")
    return job_agg, False


async def _compute_gaps(
    db,
    settings,
    user_id: str,
    job_id: str | None = None,
    role: str | None = None,
    include_provenance: bool = False,
):
    """
    Returns (gaps, job) by default for backward compatibility.
    If include_provenance=True, returns (gaps, job, provenance).

    Evaluates:
    - CAREER GAP (no specific job): Canonical RoleCompetencyProfile against candidate evidence.
      Both with and without resume, uses the EXACT SAME canonical hierarchy.
      Preserves DEMONSTRATED skills, evidence provenance, and neutral wording.
    - JOB GAP (specific job ID): StructuredJobRequirements against candidate evidence
      using authoritative evidence mapping.
    """
    resume = await resume_repo.get_active_master_resume(db, user_id)
    job, job_is_specific = await _resolve_job_for_context(db, user_id, job_id=job_id, role=role)

    reqs = await get_canonical_job_requirements(db, job)

    resume_found = resume is not None and bool(resume.get("parsed"))
    role_confidence = job.get("confidence", "HIGH")
    provenance_source = job.get("provenance", "JOB_REQUIREMENTS" if job_is_specific else "ROLE_TAXONOMY")
    domain = job.get("domain")
    subdomain = job.get("subdomain")
    message = job.get("message")

    must_haves = reqs.must_have_skills if reqs.must_have_skills else job.get("skills_required", [])
    preferreds = reqs.preferred_skills if reqs.preferred_skills else job.get("skills_nice_to_have", [])

    job_title = job.get("title", reqs.target_role or (role or "Target Role"))
    target_role_query = role or job_title

    # --------------------------------------------------------------------------
    # MODE A: NO RESUME AVAILABLE
    # --------------------------------------------------------------------------
    if not resume_found:
        role_context = f"{job_title} — Market Benchmark"
        provenance = _RoadmapProvenance(
            resume_found=False,
            sufficient_evidence=False,
            job_is_specific=job_is_specific,
            role_context=role_context,
            role_confidence=role_confidence,
            provenance_source=provenance_source,
            message=message,
        )

        if not job_is_specific:
            role_prof, r_conf, _ = match_canonical_role(target_role_query)
            if role_prof is not None:
                gaps = evaluate_career_competencies(
                    role_prof,
                    candidate=None,
                    source=provenance_source,
                    confidence=r_conf,
                )
            elif role_confidence == "LOW" or (not must_haves and not preferreds):
                gaps = []
            else:
                gaps = compute_skill_gaps(
                    missing_required=must_haves,
                    partial_required=[],
                    missing_nice_to_have=preferreds,
                    job_title=job_title,
                    is_market_benchmark=True,
                    source=provenance_source,
                    confidence=role_confidence,
                    domain=domain,
                    subdomain=subdomain,
                )
        else:
            if role_confidence == "LOW" or (not must_haves and not preferreds):
                gaps = []
            else:
                gaps = compute_skill_gaps(
                    missing_required=must_haves,
                    partial_required=[],
                    missing_nice_to_have=preferreds,
                    job_title=job_title,
                    is_market_benchmark=True,
                    source=provenance_source,
                    confidence=role_confidence,
                    domain=domain,
                    subdomain=subdomain,
                )

        if include_provenance:
            return gaps, job, provenance
        return gaps, job

    # --------------------------------------------------------------------------
    # MODE B: RESUME AVAILABLE (CANONICAL CANDIDATE EVIDENCE ALIGNMENT)
    # --------------------------------------------------------------------------
    candidate_profile = CandidateProfile.from_parsed_dict(resume["parsed"])

    candidate_skills = list(candidate_profile.skills_explicit or candidate_profile.skills)
    for ev in candidate_profile.evidence_units:
        for t in ev.technologies:
            if t not in candidate_skills:
                candidate_skills.append(t)

    try:
        achievements = await resume_repo.list_achievements(db, user_id)
        for a in achievements or []:
            for t in a.get("skills_tags", []):
                if t not in candidate_skills:
                    candidate_skills.append(t)
    except Exception:
        pass

    sufficient_evidence = len(candidate_skills) >= _MIN_SKILLS_FOR_PERSONALIZATION

    if job_is_specific:
        role_context = f"{job_title} at {job.get('company', 'Company')}"
    else:
        role_context = f"{job_title} — Market Benchmark"

    provenance = _RoadmapProvenance(
        resume_found=True,
        sufficient_evidence=sufficient_evidence,
        job_is_specific=job_is_specific,
        role_context=role_context,
        role_confidence=role_confidence,
        provenance_source=provenance_source,
        message=message,
    )

    if role_confidence == "LOW" and not job_is_specific:
        gaps = []
        if include_provenance:
            return gaps, job, provenance
        return gaps, job

    if not job_is_specific:
        # CAREER GAP: Evaluate Canonical RoleCompetencyProfile against CandidateProfile
        role_prof, r_conf, _ = match_canonical_role(target_role_query)
        if role_prof is not None:
            gaps = evaluate_career_competencies(
                role_prof,
                candidate=candidate_profile,
                source=provenance_source,
                confidence=r_conf,
            )
        else:
            embedder = build_embedding_provider(settings)
            candidate_skills_lower = {s.lower().strip() for s in candidate_skills}
            missing_required = []
            partial_required = []
            candidate_status_map = {}
            for req_skill in must_haves:
                r_low = req_skill.lower().strip()
                if r_low in candidate_skills_lower:
                    candidate_status_map[req_skill] = "MATCHED"
                    continue
                best_sim = max((embedder.similarity(r_low, c) for c in candidate_skills_lower), default=0.0)
                if best_sim >= 0.55:
                    partial_required.append(req_skill)
                    candidate_status_map[req_skill] = "PARTIAL"
                else:
                    missing_required.append(req_skill)
                    candidate_status_map[req_skill] = "MISSING"

            missing_preferred = []
            for pref_skill in preferreds:
                p_low = pref_skill.lower().strip()
                if p_low in candidate_skills_lower:
                    candidate_status_map[pref_skill] = "MATCHED"
                    continue
                missing_preferred.append(pref_skill)
                candidate_status_map[pref_skill] = "MISSING"

            gaps = compute_skill_gaps(
                missing_required=missing_required,
                partial_required=partial_required,
                missing_nice_to_have=missing_preferred,
                job_title=job_title,
                is_market_benchmark=False,
                source=provenance_source,
                confidence=role_confidence,
                domain=domain,
                subdomain=subdomain,
                candidate_status_map=candidate_status_map,
            )
    else:
        # JOB GAP: StructuredJobRequirements against CandidateProfile
        embedder = build_embedding_provider(settings)
        candidate_skills_lower = {s.lower().strip() for s in candidate_skills}
        missing_required = []
        partial_required = []
        candidate_status_map = {}

        for req_skill in must_haves:
            r_low = req_skill.lower().strip()
            if r_low in candidate_skills_lower:
                candidate_status_map[req_skill] = "MATCHED"
                continue
            best_sim = max((embedder.similarity(r_low, c) for c in candidate_skills_lower), default=0.0)
            if best_sim >= 0.55:
                partial_required.append(req_skill)
                candidate_status_map[req_skill] = "PARTIAL"
            else:
                missing_required.append(req_skill)
                candidate_status_map[req_skill] = "MISSING"

        missing_preferred = []
        for pref_skill in preferreds:
            p_low = pref_skill.lower().strip()
            if p_low in candidate_skills_lower:
                candidate_status_map[pref_skill] = "MATCHED"
                continue
            missing_preferred.append(pref_skill)
            candidate_status_map[pref_skill] = "MISSING"

        gaps = compute_skill_gaps(
            missing_required=missing_required,
            partial_required=partial_required,
            missing_nice_to_have=missing_preferred,
            job_title=job_title,
            is_market_benchmark=False,
            source="JOB_REQUIREMENTS",
            confidence=role_confidence,
            domain=domain,
            subdomain=subdomain,
            candidate_status_map=candidate_status_map,
        )

    if include_provenance:
        return gaps, job, provenance
    return gaps, job


def _provenance_to_roadmap_fields(p: _RoadmapProvenance) -> dict:
    """
    Maps a _RoadmapProvenance to the RoadmapOut provenance fields.

    State matrix:
      no resume                              → MARKET / NONE / not personalized
      resume, insufficient evidence          → MARKET / LIMITED_EVIDENCE / not personalized
      resume, sufficient evidence, specific job → JOB / PERSONALIZED / personalized
      resume, sufficient evidence, role agg  → CANDIDATE / PERSONALIZED / personalized
    """
    base = {
        "role_context": p.role_context,
        "role_confidence": p.role_confidence,
        "provenance_source": p.provenance_source,
        "message": p.message,
    }

    if not p.resume_found:
        return {
            **base,
            "roadmap_type": "MARKET",
            "personalization_status": "NONE",
            "is_personalized": False,
        }
    if not p.sufficient_evidence:
        return {
            **base,
            "roadmap_type": "MARKET",
            "personalization_status": "LIMITED_EVIDENCE",
            "is_personalized": False,
        }
    if p.job_is_specific:
        return {
            **base,
            "roadmap_type": "JOB",
            "personalization_status": "PERSONALIZED",
            "is_personalized": True,
        }
    return {
        **base,
        "roadmap_type": "CANDIDATE",
        "personalization_status": "PERSONALIZED",
        "is_personalized": True,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/gaps", response_model=CareerAlignmentOut)
async def get_skill_gaps_for_role(
    role: str | None = Query(default=None, description="Target role name"),
    job_id: str | None = Query(default=None, description="Optional job ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, job, provenance = await _compute_gaps(
        db, settings, str(current_user["_id"]), job_id=job_id, role=role, include_provenance=True
    )

    demonstrated_count = sum(1 for g in gaps if getattr(g, "status", None) == "DEMONSTRATED")
    partial_count = sum(1 for g in gaps if getattr(g, "status", None) == "PARTIALLY_DEMONSTRATED")
    no_evidence_count = sum(1 for g in gaps if getattr(g, "status", None) == "NO_RESUME_EVIDENCE")

    summary = CareerAlignmentSummary(
        total=len(gaps),
        demonstrated=demonstrated_count,
        partially_demonstrated=partial_count,
        no_resume_evidence=no_evidence_count,
    )

    return CareerAlignmentOut(
        role=job.get("title", role or "Target Role"),
        domain=job.get("domain"),
        subdomain=job.get("subdomain"),
        confidence=job.get("confidence", "HIGH"),
        provenance=job.get("provenance", "ROLE_TAXONOMY"),
        has_resume=provenance.resume_found,
        message=job.get("message"),
        summary=summary,
        competencies=[SkillGapOut(**g.__dict__) for g in gaps],
    )


@router.get("/gaps/{job_id}", response_model=CareerAlignmentOut)
async def get_skill_gaps(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, job, provenance = await _compute_gaps(
        db, settings, str(current_user["_id"]), job_id=job_id, include_provenance=True
    )

    demonstrated_count = sum(1 for g in gaps if getattr(g, "status", None) == "DEMONSTRATED")
    partial_count = sum(1 for g in gaps if getattr(g, "status", None) == "PARTIALLY_DEMONSTRATED")
    no_evidence_count = sum(1 for g in gaps if getattr(g, "status", None) == "NO_RESUME_EVIDENCE")

    summary = CareerAlignmentSummary(
        total=len(gaps),
        demonstrated=demonstrated_count,
        partially_demonstrated=partial_count,
        no_resume_evidence=no_evidence_count,
    )

    return CareerAlignmentOut(
        role=job.get("title", "Target Opportunity"),
        domain=job.get("domain"),
        subdomain=job.get("subdomain"),
        confidence=job.get("confidence", "HIGH"),
        provenance=job.get("provenance", "JOB_REQUIREMENTS"),
        has_resume=provenance.resume_found,
        message=job.get("message"),
        summary=summary,
        competencies=[SkillGapOut(**g.__dict__) for g in gaps],
    )


@router.get("/roles", response_model=list[CanonicalRoleOut])
async def get_canonical_roles():
    """
    Returns canonical list of supported career roles directly from the backend authoritative
    ROLE_TAXONOMY, eliminating the need for hardcoded frontend duplicates.
    """
    roles = []
    for prof in ROLE_TAXONOMY.values():
        roles.append(CanonicalRoleOut(
            role=prof.canonical_role,
            domain=prof.domain,
            subdomain=prof.subdomain,
            aliases=prof.aliases,
        ))
    return roles


@router.get("/roadmap", response_model=RoadmapOut)
async def get_roadmap_for_role(
    role: str | None = Query(default=None, description="Target role name"),
    job_id: str | None = Query(default=None, description="Optional job ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, _, provenance = await _compute_gaps(
        db, settings, str(current_user["_id"]), job_id=job_id, role=role, include_provenance=True
    )
    roadmap = build_roadmap(gaps)
    return RoadmapOut(**roadmap, **_provenance_to_roadmap_fields(provenance))


@router.get("/roadmap/{job_id}", response_model=RoadmapOut)
async def get_roadmap(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    gaps, _, provenance = await _compute_gaps(
        db, settings, str(current_user["_id"]), job_id=job_id, include_provenance=True
    )
    roadmap = build_roadmap(gaps)
    return RoadmapOut(**roadmap, **_provenance_to_roadmap_fields(provenance))
