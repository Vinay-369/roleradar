"""
Canonical Job and Internship Description Presentation Normalizer.

Transforms raw ATS description text into clean, structured presentation sections:
- summary (Job Summary / Overview)
- responsibilities (Core Responsibilities)
- qualifications (Qualifications & Educational Requirements)
- additional_info (Additional Information / Logistics / Perks)
- detailed_sections (Remaining unique contextual narrative)

Removes redundant headings (repeated JOB DESCRIPTION, QUALIFICATIONS, etc.),
strips inline headings and colons, and avoids repeating content that already
exists in canonical cards.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

FORBIDDEN_METADATA_PATTERNS = [
    re.compile(
        r"^\s*(?:tariff\s*area|legal\s*entity(?:\s*\(acronym\))?|global\s*salary(?:\s*level)?|division(?:\s*full\s*name|\s*identifiers)?|local\s*grade|cost\s*center|entity\s*acronym|direct\s*or\s*indirect|working\s*(?:location|country|hours)|position\s*type|brands)\s*[:\-].*$",
        re.IGNORECASE,
    )
]

HEADING_PATTERNS = [
    (
        "overview",
        re.compile(
            r"^(?:company\s*description|about\s*(?:the\s*)?company|about\s*us|who\s*we\s*are|who\s*are\s*we|the\s*opportunity|role\s*overview|job\s*summary|overview|about\s*the\s*role|summary)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ),
    (
        "responsibilities",
        re.compile(
            r"^(?:job\s*description|role\s*description|what\s*you(?:'ll|’ll|\s*will)\s*do|key\s*responsibilities|responsibilities|tasks\s*(?:\/|and)\s*responsibilities|duties|roles?\s*and\s*responsibilities)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ),
    (
        "requirements",
        re.compile(
            r"^(?:requirements|must\s*have(?:\s*qualifications)?|required\s*skills(?:\s*set)?|expected\s*skill\s*set|expected\s*skills|technical\s*skillset|key\s*skills|what\s*you(?:'ll|’ll|\s*will)\s*need|minimum\s*qualifications|basic\s*qualifications)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ),
    (
        "preferred",
        re.compile(
            r"^(?:preferred\s*qualifications|nice[- ]to[- ]have|good\s*to\s*have|bonus\s*points|desired\s*skills|preferred\s*skills|plus)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ),
    (
        "qualifications",
        re.compile(
            r"^(?:qualifications?|educational\s*requirements?|education(?:\s*and\s*experience)?|eligibility)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ),
    (
        "additional",
        re.compile(
            r"^(?:additional\s*information(?:\s*\/\s*experience)?|what\s*else\??|benefits|perks|working\s*conditions|other\s*skills|our\s*values|equal\s*opportunity|eeo\s*statement)\s*[:\-]?$",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class NormalizedItem:
    is_bullet: bool
    text: str


@dataclass
class NormalizedSection:
    title: str | None
    items: list[NormalizedItem] = field(default_factory=list)


@dataclass
class JobPresentationResult:
    summary: NormalizedSection | None
    responsibilities: list[str]
    qualifications: list[str]
    additional_info: NormalizedSection | None
    detailed_sections: list[NormalizedSection]


def clean_raw_description(raw: str) -> str:
    if not raw:
        return ""
    text = (
        raw.replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#xa0;", " ")
        .replace("&nbsp;", " ")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    # Convert HTML bold/headings into markdown
    text = re.sub(r"<(?:h[1-4]|b|strong)>(.*?)</(?:h[1-4]|b|strong)>", r"\n\1:\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    # Convert bullet and separator artifacts
    text = re.sub(r"[\s\xa0]*[\u00d8\ufffd•][\s\xa0]*", "\n- ", text)
    text = re.sub(r"[\u00b7·]", "\n- ", text)

    lines = [line for line in text.split("\n") if not any(pat.match(line) for pat in FORBIDDEN_METADATA_PATTERNS)]
    return "\n".join(lines).strip()


def _normalize_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _match_category(line: str) -> str | None:
    clean = re.sub(r"^#+\s*", "", line).strip()
    clean = re.sub(r"[:\-]+$", "", clean).strip()
    if not clean or len(clean) > 70:
        return None
    for category, pat in HEADING_PATTERNS:
        if pat.match(clean):
            return category
    return None


def normalize_job_description_presentation(
    description: str,
    responsibilities: list[str] | None = None,
    qualifications: list[str] | None = None,
    skills_required: list[str] | None = None,
    skills_nice_to_have: list[str] | None = None,
) -> JobPresentationResult:
    resps = list(responsibilities or [])
    quals = list(qualifications or [])
    skills_req = list(skills_required or [])
    skills_pref = list(skills_nice_to_have or [])

    cleaned = clean_raw_description(description)
    if not cleaned:
        return JobPresentationResult(
            summary=None,
            responsibilities=[r for r in resps if r],
            qualifications=[q for q in quals if q],
            additional_info=None,
            detailed_sections=[],
        )

    resp_set = {_normalize_key(r) for r in resps if r}
    qual_set = {_normalize_key(q) for q in quals if q}
    skill_set = {_normalize_key(s) for s in (skills_req + skills_pref) if s}

    # Pre-process inline headings so they start on separate lines
    subheading_regex = re.compile(
        r"(?:\r?\n|^|\.\s+)(Expected skill set|Tasks\s*\/\s*Responsibilities|Good to have|Job Description|Qualifications|Required skills|Key skills)\s*:\s*",
        re.IGNORECASE,
    )
    text_with_subheadings = subheading_regex.sub(r"\n\n\1:\n", cleaned)

    lines = [line.strip() for line in text_with_subheadings.split("\n") if line.strip()]

    @dataclass
    class RawSection:
        category: str
        title: str
        items: list[NormalizedItem] = field(default_factory=list)

    sections: list[RawSection] = []
    current_sec = RawSection(category="other", title="")

    for line in lines:
        is_md_heading = line.startswith("#")
        detected_cat = _match_category(line)

        if is_md_heading or detected_cat:
            if current_sec.items or current_sec.title:
                sections.append(current_sec)
            title_clean = re.sub(r"^#+\s*", "", line).strip()
            title_clean = re.sub(r"[:\-]+$", "", title_clean).strip()
            current_sec = RawSection(category=detected_cat or "other", title=title_clean)
            continue

        # Check for inline redundant headings within a section
        inline_cat = _match_category(line)
        if inline_cat and len(line) < 50 and "." not in line:
            if inline_cat == current_sec.category or inline_cat in ("responsibilities", "qualifications"):
                continue

        is_bullet = line.startswith("- ") or line.startswith("* ") or line.startswith("• ")
        text_clean = re.sub(r"^[-*•]\s+", "", line).strip()
        if text_clean:
            current_sec.items.append(NormalizedItem(is_bullet=is_bullet, text=text_clean))

    if current_sec.items or current_sec.title:
        sections.append(current_sec)

    summary_sec: NormalizedSection | None = None
    additional_sec: NormalizedSection | None = None
    detailed_sections: list[NormalizedSection] = []

    final_resps = list(resps)
    final_quals = list(quals)

    for sec in sections:
        if sec.category == "overview":
            if summary_sec is None and sec.items:
                summary_sec = NormalizedSection(title="Job Summary", items=sec.items)
            elif sec.items:
                detailed_sections.append(NormalizedSection(title="Role Overview", items=sec.items))
            continue

        if sec.category == "responsibilities":
            for item in sec.items:
                norm_k = _normalize_key(item.text)
                if not norm_k:
                    continue
                # If item is role logistics/metadata (e.g. "Location: ...", "Job position: ..."), route to additional_info
                if re.match(r"^(?:job\s*position|location|department|experience|employment\s*type|contract\s*type)\s*[:\-].*", item.text.strip(), re.IGNORECASE):
                    if additional_sec is None:
                        additional_sec = NormalizedSection(title="Additional Information", items=[item])
                    else:
                        additional_sec.items.append(item)
                    continue

                # If bullet or concise responsibility description, merge into canonical responsibilities
                if item.is_bullet or len(item.text.split()) < 35:
                    if norm_k not in resp_set:
                        final_resps.append(item.text)
                        resp_set.add(norm_k)
                else:
                    # Longer narrative prose inside a responsibilities block goes to detailed sections without "Job Description" title
                    if norm_k not in resp_set:
                        detailed_sections.append(NormalizedSection(title="Role Context", items=[item]))
            continue

        if sec.category == "qualifications":
            for item in sec.items:
                norm_k = _normalize_key(item.text)
                if not norm_k:
                    continue
                if item.is_bullet or len(item.text.split()) < 35:
                    if norm_k not in qual_set:
                        final_quals.append(item.text)
                        qual_set.add(norm_k)
                else:
                    if norm_k not in qual_set:
                        detailed_sections.append(NormalizedSection(title="Qualifications Context", items=[item]))
            continue

        if sec.category in ("requirements", "preferred"):
            unique_items = [i for i in sec.items if _normalize_key(i.text) not in skill_set]
            non_chip_items = [i for i in unique_items if len(i.text.split()) > 4 or _normalize_key(i.text) not in skill_set]
            if non_chip_items:
                title = "Preferred Profile Details" if sec.category == "preferred" else "Requirement Details"
                detailed_sections.append(NormalizedSection(title=title, items=non_chip_items))
            continue

        if sec.category == "additional":
            if additional_sec is None and sec.items:
                additional_sec = NormalizedSection(title="Additional Information", items=sec.items)
            elif sec.items and additional_sec is not None:
                additional_sec.items.extend(sec.items)
            continue

        if sec.items:
            title_lower = (sec.title or "").lower().strip()
            is_redundant_heading = any(
                title_lower == h or title_lower.startswith(h + ":")
                for h in (
                    "job description",
                    "role description",
                    "qualifications",
                    "qualification",
                    "requirements",
                    "details",
                    "additional information",
                )
            )
            clean_title = None if is_redundant_heading else sec.title
            detailed_sections.append(NormalizedSection(title=clean_title, items=sec.items))

    # Deduplicate consecutive detailed sections with identical title
    final_detailed: list[NormalizedSection] = []
    for ds in detailed_sections:
        if not ds.items:
            continue
        if final_detailed and final_detailed[-1].title and ds.title and final_detailed[-1].title.lower() == ds.title.lower():
            final_detailed[-1].items.extend(ds.items)
        else:
            final_detailed.append(ds)

    return JobPresentationResult(
        summary=summary_sec if (summary_sec and summary_sec.items) else None,
        responsibilities=final_resps,
        qualifications=final_quals,
        additional_info=additional_sec if (additional_sec and additional_sec.items) else None,
        detailed_sections=final_detailed,
    )
