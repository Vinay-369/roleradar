"""
Neutral domain utilities for quantified metric extraction and normalization.
Decoupled from tailoring and intelligence services to avoid circular dependencies.
"""
from __future__ import annotations

import re

# Comprehensive regex for extracting metrics (percentages, multipliers, currency, durations, scale)
_METRIC_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?%?|\$\d+(?:\.\d+)?(?:k|m|b)?\+?|\b\d+[xXkKMmB]\b|\b\d+\+?\s*(?:hours?|hrs?|mins?|minutes?|secs?|seconds?|days?|users?|deployments?|transactions?|requests?|records?|rows?)\b)",
    re.IGNORECASE,
)

# Standard fast metric finder matching existing regex patterns
_STANDARD_METRIC_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?%?|\$\d+(?:\.\d+)?(?:k|m|b)?\+?|\b\d+[xXkKMmB]\b)",
    re.IGNORECASE,
)


def extract_quantified_metrics(text: str) -> list[str]:
    """
    Extract numbers, percentages, multipliers, currency metrics, and scale tokens.
    """
    if not text:
        return []
    return _STANDARD_METRIC_RE.findall(text)


def normalize_metric(metric: str) -> str:
    """
    Canonicalizes metric representations for comparison (e.g. '99.8 %' -> '99.8%').
    """
    value = metric.lower().replace(",", "").replace("+", "")
    value = re.sub(r"\s+", "", value)
    return value.replace("percent", "%")


# Backward compatibility alias
_extract_quantified_metrics = extract_quantified_metrics
