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
    {"python", "flask", "fastapi", "django", "tornado", "backend", "rest apis", "restful api design", "api"},
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


NEGATION_ASPIRATIONAL_PATTERNS = [
    r"\bno\s+(?:prior\s+|hands-on\s+|commercial\s+|professional\s+)?experience\s+(?:in|with|using)\b",
    r"\bnot\s+(?:familiar\s+with|experienced\s+in|proficient\s+in)\b",
    r"\bnever\s+(?:used|worked\s+with|developed\s+in)\b",
    r"\bwithout\s+(?:any\s+)?experience\s+in\b",
    r"\binterested\s+in\s+(?:learning|exploring|working\s+with)\b",
    r"\baspiring\s+to\s+(?:learn|work\s+with)\b",
    r"\blooking\s+to\s+(?:learn|gain\s+experience\s+in)\b",
    r"\bwant(?:s)?\s+to\s+learn\b",
    r"\bhope(?:s)?\s+to\s+gain\s+experience\b",
    r"\bheard\s+about\b",
    r"\bread\s+about\b",
    r"\btheory\s+only\b",
]


def _is_negative_or_aspirational(text: str, skill: str) -> bool:
    text_lower = text.lower()
    skill_lower = skill.lower()
    if skill_lower not in text_lower:
        return False
    for pat in NEGATION_ASPIRATIONAL_PATTERNS:
        match = re.search(pat, text_lower)
        if match:
            start, end = match.span()
            idx = text_lower.find(skill_lower)
            if abs(idx - start) < 60 or abs(idx - end) < 60:
                return True
    return False


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


def _compute_candidate_experience_years(profile: CandidateProfile) -> int:
    """Estimates or extracts candidate total experience years from profile attributes, summary, or experience entries."""
    if hasattr(profile, "experience_years") and isinstance(profile.experience_years, (int, float)):
        return int(profile.experience_years)
    if isinstance(profile.personal, dict) and profile.personal.get("experience_years"):
        try:
            return int(profile.personal["experience_years"])
        except (ValueError, TypeError):
            pass

    text_corpus = (profile.summary or "") + " " + " ".join(ev.normalized_text for ev in profile.evidence_units)
    year_match = re.search(r"\b(\d+)\+?\s*(?:years?|yrs?)\b", text_corpus, re.IGNORECASE)
    if year_match:
        return int(year_match.group(1))

    if profile.experience:
        return max(len(profile.experience), 1)
    return 0


def map_resume_to_jd_evidence(
    profile: CandidateProfile,
    job_reqs: StructuredJobRequirements,
) -> EvidenceJDMap:
    """
    Maps candidate evidence units against structured job requirements deterministically.
    Never inflates semantic similarity. Strictly distinguishes EXACT, STRONG, SUPPORTED,
    RELATED, PARTIAL, WEAK, MISSING, and CONFLICTING match levels.
    """
    # Build candidate skills set excluding negative/aspirational mentions
    candidate_skills_lower: set[str] = set()
    for s in profile.skills:
        s_low = s.lower()
        matching_evs = [
            ev for ev in profile.evidence_units
            if s_low in ev.normalized_text.lower() or s_low in {t.lower() for t in ev.technologies}
        ]
        if matching_evs and all(_is_negative_or_aspirational(ev.normalized_text, s) for ev in matching_evs):
            continue  # Exclude negated/aspirational mention
        candidate_skills_lower.add(s_low)

    for ev in profile.evidence_units:
        for t in ev.technologies:
            if not _is_negative_or_aspirational(ev.normalized_text, t):
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
            # 2. Exact, Synonym, and Compound Skill Matching
            detected_skills = req.skills_detected or []
            exact_found = [s for s in detected_skills if s.lower() in candidate_skills_lower]
            synonym_found: list[str] = []
            for s in detected_skills:
                if s not in exact_found:
                    syn = _check_synonym_match(s, candidate_skills_lower)
                    if syn:
                        synonym_found.append(syn)

            total_detected = len(detected_skills)
            total_matched = len(exact_found) + len(synonym_found)

            # Check if requirement contains alternatives (e.g. "AWS or Azure", "Rust / C++")
            is_alternative_req = bool(re.search(r"\b(?:or|either)\b", req_lower) or "/" in req_lower)

            # Check if this requirement is primarily an experience tenure requirement without specific tools
            is_pure_tenure_req = bool(
                re.search(r"\b(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)\b", req_lower)
                and any(w in req_lower for w in ["experience", "background", "tenure", "software development", "engineering"])
                and not detected_skills
            )

            if total_matched > 0 and not is_pure_tenure_req:
                matched_target_skills = exact_found + synonym_found
                matched_skills.extend(matched_target_skills)
                all_matched_skills.update(matched_target_skills)

                # Locate supporting EvidenceUnits (excluding negative mentions)
                for ev in profile.evidence_units:
                    ev_techs_lower = {t.lower() for t in ev.technologies}
                    for s in matched_target_skills:
                        s_low = s.lower()
                        if (s_low in ev_techs_lower or s_low in ev.normalized_text.lower()) and not _is_negative_or_aspirational(ev.normalized_text, s):
                            if ev not in matched_evs:
                                matched_evs.append(ev)
                                if ev.entity_id and ev.entity_id not in matched_entities:
                                    matched_entities.append(ev.entity_id)

                # Check if evidence contains demonstrated experience/project delivery vs academic/listing
                has_delivery_evidence = any(
                    ev.section in ("EXPERIENCE", "PROJECTS")
                    or (hasattr(ev.claim_type, "value") and ev.claim_type.value in ("CORE_EXPERIENCE", "PROJECT_CONTRIBUTION"))
                    for ev in matched_evs
                )
                has_education_only = bool(matched_evs) and all(
                    ev.section == "EDUCATION" or (hasattr(ev.claim_type, "value") and ev.claim_type.value == "ACADEMIC_CREDENTIAL")
                    for ev in matched_evs
                )

                if total_detected > 1 and total_matched < total_detected and not is_alternative_req:
                    # Compound 'AND' Requirement with Partial Coverage
                    status = EvidenceMatchStatus.PARTIAL
                    score = round(0.40 + 0.45 * (total_matched / total_detected), 2)
                    partial_count += 1
                    missing_sub = [s for s in detected_skills if s not in exact_found and s not in synonym_found]
                    reason = f"Partial compound match: {total_matched}/{total_detected} skills supported ({', '.join(matched_target_skills)}); missing ({', '.join(missing_sub)})."
                    unmatched_gaps.append(f"{req.text} (Missing: {', '.join(missing_sub)})")
                    if req.category == RequirementCategory.MUST_HAVE:
                        missing_must_haves.update(missing_sub)
                    elif req.category == RequirementCategory.PREFERRED:
                        missing_preferred.update(missing_sub)
                elif exact_found and (len(exact_found) == total_detected or is_alternative_req):
                    # Complete Exact Match (or Alternative Satisfied)
                    if has_delivery_evidence:
                        status = EvidenceMatchStatus.EXACT_MATCH
                        score = 1.0
                        exact_count += 1
                        reason = f"Exact skill match verified with {len(matched_evs)} delivery evidence units ({', '.join(matched_entities)})."
                    elif has_education_only:
                        status = EvidenceMatchStatus.SUPPORTED
                        score = 0.80
                        supported_count += 1
                        reason = f"Supported by academic coursework/education credentials ({', '.join(matched_skills)})."
                    else:
                        status = EvidenceMatchStatus.SUPPORTED
                        score = 0.85
                        supported_count += 1
                        reason = f"Skill listed in profile qualifications ({', '.join(matched_skills)})."
                else:
                    # Synonym or Full Mixed Match -> STRONG_MATCH
                    status = EvidenceMatchStatus.STRONG_MATCH
                    score = 0.95
                    strong_count += 1
                    reason = f"Strong match supported by candidate qualifications ({', '.join(matched_target_skills)})."

            elif is_pure_tenure_req:
                # 3. Experience Duration Requirement Check
                exp_match = re.search(r"\b(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)\b", req_lower)
                req_years = int(exp_match.group(1)) if exp_match else 1
                candidate_years = _compute_candidate_experience_years(profile)

                if candidate_years >= req_years:
                    status = EvidenceMatchStatus.EXACT_MATCH
                    score = 1.0
                    exact_count += 1
                    reason = f"Experience requirement satisfied: candidate has {candidate_years}+ years experience (required: {req_years}+ years)."
                elif candidate_years >= req_years * 0.5:
                    status = EvidenceMatchStatus.PARTIAL
                    score = 0.60
                    partial_count += 1
                    reason = f"Partial experience: candidate has {candidate_years} years (required: {req_years}+ years)."
                else:
                    status = EvidenceMatchStatus.WEAK if candidate_years > 0 else EvidenceMatchStatus.MISSING
                    score = 0.30 if candidate_years > 0 else 0.0
                    if candidate_years > 0:
                        weak_count += 1
                    else:
                        missing_count += 1
                        unmatched_gaps.append(req.text)
                    reason = f"Insufficient experience tenure: candidate has {candidate_years} years (required: {req_years}+ years)."

            elif req.category == RequirementCategory.RESPONSIBILITY:
                # 4. Responsibility Support Check
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
                # 5. Related (Adjacent) Skills Check -> RELATED
                related_candidates: set[str] = set()
                for s in (req.skills_detected or []):
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
                    # 6. Semantic / Partial Keyword Overlap -> PARTIAL / WEAK / MISSING
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
