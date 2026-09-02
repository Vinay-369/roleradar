"""
Authoritative Evidence to Job Description Mapping Layer (Phase 7).
Deterministically maps verified candidate EvidenceUnits against structured JD requirements.
Never inflates semantic similarity, hallucinates missing skills, or invents qualifications.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field

from app.modules.jobs.taxonomy import JobRequirement, RequirementCategory, StructuredJobRequirements
from app.modules.resume.models import CandidateProfile, EvidenceUnit


class EvidenceMatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    STRONG_MATCH = "STRONG_MATCH"
    SUPPORTED = "SUPPORTED"
    RELATED = "RELATED"
    PARTIAL = "PARTIAL"
    WEAK = "WEAK"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"

    # Backward compatibility aliases
    RELATED_EVIDENCE = "RELATED"
    PARTIAL_EVIDENCE = "PARTIAL"


MatchLevel = EvidenceMatchStatus
MatchSupportLevel = EvidenceMatchStatus


# Canonical Technology Synonyms (Strict equivalence)
TECH_SYNONYMS: dict[str, set[str]] = {
    "postgres": {"postgresql", "psql"},
    "postgresql": {"postgres", "psql"},
    "react": {"reactjs", "react.js"},
    "reactjs": {"react", "react.js"},
    "node": {"nodejs", "node.js"},
    "nodejs": {"node", "node.js"},
    "golang": {"go"},
    "go": {"golang"},
    "kubernetes": {"k8s"},
    "k8s": {"kubernetes"},
    "aws": {"amazon web services"},
    "gcp": {"google cloud", "google cloud platform"},
    "typescript": {"ts"},
    "javascript": {"js"},
    "mongodb": {"mongo"},
}

# Related (Adjacent / Non-Equivalent) Skill Clusters
RELATED_SKILL_CLUSTERS = [
    {"python", "flask", "fastapi", "django", "tornado", "backend"},
    {"react", "vue", "angular", "svelte", "next.js", "frontend", "typescript", "javascript"},
    {"docker", "kubernetes", "containers", "eks", "helm", "devops", "containerd"},
    {"postgresql", "mysql", "sql", "mongodb", "redis", "cassandra", "dynamodb"},
    {"aws", "gcp", "azure", "cloud", "terraform"},
    {"pytorch", "tensorflow", "opencv", "machine learning", "deep learning", "ai", "keras", "scikit-learn"},
    {"c++", "c", "rust", "go", "systems programming", "embedded"},
]


class RequirementEvidenceMapping(BaseModel):
    requirement_id: str
    requirement_text: str
    category: RequirementCategory
    status: EvidenceMatchStatus
    match_level: EvidenceMatchStatus | None = None
    matched_skills: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    matched_evidence_units: list[EvidenceUnit] = Field(default_factory=list)
    matched_entity_ids: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    notes: str = ""

    @property
    def support_level(self) -> EvidenceMatchStatus:
        return self.status


EvidenceRequirementMatch = RequirementEvidenceMapping


class EvidenceJDMap(BaseModel):
    mappings: list[RequirementEvidenceMapping] = Field(default_factory=list)
    matches: list[RequirementEvidenceMapping] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    conflicting_requirements: list[str] = Field(default_factory=list)
    unmatched_gaps: list[str] = Field(default_factory=list)
    exact_matches_count: int = 0
    strong_matches_count: int = 0
    supported_matches_count: int = 0
    related_matches_count: int = 0
    partial_matches_count: int = 0
    weak_matches_count: int = 0
    missing_matches_count: int = 0
    conflicting_matches_count: int = 0
    missing_must_haves: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    supported_skills_count: int = 0
    overall_evidence_score: float = 0.0

    def __iter__(self):
        return iter(self.mappings)

    def __getitem__(self, item):
        return self.mappings[item]

    def __len__(self):
        return len(self.mappings)

    def get_matches_for_requirement(self, requirement_id: str) -> list[RequirementEvidenceMapping]:
        """Returns all match items for a specific requirement ID."""
        return [m for m in self.mappings if m.requirement_id == requirement_id]

    def get_matches_for_evidence(self, evidence_id: str) -> list[RequirementEvidenceMapping]:
        """Returns all requirement mappings supported by a specific EvidenceUnit ID."""
        return [m for m in self.mappings if evidence_id in m.evidence_ids]

    def get_top_supporting_evidence(self, requirement_id: str, limit: int = 3) -> list[str]:
        """Returns the top EvidenceUnit IDs supporting a given requirement."""
        req_matches = self.get_matches_for_requirement(requirement_id)
        if not req_matches:
            return []
        ev_ids = []
        for m in req_matches:
            for eid in m.evidence_ids:
                if eid not in ev_ids:
                    ev_ids.append(eid)
        return ev_ids[:limit]

    def get_supporting_evidence_ids(self) -> set[str]:
        """Returns the set of all EvidenceUnit IDs that actively support at least one JD requirement."""
        active = set()
        for m in self.mappings:
            if m.status not in (EvidenceMatchStatus.MISSING, EvidenceMatchStatus.CONFLICTING):
                active.update(m.evidence_ids)
        return active


EvidenceMappingMatrix = EvidenceJDMap


def _find_related_skills(skill: str) -> set[str]:
    skill_lower = skill.lower()
    related: set[str] = set()
    for cluster in RELATED_SKILL_CLUSTERS:
        if skill_lower in cluster:
            related.update(cluster - {skill_lower})
    return related


def _check_synonym_match(target_skill: str, candidate_skills: set[str]) -> str | None:
    target_lower = target_skill.lower()
    synonyms = TECH_SYNONYMS.get(target_lower, set())
    for s in candidate_skills:
        if s.lower() in synonyms:
            return s
    return None


def map_resume_to_jd_evidence(
    profile: CandidateProfile,
    job_reqs: StructuredJobRequirements,
) -> EvidenceJDMap:
    """
    Maps candidate evidence units against structured job requirements deterministically.
    Never inflates semantic similarity. Strictly distinguishes EXACT, STRONG, SUPPORTED,
    RELATED, PARTIAL, WEAK, MISSING, and CONFLICTING match levels.
    """
    candidate_skills_lower = {s.lower() for s in profile.skills}
    for ev in profile.evidence_units:
        for t in ev.technologies:
            candidate_skills_lower.add(t.lower())

    mappings: list[RequirementEvidenceMapping] = []
    exact_count = 0
    strong_count = 0
    supported_count = 0
    related_count = 0
    partial_count = 0
    weak_count = 0
    missing_count = 0
    conflicting_count = 0
    missing_must_haves: set[str] = set()
    missing_preferred: set[str] = set()
    conflicting_reqs: list[str] = []
    unmatched_gaps: list[str] = []
    all_matched_skills: set[str] = set()

    total_weighted_score = 0.0
    total_weights = 0.0

    for req in job_reqs.requirements:
        # Skip non-requirement context categories (e.g. company overview, benefits, legal)
        if req.category in (
            RequirementCategory.COMPANY_OVERVIEW,
            RequirementCategory.ROLE_OVERVIEW,
            RequirementCategory.BENEFITS,
            RequirementCategory.EEO_LEGAL,
            RequirementCategory.UNKNOWN,
        ):
            continue

        matched_evs: list[EvidenceUnit] = []
        matched_skills: list[str] = []
        matched_entities: list[str] = []
        status = EvidenceMatchStatus.MISSING
        score = 0.0
        reason = ""

        req_lower = req.text.lower()

        # 1. CONFLICTING Requirement Check
        is_conflicting = False
        if any(w in req_lower for w in ["top secret", "security clearance", "us citizenship required"]):
            has_clearance = any("clearance" in ev.normalized_text.lower() or "citizen" in ev.normalized_text.lower() for ev in profile.evidence_units)
            if not has_clearance:
                is_conflicting = True
                status = EvidenceMatchStatus.CONFLICTING
                score = 0.0
                conflicting_count += 1
                reason = "Candidate lacks required security clearance or citizenship authorization."
                conflicting_reqs.append(req.text)

        # Seniority conflict (e.g. Director role for student/fresher)
        if not is_conflicting and any(w in req_lower for w in ["10+ years", "12+ years", "15+ years", "director of", "vice president"]):
            is_student_or_fresher = len(profile.experience) == 0 and len(profile.projects) >= 1
            if is_student_or_fresher:
                is_conflicting = True
                status = EvidenceMatchStatus.CONFLICTING
                score = 0.0
                conflicting_count += 1
                reason = "Candidate is a student/fresher; does not satisfy executive tenure requirements."
                conflicting_reqs.append(req.text)

        if is_conflicting:
            pass
        else:
            # 2. Exact and Synonym Skill Matching
            exact_found = [s for s in req.skills_detected if s.lower() in candidate_skills_lower]
            synonym_found: list[str] = []
            if not exact_found:
                for s in req.skills_detected:
                    syn = _check_synonym_match(s, candidate_skills_lower)
                    if syn:
                        synonym_found.append(syn)

            if exact_found or synonym_found:
                target_skills = exact_found or synonym_found
                matched_skills.extend(target_skills)
                all_matched_skills.update(target_skills)

                # Locate supporting EvidenceUnits
                for ev in profile.evidence_units:
                    ev_techs_lower = {t.lower() for t in ev.technologies}
                    if any(s.lower() in ev_techs_lower or s.lower() in ev.normalized_text.lower() for s in target_skills):
                        if ev not in matched_evs:
                            matched_evs.append(ev)
                            if ev.entity_id and ev.entity_id not in matched_entities:
                                matched_entities.append(ev.entity_id)

                if exact_found:
                    if matched_evs:
                        status = EvidenceMatchStatus.EXACT_MATCH
                        score = 1.0
                        exact_count += 1
                        reason = f"Exact skill match verified with {len(matched_evs)} evidence units ({', '.join(matched_entities)})."
                    else:
                        status = EvidenceMatchStatus.SUPPORTED
                        score = 0.85
                        supported_count += 1
                        reason = "Skill listed in profile, supported by general qualifications."
                else:
                    # Synonym match -> STRONG_MATCH
                    status = EvidenceMatchStatus.STRONG_MATCH
                    score = 0.95
                    strong_count += 1
                    reason = f"Strong synonym match ({', '.join(synonym_found)}) supported by candidate evidence."

            elif req.category == RequirementCategory.RESPONSIBILITY:
                # 3. Responsibility Support Check
                req_words = [w for w in req_lower.split() if len(w) > 3 and w not in {"with", "that", "from", "your", "their", "will", "have", "experience", "proven"}]
                resp_matched_evs = [
                    ev for ev in profile.evidence_units
                    if sum(1 for w in req_words if w in ev.normalized_text.lower()) >= 2
                ]
                if resp_matched_evs:
                    matched_evs.extend(resp_matched_evs)
                    for ev in resp_matched_evs:
                        if ev.entity_id and ev.entity_id not in matched_entities:
                            matched_entities.append(ev.entity_id)
                    status = EvidenceMatchStatus.SUPPORTED
                    score = 0.85
                    supported_count += 1
                    reason = f"Supported by {len(resp_matched_evs)} candidate delivery evidence units."
                else:
                    status = EvidenceMatchStatus.MISSING
                    score = 0.0
                    missing_count += 1
                    reason = "No candidate evidence found supporting this responsibility."
                    unmatched_gaps.append(req.text)

            else:
                # 4. Related (Adjacent) Skills Check -> RELATED / PARTIAL
                related_candidates: set[str] = set()
                for s in req.skills_detected:
                    related_candidates.update(_find_related_skills(s))

                related_found = [s for s in related_candidates if s in candidate_skills_lower]
                if related_found:
                    matched_skills.extend(related_found)
                    for ev in profile.evidence_units:
                        ev_techs_lower = {t.lower() for t in ev.technologies}
                        if any(r in ev_techs_lower or r in ev.normalized_text.lower() for r in related_found):
                            if ev not in matched_evs:
                                matched_evs.append(ev)
                                if ev.entity_id and ev.entity_id not in matched_entities:
                                    matched_entities.append(ev.entity_id)

                    status = EvidenceMatchStatus.RELATED
                    score = 0.70
                    related_count += 1
                    reason = f"Related adjacent technology ({', '.join(related_found)}) provides transferable foundation (not exact match)."
                else:
                    # 5. Semantic / Partial Keyword Overlap -> PARTIAL / WEAK
                    req_words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", req_lower) if w not in {"with", "that", "from", "your", "their", "will", "have", "experience", "proven", "background", "years"}]
                    text_matched_evs = [
                        ev for ev in profile.evidence_units
                        if any(w in ev.normalized_text.lower() for w in req_words)
                    ]
                    if len(text_matched_evs) >= 2:
                        matched_evs.extend(text_matched_evs)
                        for ev in text_matched_evs:
                            if ev.entity_id and ev.entity_id not in matched_entities:
                                matched_entities.append(ev.entity_id)
                        status = EvidenceMatchStatus.PARTIAL
                        score = 0.50
                        partial_count += 1
                        reason = f"Partial domain overlap supported by {len(text_matched_evs)} evidence units."
                    elif len(text_matched_evs) == 1:
                        matched_evs.extend(text_matched_evs)
                        status = EvidenceMatchStatus.WEAK
                        score = 0.30
                        weak_count += 1
                        reason = "Weak transferable overlap."
                    else:
                        status = EvidenceMatchStatus.MISSING
                        score = 0.0
                        missing_count += 1
                        reason = "Missing qualification: no candidate evidence found."
                        unmatched_gaps.append(req.text)
                        if req.category == RequirementCategory.MUST_HAVE:
                            missing_must_haves.update(req.skills_detected or [req.text[:30]])
                        elif req.category == RequirementCategory.PREFERRED:
                            missing_preferred.update(req.skills_detected or [req.text[:30]])

        total_weighted_score += score * req.importance_weight
        total_weights += req.importance_weight

        ev_ids = [ev.id for ev in matched_evs]

        mapping_item = RequirementEvidenceMapping(
            requirement_id=req.id,
            requirement_text=req.text,
            category=req.category,
            status=status,
            match_level=status,
            matched_skills=matched_skills,
            evidence_ids=ev_ids,
            matched_evidence_units=matched_evs,
            matched_entity_ids=matched_entities,
            relevance_score=score,
            confidence=score,
            reason=reason,
            notes=reason,
        )
        mappings.append(mapping_item)

    overall_score = round((total_weighted_score / total_weights * 100.0), 1) if total_weights > 0 else 50.0

    missing_skills_list = sorted(list(missing_must_haves | missing_preferred))

    return EvidenceJDMap(
        mappings=mappings,
        matches=mappings,
        matched_skills=sorted(list(all_matched_skills)),
        missing_skills=missing_skills_list,
        conflicting_requirements=conflicting_reqs,
        unmatched_gaps=unmatched_gaps,
        exact_matches_count=exact_count,
        strong_matches_count=strong_count,
        supported_matches_count=supported_count,
        related_matches_count=related_count,
        partial_matches_count=partial_count,
        weak_matches_count=weak_count,
        missing_matches_count=missing_count,
        conflicting_matches_count=conflicting_count,
        missing_must_haves=sorted(list(missing_must_haves)),
        missing_preferred=sorted(list(missing_preferred)),
        supported_skills_count=len(all_matched_skills),
        overall_evidence_score=overall_score,
    )


# Backward compatibility aliases
map_resume_evidence_to_jd_requirements = map_resume_to_jd_evidence
