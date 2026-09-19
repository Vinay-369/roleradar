"""
Authoritative Compensation & Stipend Extraction Engine.

Extracts candidate compensation from:
1. Structured ATS fields (Lever salaryRange, Greenhouse pay, SmartRecruiters customField)
2. Job description text and requisition sections

Strictly enforces:
- Truthful recovery of employer-provided numeric salary (LPA, annual INR) and stipends.
- Qualitative compensation recognition ("Competitive compensation", "Best in industry salary").
- False-positive protection against company sales/revenues, loan products, and experience years.
- Zero fabrication: If undisclosed, leaves values as None and marks UNDISCLOSED.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

# False-positive filters: candidate salary must NEVER match company financials, budgets, customer data, loans, or experience
FALSE_POSITIVE_PATTERNS = [
    re.compile(r"\b(?:sales\s*of|revenue\s*of|turnover|crores?|billion|billions?|million|millions?)\b", re.I),
    re.compile(r"\b(?:offerings?\s*ranging\s*from|loans?|credit\s*lines?|credit\s*limits?|transaction\s*volume|borrowers?|lending|disburs\w*)\b", re.I),
    re.compile(r"\b(?:years?|yrs?|months?)\s*(?:of\s*)?(?:experience|exp)\b", re.I),
    re.compile(r"\b(?:active\s*members?|transacting\s*members?|subscribers?|users?|customers?)\b", re.I),
    re.compile(r"\b(?:project\s*budget|equipment\s*budget|procurement\s*budget|marketing\s*budget|ad\s*spend|tooling\s*budget)\b", re.I),
    re.compile(r"\b(?:contract\s*value|deal\s*size|contract\s*worth|portfolio\s*value)\b", re.I),
    re.compile(r"\b(?:customer\s*salaries|client\s*salaries|process(?:ing)?\s+payroll\s+for)\b", re.I),
    re.compile(r"\b(?:series\s*[a-g]|funding\s*of|raised\s*(?:\$|€|₹)?\d+)\b", re.I),
]

# Internship-specific paid/unpaid patterns
INTERNSHIP_QUALITATIVE_PATTERNS = [
    (re.compile(r"\b(?:paid\s+internship|remunerated\s+internship|stipend\s+provided)\b", re.I), "Paid internship"),
    (re.compile(r"\b(?:unpaid\s+internship|voluntary\s+internship|no\s+stipend)\b", re.I), "Unpaid internship"),
]

# Strict numeric salary patterns for Indian context
NUMERIC_LPA_RANGE_RE = re.compile(
    r"(?:(?:₹|INR|Rs\.?)\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|to)\s*(?:(?:₹|INR|Rs\.?)\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:lpa|lacs?|lakhs?|per\s*annum|p\.?a\.?)\b",
    re.I,
)
NUMERIC_LPA_SINGLE_RE = re.compile(
    r"(?:(?:₹|INR|Rs\.?)\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:lpa|per\s*annum|p\.?a\.?)\b",
    re.I,
)
NUMERIC_LAKHS_SINGLE_RE = re.compile(
    r"(?:(?:₹|INR|Rs\.?)\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:lacs?|lakhs?)\b",
    re.I,
)
NUMERIC_INR_FULL_RANGE_RE = re.compile(
    r"(?:₹|INR|Rs\.?)\s*([0-9][0-9,]{4,})\s*(?:-|–|to)\s*(?:(?:₹|INR|Rs\.?)\s*)?([0-9][0-9,]{4,})\b",
    re.I,
)
NUMERIC_STIPEND_RE = re.compile(
    r"(?:(?:stipend|salary)\s*[:\-]?\s*)?(?:₹|INR|Rs\.?)\s*([0-9][0-9,]{3,})\s*(?:/|\s*per\s*)?(?:month|pm|mo)\b",
    re.I,
)

# Qualitative compensation phrases
QUALITATIVE_PATTERNS = [
    (re.compile(r"\b(?:best\s*in\s*industry|best\s*in\s*class)\s+(?:salary|compensation|package|pay)\b", re.I), "Best in industry salary"),
    (re.compile(r"\b(?:competitive|attractive|market\s*standard|industry\s*standard)\s+(?:salary|compensation|package|remuneration|stipend)\b", re.I), "Competitive compensation disclosed by employer"),
    (re.compile(r"\b(?:salary|compensation|remuneration)\s*[:\-]?\s*(?:is\s*)?(?:competitive|attractive|best\s*in\s*industry|negotiable|as\s*per\s*market)\b", re.I), "Competitive compensation disclosed by employer"),
    (re.compile(r"\bcommensurate\s+with\s+(?:experience|skills|market)\b", re.I), "Compensation commensurate with experience"),
]


@dataclass
class CompensationDetails:
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = "INR"
    salary_disclosed: bool = False
    stipend_min: float | None = None
    stipend_max: float | None = None
    compensation_type: str = "UNDISCLOSED"  # "NUMERIC" | "QUALITATIVE" | "UNDISCLOSED"
    compensation_text: str | None = None


def extract_compensation_from_payload_and_text(
    text: str | None = None,
    raw_payload: dict[str, Any] | None = None,
    is_internship: bool = False,
) -> CompensationDetails:
    """
    Extracts compensation details combining structured ATS payload and text inspection.
    """
    result = CompensationDetails()
    payload = raw_payload or {}

    # 1. Structured ATS fields inspection
    # Lever: salaryRange = {'min': ..., 'max': ..., 'currency': 'INR'}
    s_range = payload.get("salaryRange")
    if isinstance(s_range, dict):
        min_val = s_range.get("min")
        max_val = s_range.get("max")
        curr = s_range.get("currency") or "INR"
        # Only accept if values are non-zero numbers
        if isinstance(min_val, (int, float)) and min_val > 0:
            result.salary_min = min_val / 100000.0 if min_val > 1000 else float(min_val)
            result.salary_disclosed = True
            result.salary_currency = curr
            result.compensation_type = "NUMERIC"
        if isinstance(max_val, (int, float)) and max_val > 0:
            result.salary_max = max_val / 100000.0 if max_val > 1000 else float(max_val)
            result.salary_disclosed = True
            result.salary_currency = curr
            result.compensation_type = "NUMERIC"

    # Greenhouse: pay = {'min_value': ..., 'max_value': ..., 'unit': ...}
    pay_obj = payload.get("pay")
    if isinstance(pay_obj, dict):
        min_val = pay_obj.get("min_value")
        max_val = pay_obj.get("max_value")
        if isinstance(min_val, (int, float)) and min_val > 0:
            result.salary_min = min_val / 100000.0 if min_val > 1000 else float(min_val)
            result.salary_disclosed = True
            result.compensation_type = "NUMERIC"
        if isinstance(max_val, (int, float)) and max_val > 0:
            result.salary_max = max_val / 100000.0 if max_val > 1000 else float(max_val)
            result.salary_disclosed = True
            result.compensation_type = "NUMERIC"

<<<<<<< HEAD
=======
    # Ashby: compensation = {'summaryComponents': [{'compensationType': 'Salary', 'minValue': ..., 'maxValue': ..., 'currencyCode': 'INR'}]}
    ashby_comp = payload.get("compensation")
    if isinstance(ashby_comp, dict):
        components = ashby_comp.get("summaryComponents") or []
        for comp in components:
            if isinstance(comp, dict) and comp.get("compensationType") == "Salary":
                c_curr = comp.get("currencyCode")
                c_min = comp.get("minValue")
                c_max = comp.get("maxValue")
                if isinstance(c_min, (int, float)) and c_min > 0:
                    result.salary_min = c_min / 100000.0 if (c_min > 1000 and c_curr == "INR") else float(c_min)
                    result.salary_disclosed = True
                    result.salary_currency = c_curr or result.salary_currency
                    result.compensation_type = "NUMERIC"
                if isinstance(c_max, (int, float)) and c_max > 0:
                    result.salary_max = c_max / 100000.0 if (c_max > 1000 and c_curr == "INR") else float(c_max)
                    result.salary_disclosed = True
                    result.salary_currency = c_curr or result.salary_currency
                    result.compensation_type = "NUMERIC"
                tier_summary = ashby_comp.get("scrapeableCompensationSalarySummary") or ashby_comp.get("compensationTierSummary")
                if tier_summary and isinstance(tier_summary, str):
                    result.compensation_text = tier_summary.strip()
                break

>>>>>>> 1161debb0d86395e8540a9a7b4d6f96f1278b97b
    # If structured numeric compensation already found, format text and return
    if result.compensation_type == "NUMERIC":
        if result.salary_min and result.salary_max:
            result.compensation_text = f"₹{result.salary_min}–{result.salary_max} LPA"
        elif result.salary_min:
            result.compensation_text = f"₹{result.salary_min} LPA"
        return result

    if not text:
        return result

    # 2. Text-based Numeric Extraction
    CONTEXT_WINDOW = 160

    # Check for Stipend first if internship or stipend keyword present
    stipend_m = NUMERIC_STIPEND_RE.search(text)
    if stipend_m:
        raw_context = text[max(0, stipend_m.start() - CONTEXT_WINDOW):min(len(text), stipend_m.end() + CONTEXT_WINDOW)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            val_str = stipend_m.group(1).replace(",", "")
            try:
                stip_val = float(val_str)
                if 2000 <= stip_val <= 200000:
                    result.stipend_min = stip_val
                    result.salary_disclosed = True
                    result.compensation_type = "NUMERIC"
                    result.compensation_text = f"₹{stip_val:,.0f}/month"
                    return result
            except ValueError:
                pass

    # Check for LPA range (e.g., ₹8–12 LPA or 6 to 9 LPA)
    lpa_range_m = NUMERIC_LPA_RANGE_RE.search(text)
    if lpa_range_m:
        raw_context = text[max(0, lpa_range_m.start() - CONTEXT_WINDOW):min(len(text), lpa_range_m.end() + CONTEXT_WINDOW)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                s_min = float(lpa_range_m.group(1))
                s_max = float(lpa_range_m.group(2))
                if 1.0 <= s_min <= 150.0 and 1.0 <= s_max <= 200.0:
                    result.salary_min = s_min
                    result.salary_max = s_max
                    result.salary_disclosed = True
                    result.compensation_type = "NUMERIC"
                    result.compensation_text = f"₹{s_min}–{s_max} LPA"
                    return result
            except ValueError:
                pass

    # Check for full INR range (e.g., INR 600000 to 1000000)
    inr_range_m = NUMERIC_INR_FULL_RANGE_RE.search(text)
    if inr_range_m:
        raw_context = text[max(0, inr_range_m.start() - CONTEXT_WINDOW):min(len(text), inr_range_m.end() + CONTEXT_WINDOW)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                s_min = float(inr_range_m.group(1).replace(",", "")) / 100000.0
                s_max = float(inr_range_m.group(2).replace(",", "")) / 100000.0
                if 1.0 <= s_min <= 150.0 and 1.0 <= s_max <= 200.0:
                    result.salary_min = s_min
                    result.salary_max = s_max
                    result.salary_disclosed = True
                    result.compensation_type = "NUMERIC"
                    result.compensation_text = f"₹{s_min:g}–{s_max:g} LPA"
                    return result
            except ValueError:
                pass

    # Check for single LPA (e.g., 10 LPA)
    lpa_single_m = NUMERIC_LPA_SINGLE_RE.search(text)
    if lpa_single_m:
        raw_context = text[max(0, lpa_single_m.start() - CONTEXT_WINDOW):min(len(text), lpa_single_m.end() + CONTEXT_WINDOW)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                s_val = float(lpa_single_m.group(1))
                if 1.0 <= s_val <= 150.0:
                    result.salary_min = s_val
                    result.salary_disclosed = True
                    result.compensation_type = "NUMERIC"
                    result.compensation_text = f"₹{s_val} LPA"
                    return result
            except ValueError:
                pass

    # Check for single Lakhs with explicit salary context
    lakhs_single_m = NUMERIC_LAKHS_SINGLE_RE.search(text)
    if lakhs_single_m:
        raw_context = text[max(0, lakhs_single_m.start() - CONTEXT_WINDOW):min(len(text), lakhs_single_m.end() + CONTEXT_WINDOW)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            if re.search(r"\b(?:salary|ctc|compensation|remuneration|package|pay)\b", raw_context, re.I):
                try:
                    s_val = float(lakhs_single_m.group(1))
                    if 1.0 <= s_val <= 150.0:
                        result.salary_min = s_val
                        result.salary_disclosed = True
                        result.compensation_type = "NUMERIC"
                        result.compensation_text = f"₹{s_val} Lakhs"
                        return result
                except ValueError:
                    pass

    # 3. Internship-specific qualitative statements (paid/unpaid)
    if is_internship or "intern" in (text[:200].lower()):
        for pat, label in INTERNSHIP_QUALITATIVE_PATTERNS:
            m = pat.search(text)
            if m:
                raw_context = text[max(0, m.start() - CONTEXT_WINDOW):min(len(text), m.end() + CONTEXT_WINDOW)]
                if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
                    result.compensation_text = label
                    result.salary_disclosed = True
                    result.compensation_type = "QUALITATIVE"
                    return result

    # 4. General Qualitative Compensation Recognition
    for pat, label in QUALITATIVE_PATTERNS:
        m = pat.search(text)
        if m:
            raw_context = text[max(0, m.start() - CONTEXT_WINDOW):min(len(text), m.end() + CONTEXT_WINDOW)]
            if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
                # Preserve the exact phrase if it is "Best in industry salary"
                matched_phrase = m.group(0).strip()
                if "best in industry" in matched_phrase.lower():
                    result.compensation_text = "Best in industry salary"
                elif "commensurate" in matched_phrase.lower():
                    result.compensation_text = "Compensation commensurate with experience"
                else:
                    result.compensation_text = "Competitive compensation disclosed by employer"
                result.salary_disclosed = True
                result.compensation_type = "QUALITATIVE"
                return result

    return result
