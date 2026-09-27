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
    r"(?:(?:₹|INR|Rs\.?)\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|to)\s*(?:(?:₹|INR|Rs\.?)\s*)?([0-9]+(?:\.[0-9]+)?)\s*(lpa|lacs?|lakhs?(?:\s+per\s+annum)?|per\s*annum|p\.?a\.?)\b",
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
    r"\b(?:monthly\s+)?stipend\s*(?:of\s*)?[:\-]?\s*(₹|INR|Rs\.?|\$|USD|€|EUR|£|GBP)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:/|\s*per\s*)?(month|pm|mo)\b",
    re.I,
)
NUMERIC_STIPEND_SUFFIX_RE = re.compile(
    r"(?P<currency>₹|INR|Rs\.?|\$|USD|€|EUR|£|GBP)\s*(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:/|\s*per\s*)(?P<period>month|pm|mo)\s+stipend\b",
    re.I,
)
NUMERIC_STIPEND_RANGE_RE = re.compile(
    r"\bstipend\s*(?:of\s*)?[:\-]?\s*(₹|INR|Rs\.?|\$|USD|€|EUR|£|GBP)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:-|–|to)\s*(₹|INR|Rs\.?|\$|USD|€|EUR|£|GBP)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:/|\s*per\s*)?(month|pm|mo)\b",
    re.I,
)
NUMERIC_CURRENCY_RANGE_RE = re.compile(
    r"(?P<currency>₹|INR|Rs\.?|\$|USD|€|EUR|£|GBP)\s*(?P<min>[0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:-|–|to)\s*(?:(?P<currency_max>₹|INR|Rs\.?|\$|USD|€|EUR|£|GBP)\s*)?(?P<max>[0-9][0-9,]*(?:\.[0-9]+)?)(?:\s*(?P<currency_suffix>INR|USD|EUR|GBP))?(?:\s*/?\s*(?P<period>per\s+year|yearly|annually|annual|per\s+month|monthly|per\s+hour|hourly|per\s+week|weekly|year|month|hour|week))?\b",
    re.I,
)
NUMERIC_CURRENCY_SINGLE_RE = re.compile(
    r"(?P<currency>₹|INR|Rs\.?|\$|USD|€|EUR|£|GBP)\s*(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)(?:\s*(?P<period>per\s+year|yearly|annually|annual|per\s+month|monthly|per\s+hour|hourly|per\s+week|weekly))?\b",
    re.I,
)
NUMERIC_LAKH_RANGE_RE = re.compile(
    r"(?:(?P<currency>₹|INR|Rs\.?)\s*)?(?P<min>[0-9]+(?:\.[0-9]+)?)\s*L(?P<unit_min>PA)?\s*(?:-|–|to)\s*(?:(?P<currency_max>₹|INR|Rs\.?)\s*)?(?P<max>[0-9]+(?:\.[0-9]+)?)\s*L(?P<unit_max>PA)?\b",
    re.I,
)
NUMERIC_LAKH_SINGLE_RE = re.compile(
    r"(?:(?P<currency>₹|INR|Rs\.?)\s*)?(?P<amount>[0-9]+(?:\.[0-9]+)?)\s*L(?P<unit>PA)?\b",
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
    salary_currency: str | None = None
    salary_period: str | None = None
    salary_unit: str | None = None
    salary_disclosed: bool = False
    stipend_min: float | None = None
    stipend_max: float | None = None
    stipend_currency: str | None = None
    stipend_period: str | None = None
    stipend_unit: str | None = None
    compensation_type: str = "UNDISCLOSED"  # SALARY | STIPEND | MIXED | QUALITATIVE | UNDISCLOSED
    compensation_text: str | None = None

    @property
    def stipend(self) -> float | None:
        return self.stipend_min

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


def _normalize_period(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("_", " ")
    for token, period in (
        ("year", "YEAR"),
        ("annual", "YEAR"),
        ("annum", "YEAR"),
        ("month", "MONTH"),
        ("week", "WEEK"),
        ("day", "DAY"),
        ("hour", "HOUR"),
    ):
        if token in text:
            return period
    return None


def _normalize_currency(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip().upper()
    return {"₹": "INR", "RS": "INR", "RS.": "INR", "$": "USD", "€": "EUR", "£": "GBP"}.get(token, token)


def _format_provider_amount(amount: float, currency: str | None) -> str:
    amount = float(amount)
    code = _normalize_currency(currency)
    symbol = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(code)
    number = f"{amount:,.2f}".rstrip("0").rstrip(".") if not amount.is_integer() else f"{amount:,.0f}"
    return f"{symbol}{number}" if symbol else (f"{code} {number}" if code else number)


def _format_range(minimum: float | None, maximum: float | None, currency: str | None, period: str | None) -> str | None:
    if minimum is None:
        return None
    low = _format_provider_amount(minimum, currency)
    high = _format_provider_amount(maximum, currency) if maximum is not None else None
    value = f"{low}–{high}" if high is not None and high != low else low
    suffix = {"YEAR": "/year", "MONTH": "/month", "WEEK": "/week", "DAY": "/day", "HOUR": "/hour"}.get(period)
    return f"{value} {suffix}" if suffix else value


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

    # 1. Structured provider fields are authoritative; preserve their amounts and units.
    s_range = payload.get("salaryRange")
    if isinstance(s_range, dict):
        min_val = s_range.get("min")
        max_val = s_range.get("max")
        curr = _normalize_currency(s_range.get("currency"))
        period = _normalize_period(s_range.get("interval"))
        if isinstance(min_val, (int, float)) and min_val > 0:
            result.salary_min = float(min_val)
            result.salary_disclosed = True
            result.salary_currency = curr
            result.compensation_type = "SALARY"
        if isinstance(max_val, (int, float)) and max_val > 0:
            result.salary_max = float(max_val)
            result.salary_disclosed = True
            result.salary_currency = curr
            result.compensation_type = "SALARY"
        result.salary_period = period
        result.salary_unit = "CURRENCY"

    # Greenhouse: pay = {'min_value': ..., 'max_value': ..., 'currency': ..., 'unit': ...}
    pay_obj = payload.get("pay")
    if isinstance(pay_obj, dict):
        min_val = pay_obj.get("min_value")
        max_val = pay_obj.get("max_value")
        curr = _normalize_currency(pay_obj.get("currency") or pay_obj.get("currency_code"))
        if isinstance(min_val, (int, float)) and min_val > 0:
            result.salary_min = float(min_val)
            result.salary_disclosed = True
            result.salary_currency = curr
            result.compensation_type = "SALARY"
        if isinstance(max_val, (int, float)) and max_val > 0:
            result.salary_max = float(max_val)
            result.salary_disclosed = True
            result.salary_currency = curr
            result.compensation_type = "SALARY"
        result.salary_period = _normalize_period(pay_obj.get("unit"))
        result.salary_unit = "CURRENCY"

<<<<<<< HEAD
    # Ashby explicitly distinguishes salary and stipend components and supplies interval/currency.
=======
    # Ashby: compensation = {'summaryComponents': [{'compensationType': 'Salary', 'minValue': ..., 'maxValue': ..., 'currencyCode': 'INR'}]}
>>>>>>> 70804571dc73c928037d4e20acf18351cd6a9b18
    ashby_comp = payload.get("compensation")
    if isinstance(ashby_comp, dict):
        components = ashby_comp.get("summaryComponents") or []
        for comp in components:
            if not isinstance(comp, dict):
                continue
            kind = str(comp.get("compensationType") or "").strip().lower()
            c_curr = _normalize_currency(comp.get("currencyCode"))
            c_min = comp.get("minValue")
            c_max = comp.get("maxValue")
            c_period = _normalize_period(comp.get("interval"))
            if kind == "salary":
                if isinstance(c_min, (int, float)) and c_min > 0:
                    result.salary_min = float(c_min)
                    result.salary_disclosed = True
                    result.salary_currency = c_curr
                if isinstance(c_max, (int, float)) and c_max > 0:
                    result.salary_max = float(c_max)
                    result.salary_disclosed = True
<<<<<<< HEAD
                    result.salary_currency = c_curr
                result.salary_period = c_period
                result.salary_unit = "CURRENCY"
                result.compensation_type = "SALARY"
            elif kind == "stipend":
                if isinstance(c_min, (int, float)) and c_min > 0:
                    result.stipend_min = float(c_min)
                    result.stipend_currency = c_curr
                    result.salary_disclosed = True
                if isinstance(c_max, (int, float)) and c_max > 0:
                    result.stipend_max = float(c_max)
                    result.stipend_currency = c_curr
                    result.salary_disclosed = True
                result.stipend_period = c_period
                result.stipend_unit = "CURRENCY"
                if result.stipend_min is not None:
                    result.compensation_type = "STIPEND" if result.salary_min is None else "MIXED"

        tier_summary = ashby_comp.get("scrapeableCompensationSalarySummary") or ashby_comp.get("compensationTierSummary")
        if tier_summary and isinstance(tier_summary, str) and result.salary_disclosed:
            result.compensation_text = tier_summary.strip()

    # Structured amounts take precedence over text parsing. Render only with source currency/unit.
    if result.salary_min is not None or result.salary_max is not None or result.stipend_min is not None:
        if result.compensation_text is None:
            if result.compensation_type == "STIPEND":
                result.compensation_text = _format_range(
                    result.stipend_min, result.stipend_max, result.stipend_currency, result.stipend_period
                )
            else:
                result.compensation_text = _format_range(
                    result.salary_min, result.salary_max, result.salary_currency, result.salary_period
                )
=======
                    result.salary_currency = c_curr or result.salary_currency
                    result.compensation_type = "NUMERIC"
                tier_summary = ashby_comp.get("scrapeableCompensationSalarySummary") or ashby_comp.get("compensationTierSummary")
                if tier_summary and isinstance(tier_summary, str):
                    result.compensation_text = tier_summary.strip()
                break
    # If structured numeric compensation already found, format text and return
    if result.compensation_type == "NUMERIC":
        if result.salary_min and result.salary_max:
            result.compensation_text = f"₹{result.salary_min}–{result.salary_max} LPA"
        elif result.salary_min:
            result.compensation_text = f"₹{result.salary_min} LPA"
>>>>>>> 70804571dc73c928037d4e20acf18351cd6a9b18
        return result

    if not text:
        return result

    # 2. Text-based numeric extraction. Pay type, currency, scale, and period
    # are set only when the posting states them explicitly.
    context_window = 160
    stipend_range = NUMERIC_STIPEND_RANGE_RE.search(text)
    stipend_single = NUMERIC_STIPEND_RE.search(text) if not stipend_range else None
    stipend_suffix = NUMERIC_STIPEND_SUFFIX_RE.search(text) if not stipend_range and not stipend_single else None
    stipend_match = stipend_range or stipend_single or stipend_suffix
    if stipend_match:
        raw_context = text[max(0, stipend_match.start() - context_window):min(len(text), stipend_match.end() + context_window)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                if stipend_range:
                    stipend_min = float(stipend_range.group(2).replace(",", ""))
                    stipend_max = float(stipend_range.group(4).replace(",", ""))
                    currency = _normalize_currency(stipend_range.group(1) or stipend_range.group(3))
                    period = _normalize_period(stipend_range.group(5))
                elif stipend_suffix:
                    stipend_min = float(stipend_suffix.group("amount").replace(",", ""))
                    stipend_max = None
                    currency = _normalize_currency(stipend_suffix.group("currency"))
                    period = _normalize_period(stipend_suffix.group("period"))
                else:
                    stipend_min = float(stipend_single.group(2).replace(",", ""))
                    stipend_max = None
                    currency = _normalize_currency(stipend_single.group(1))
                    period = _normalize_period(stipend_single.group(3))
                if stipend_min > 0 and (stipend_max is None or stipend_max > 0):
                    result.stipend_min = stipend_min
                    result.stipend_max = stipend_max
                    result.stipend_currency = currency
                    result.stipend_period = period
                    result.stipend_unit = "CURRENCY"
                    result.salary_disclosed = True
                    result.compensation_type = "STIPEND"
                    result.compensation_text = _format_range(stipend_min, stipend_max, currency, period)
                    return result
            except (ValueError, TypeError):
                pass

    lakh_range = NUMERIC_LAKH_RANGE_RE.search(text)
    if lakh_range:
        raw_context = text[max(0, lakh_range.start() - context_window):min(len(text), lakh_range.end() + context_window)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            result.salary_min = float(lakh_range.group("min"))
            result.salary_max = float(lakh_range.group("max"))
            result.salary_currency = _normalize_currency(lakh_range.group("currency") or lakh_range.group("currency_max")) or "INR"
            is_lpa = bool(lakh_range.group("unit_min") or lakh_range.group("unit_max"))
            result.salary_period = "YEAR" if is_lpa else None
            result.salary_unit = "LPA" if is_lpa else "LAKH"
            result.salary_disclosed = True
            result.compensation_type = "SALARY"
            if re.search(r"\bstipend\b", raw_context, re.I):
                result.stipend_min = result.salary_min
                result.stipend_max = result.salary_max
                result.stipend_currency = result.salary_currency
                result.stipend_period = result.salary_period
                result.stipend_unit = result.salary_unit
                result.salary_min = None
                result.salary_max = None
                result.compensation_type = "STIPEND"
                result.compensation_text = f"₹{result.stipend_min:g}–{result.stipend_max:g} {result.stipend_unit} stipend"
            else:
                unit_text = "LPA" if is_lpa else "lakh"
                result.compensation_text = f"₹{result.salary_min:g}–{result.salary_max:g} {unit_text}"
            return result

    currency_range = NUMERIC_CURRENCY_RANGE_RE.search(text)
    if currency_range and re.match(r"\s*(?:lpa|lacs?|lakhs?|l(?:pa)?|per\s+annum|p\.?a\.?)\b", text[currency_range.end():], re.I):
        currency_range = None
    if currency_range:
        raw_context = text[max(0, currency_range.start() - context_window):min(len(text), currency_range.end() + context_window)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                result.salary_min = float(currency_range.group("min").replace(",", ""))
                result.salary_max = float(currency_range.group("max").replace(",", ""))
                result.salary_currency = _normalize_currency(currency_range.group("currency") or currency_range.group("currency_max") or currency_range.group("currency_suffix"))
                result.salary_period = _normalize_period(currency_range.group("period"))
                result.salary_unit = "CURRENCY"
                result.salary_disclosed = True
                result.compensation_type = "SALARY"
                result.compensation_text = _format_range(
                    result.salary_min, result.salary_max, result.salary_currency, result.salary_period
                )
                return result
            except (ValueError, TypeError):
                pass

    lpa_range = NUMERIC_LPA_RANGE_RE.search(text)
    if lpa_range:
        raw_context = text[max(0, lpa_range.start() - context_window):min(len(text), lpa_range.end() + context_window)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                result.salary_min = float(lpa_range.group(1))
                result.salary_max = float(lpa_range.group(2))
                suffix = lpa_range.group(3).lower()
                is_lpa = "lpa" in suffix or "annum" in suffix or "p.a" in suffix
                result.salary_currency = "INR"
                result.salary_period = "YEAR" if is_lpa else None
                result.salary_unit = "LPA" if is_lpa else "LAKH"
                result.salary_disclosed = True
                result.compensation_type = "SALARY"
                unit_text = "LPA" if is_lpa else "lakh"
                result.compensation_text = f"₹{result.salary_min:g}–{result.salary_max:g} {unit_text}"
                return result
            except (ValueError, TypeError):
                pass

    currency_single = NUMERIC_CURRENCY_SINGLE_RE.search(text)
    if currency_single and re.match(r"\s*(?:lpa|lacs?|lakhs?|l(?:pa)?|per\s+annum|p\.?a\.?)\b", text[currency_single.end():], re.I):
        currency_single = None
    if currency_single:
        raw_context = text[max(0, currency_single.start() - context_window):min(len(text), currency_single.end() + context_window)]
        if re.search(r"\b(?:salary|compensation|pay|remuneration|stipend|range|ctc)\b", raw_context, re.I) and not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                result.salary_min = float(currency_single.group("amount").replace(",", ""))
                result.salary_currency = _normalize_currency(currency_single.group("currency"))
                result.salary_period = _normalize_period(currency_single.group("period"))
                result.salary_unit = "CURRENCY"
                result.salary_disclosed = True
                result.compensation_type = "SALARY"
                result.compensation_text = f"₹{result.salary_min:g} LPA"
                return result
            except (ValueError, TypeError):
                pass

    lakh_single = NUMERIC_LAKH_SINGLE_RE.search(text)
    if lakh_single:
        raw_context = text[max(0, lakh_single.start() - context_window):min(len(text), lakh_single.end() + context_window)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS) and re.search(r"\b(?:salary|ctc|compensation|remuneration|package|pay|stipend)\b", raw_context, re.I):
            result.salary_min = float(lakh_single.group("amount"))
            result.salary_currency = _normalize_currency(lakh_single.group("currency")) or "INR"
            result.salary_period = "YEAR" if lakh_single.group("unit") else None
            result.salary_unit = "LPA" if lakh_single.group("unit") else "LAKH"
            result.salary_disclosed = True
            result.compensation_type = "SALARY"
            if re.search(r"\bstipend\b", raw_context, re.I):
                result.stipend_min = result.salary_min
                result.stipend_currency = result.salary_currency
                result.stipend_period = result.salary_period
                result.stipend_unit = result.salary_unit
                result.salary_min = None
                result.compensation_type = "STIPEND"
            amount = result.stipend_min if result.compensation_type == "STIPEND" else result.salary_min
            unit_text = result.stipend_unit if result.compensation_type == "STIPEND" else result.salary_unit
            result.compensation_text = f"₹{amount:g} {unit_text}"
            return result

    lpa_single = NUMERIC_LPA_SINGLE_RE.search(text)
    if lpa_single:
        raw_context = text[max(0, lpa_single.start() - context_window):min(len(text), lpa_single.end() + context_window)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
            try:
                result.salary_min = float(lpa_single.group(1))
                result.salary_currency = "INR"
                result.salary_period = "YEAR"
                result.salary_unit = "LPA"
                result.salary_disclosed = True
                result.compensation_type = "SALARY"
                result.compensation_text = f"₹{result.salary_min:g} LPA"
                return result
            except (ValueError, TypeError):
                pass

    lakhs_single = NUMERIC_LAKHS_SINGLE_RE.search(text)
    if lakhs_single:
        raw_context = text[max(0, lakhs_single.start() - context_window):min(len(text), lakhs_single.end() + context_window)]
        if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS) and re.search(r"\b(?:salary|ctc|compensation|remuneration|package|pay)\b", raw_context, re.I):
            try:
                result.salary_min = float(lakhs_single.group(1))
                result.salary_currency = "INR"
                result.salary_unit = "LAKH"
                result.salary_period = "YEAR" if re.search(r"\b(?:per\s+annum|annual|yearly|p\.?a\.?)\b", raw_context, re.I) else None
                result.salary_disclosed = True
                result.compensation_type = "SALARY"
                result.compensation_text = f"₹{result.salary_min:g} lakh"
                return result
            except (ValueError, TypeError):
                pass

    # 3. Internship-specific qualitative statements (paid/unpaid)
    if is_internship or "intern" in (text[:200].lower()):
        for pat, label in INTERNSHIP_QUALITATIVE_PATTERNS:
            m = pat.search(text)
            if m:
                raw_context = text[max(0, m.start() - context_window):min(len(text), m.end() + context_window)]
                if not any(fp.search(raw_context) for fp in FALSE_POSITIVE_PATTERNS):
                    result.compensation_text = label
                    result.salary_disclosed = True
                    result.compensation_type = "QUALITATIVE"
                    return result

    # 4. General Qualitative Compensation Recognition
    for pat, label in QUALITATIVE_PATTERNS:
        m = pat.search(text)
        if m:
            raw_context = text[max(0, m.start() - context_window):min(len(text), m.end() + context_window)]
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


def extract_compensation_details(
    text: str | None = None,
    is_internship: bool = False,
) -> CompensationDetails:
    """Convenience wrapper for extracting compensation details directly from text."""
    return extract_compensation_from_payload_and_text(text=text, is_internship=is_internship)
