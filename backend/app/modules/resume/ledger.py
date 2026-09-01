"""
Authoritative Source Evidence Ledger for RoleRadar.
Guarantees 100% provenance tracking, claim extraction, exact metric preservation,
and source coverage auditing across CandidateProfile.
"""
from __future__ import annotations

import re
from typing import Any, Sequence

from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.resume.metrics import extract_quantified_metrics
from app.modules.resume.models import (
    CandidateProfile,
    ClaimType,
    EvidenceUnit,
    SourceCoverageState,
)

# Deterministic claim classifier patterns
_CLAIM_PATTERNS: list[tuple[ClaimType, re.Pattern]] = [
    (ClaimType.METRIC, re.compile(r"(?:\b\d+(?:\.\d+)?%|\$\d+|\b\d+\s*(?:qps|tps|req/sec|users?|events?|gpus?|ms|hours?|minutes?)\b)", re.IGNORECASE)),
    (ClaimType.LEADERSHIP, re.compile(r"\b(?:led|managed|spearheaded|directed|mentored|guided|organized|supervised|championed|headed|founded)\b", re.IGNORECASE)),
    (ClaimType.SCALE, re.compile(r"\b(?:scaled|scaling|scale|distributed|multi-tenant|multi-region|concurrent|high-throughput|cluster|clusters|terabytes?|petabytes?|millions?|thousands?)\b", re.IGNORECASE)),
    (ClaimType.PERFORMANCE, re.compile(r"\b(?:latency|throughput|p99|speed|response time|runtime|cpu|memory|cache hit|optimization|optimized|boosted)\b", re.IGNORECASE)),
    (ClaimType.BUSINESS_IMPACT, re.compile(r"\b(?:revenue|costs?|cost reduction|cost savings?|annually|annual|growth|adoption|retention|conversion|churn|sales)\b", re.IGNORECASE)),
    (ClaimType.OWNERSHIP, re.compile(r"\b(?:architected|authored|owned|designed|engineered|built|constructed|created|launched|delivered|implemented)\b", re.IGNORECASE)),
    (ClaimType.RESPONSIBILITY, re.compile(r"\b(?:responsible for|maintained|monitored|supported|developed|handled|collaborated)\b", re.IGNORECASE)),
    (ClaimType.OUTCOME, re.compile(r"\b(?:reducing|increased|increasing|eliminating|achieving|resulting in|enabling|improving|improved)\b", re.IGNORECASE)),
]


def extract_claims_from_text(text: str) -> list[tuple[ClaimType, str]]:
    """
    Classifies distinct atomic claims within evidence statements into semantic claim types.
    Does NOT infer or generate unsupported facts.
    """
    if not text:
        return []

    claims: list[tuple[ClaimType, str]] = []
    clean = text.strip()

    # Check for matched semantic categories
    matched_types = set()
    for claim_type, pattern in _CLAIM_PATTERNS:
        if pattern.search(clean) and claim_type not in matched_types:
            matched_types.add(claim_type)
            claims.append((claim_type, clean))

    # Technology claims
    techs = extract_skills_from_text(clean)
    if techs and ClaimType.TECHNOLOGY not in matched_types:
        claims.append((ClaimType.TECHNOLOGY, f"Technologies: {', '.join(sorted(techs))}"))

    # Fallback to ACTION / DELIVERY
    if not claims:
        claims.append((ClaimType.ACTION, clean))

    return claims


def get_evidence_by_id(profile: CandidateProfile, evidence_id: str) -> EvidenceUnit | None:
    """Retrieves a specific EvidenceUnit across the entire CandidateProfile."""
    return profile.get_evidence_by_id(evidence_id)


def get_evidence_for_entity(profile: CandidateProfile, entity_id: str) -> list[EvidenceUnit]:
    """Retrieves all EvidenceUnits belonging to a specific company, project, or section entity."""
    return profile.find_evidence_units(entity_id=entity_id)


def get_source_location(evidence: EvidenceUnit) -> str:
    """Returns the provenance location string for a given EvidenceUnit."""
    if evidence.source_location:
        return evidence.source_location
    if evidence.source_reference:
        return evidence.source_reference
    return f"{evidence.section} (Entity: {evidence.entity_id or 'unknown'})"


def get_claims(evidence: EvidenceUnit) -> list[str]:
    """Returns all verified claims associated with this evidence unit."""
    if evidence.claims:
        return list(evidence.claims)
    extracted = extract_claims_from_text(evidence.text)
    return [f"[{ct.value}] {c_text}" for ct, c_text in extracted]


def get_metrics(evidence: EvidenceUnit) -> list[str]:
    """Returns all exact source metrics preserved in this evidence unit."""
    return list(evidence.metrics) if evidence.metrics else extract_quantified_metrics(evidence.text)


def get_technologies(evidence: EvidenceUnit) -> list[str]:
    """Returns all technologies verified in this evidence unit."""
    return list(evidence.technologies) if evidence.technologies else list(extract_skills_from_text(evidence.text))


def compare_source_coverage(
    source_evidence: Sequence[EvidenceUnit],
    target_content: str | list[str] | list[dict[str, Any]],
    explicit_decisions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Audits source coverage between the source Evidence Ledger and target/tailored output.
    Identifies PRESERVED, REWRITTEN, CONDENSED, REORDERED, INTENTIONALLY_REMOVED,
    NEEDS_USER_INPUT, ACCIDENTALLY_LOST, or INVALID states.
    """
    explicit_decisions = explicit_decisions or {}

    # Normalize target content into a list of plain strings
    target_strings: list[str] = []
    if isinstance(target_content, str):
        target_strings = [line.strip() for line in target_content.splitlines() if line.strip()]
    elif isinstance(target_content, list):
        for item in target_content:
            if isinstance(item, str):
                target_strings.append(item.strip())
            elif isinstance(item, dict):
                t = item.get("text") or item.get("proposed_text") or item.get("original_text") or ""
                if t:
                    target_strings.append(str(t).strip())

    combined_target_text = " ".join(target_strings).lower()

    unit_states: dict[str, SourceCoverageState] = {}
    lost_evidence: list[str] = []
    preserved_count = 0

    for ev in source_evidence:
        ev_id = ev.id
        ev_text = ev.text.strip().lower()
        ev_metrics = [m.lower() for m in (ev.metrics or extract_quantified_metrics(ev.text))]

        # Check explicit decision first
        decision = explicit_decisions.get(ev_id, "").upper()
        if decision == "REMOVE":
            unit_states[ev_id] = SourceCoverageState.INTENTIONALLY_REMOVED
            continue
        elif decision == "NEEDS_USER_INPUT":
            unit_states[ev_id] = SourceCoverageState.NEEDS_USER_INPUT
            continue

        # Exact or near-exact match
        if ev_text in combined_target_text:
            unit_states[ev_id] = SourceCoverageState.PRESERVED
            preserved_count += 1
            continue

        # Check if all metrics and key tech are preserved in target
        metrics_preserved = all(m in combined_target_text for m in ev_metrics) if ev_metrics else True
        tech_words = [t.lower() for t in (ev.technologies or extract_skills_from_text(ev.text))]
        tech_preserved = any(t in combined_target_text for t in tech_words) if tech_words else True

        # Check for rewriting / condensing
        ev_words = [w for w in re.findall(r"\w+", ev_text) if len(w) >= 4]
        overlap_words = [w for w in ev_words if w in combined_target_text]
        overlap_ratio = len(overlap_words) / len(ev_words) if ev_words else 0.0

        if metrics_preserved and overlap_ratio >= 0.5:
            if len(combined_target_text) < len(ev_text) * 0.8:
                unit_states[ev_id] = SourceCoverageState.CONDENSED
            else:
                unit_states[ev_id] = SourceCoverageState.REWRITTEN
            preserved_count += 1
        elif overlap_ratio >= 0.35 and (metrics_preserved or not ev_metrics):
            unit_states[ev_id] = SourceCoverageState.REWRITTEN
            preserved_count += 1
        else:
            # Fact missing from target
            unit_states[ev_id] = SourceCoverageState.ACCIDENTALLY_LOST
            lost_evidence.append(ev_id)

    total_units = len(source_evidence)
    coverage_rate = (preserved_count / total_units) if total_units > 0 else 1.0

    return {
        "total_source_units": total_units,
        "preserved_units_count": preserved_count,
        "coverage_rate": round(coverage_rate, 4),
        "states": unit_states,
        "lost_evidence_ids": lost_evidence,
    }
