"""
India Location and Workplace Normalization Layer.
Normalizes Indian metro aliases, detects workplace modes (REMOTE/HYBRID/ON_SITE),
and standardizes INR compensation representations without altering raw display text.
"""
from __future__ import annotations

import re
from typing import Any

# Canonical Metro Cluster mapping
INDIA_METRO_CLUSTERS: dict[str, set[str]] = {
    "Bengaluru": {
        "bengaluru", "bangalore", "blr", "whitefield", "electronic city", "koramangala", "indiranagar", "bellandur", "marathahalli"
    },
    "Gurugram": {
        "gurugram", "gurgaon", "cyber city", "cyber hub", "golf course road"
    },
    "Noida": {
        "noida", "greater noida", "sector 62", "sector 125", "sector 135"
    },
    "Delhi NCR": {
        "delhi", "new delhi", "delhi ncr", "ncr", "ghaziabad", "faridabad"
    },
    "Mumbai": {
        "mumbai", "bombay", "navi mumbai", "thane", "bkc", "bandra", "andheri", "powai", "lower parel"
    },
    "Hyderabad": {
        "hyderabad", "secunderabad", "hitech city", "madhapur", "gachibowli", "kondapur", "cyberabad"
    },
    "Pune": {
        "pune", "poona", "hinjewadi", "magarpatta", "viman nagar", "baner", "kharadi", "wakad"
    },
    "Chennai": {
        "chennai", "madras", "omr", "t nagar", "velachery", "sholinganallur", "guindy"
    },
    "Kolkata": {
        "kolkata", "calcutta", "salt lake", "new town", "rajarhat", "sector v"
    },
    "Ahmedabad": {
        "ahmedabad", "gandhinagar", "gift city"
    },
    "Kochi": {
        "kochi", "cochin", "infopark", "kakkanad"
    },
    "Chandigarh": {
        "chandigarh", "mohali", "panchkula", "tricity"
    },
    "Jaipur": {"jaipur"},
    "Indore": {"indore"},
    "Lucknow": {"lucknow", "lko"},
    "Coimbatore": {"coimbatore", "kovai"},
    "Bhubaneswar": {"bhubaneswar", "bhubaneshwar"},
    "Thiruvananthapuram": {"thiruvananthapuram", "trivandrum", "technopark"},
    "Nagpur": {"nagpur"},
    "Vadodara": {"vadodara", "baroda"},
}

INDIA_LOCATION_KEYWORDS = {
    "india", "in", "bengaluru", "bangalore", "delhi", "gurgaon", "gurugram", "noida",
    "mumbai", "bombay", "hyderabad", "pune", "chennai", "kolkata", "ahmedabad", "kochi",
    "chandigarh", "mohali", "jaipur", "indore", "lucknow", "coimbatore", "bhubaneswar",
    "bhubaneshwar", "thiruvananthapuram", "trivandrum", "nagpur", "vadodara"
}


def normalize_india_location(location_str: str | None) -> str | None:
    """
    Returns canonical city cluster if recognized, otherwise cleaned location string.
    Does not mutate original display text.
    """
    if not location_str or not location_str.strip():
        return None

    raw_clean = location_str.lower().strip()
    # Normalize punctuation and delimiters
    tokens = set(re.findall(r"\b[a-z0-9-]+\b", raw_clean))

    for canonical, aliases in INDIA_METRO_CLUSTERS.items():
        for alias in aliases:
            if alias in raw_clean or alias in tokens:
                return canonical

    return location_str.strip()


COUNTRY_DEFINITIONS: list[tuple[str, list[str]]] = [
    ("India", [
        r"\bindia\b", r"\bbharat\b", r"\bremote\s*-\s*india\b"
    ]),
    ("United States", [
        r"\bunited\s+states\s+of\s+america\b",
        r"\bunited\s+states\b",
        r"\bu\.s\.a\.\b",
        r"\busa\b",
        r"\bu\.s\.\b",
        r"\bca,\s*united\s+states\b",
        r"\b(?:alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new\s+hampshire|new\s+jersey|new\s+mexico|new\s+york|north\s+carolina|north\s+dakota|ohio|oklahoma|oregon|pennsylvania|rhode\s+island|south\s+carolina|south\s+dakota|tennessee|texas|utah|vermont|virginia|washington|west\s+virginia|wisconsin|wyoming)\b",
        r",\s*(?:al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy)\b",
        r"\bremote\s*-\s*us\b",
    ]),
    ("United Arab Emirates", [
        r"\bunited\s+arab\s+emirates\b",
        r"\bu\.a\.e\.\b",
        r"\buae\b",
        r"\bdubai\b",
        r"\babu\s+dhabi\b",
        r"\bsharjah\b",
    ]),
    ("United Kingdom", [
        r"\bunited\s+kingdom\b",
        r"\bu\.k\.\b",
        r"\bgreat\s+britain\b",
        r"\bengland\b",
        r"\bscotland\b",
        r"\bwales\b",
        r"\blondon\b",
        r"\bremote\s*-\s*uk\b",
        r"\buk\b",
        r",\s*uk\b",
    ]),
    ("Canada", [
        r"\bcanada\b",
        r"\b(?:toronto|vancouver|montreal|ottawa|calgary|waterloo)\b",
    ]),
    ("Germany", [
        r"\bgermany\b",
        r"\bdeutschland\b",
        r"\b(?:berlin|munich|frankfurt|hamburg)\b",
    ]),
    ("Singapore", [
        r"\bsingapore\b",
    ]),
    ("Australia", [
        r"\baustralia\b",
        r"\b(?:sydney|melbourne|brisbane)\b",
    ]),
    ("Ireland", [
        r"\bireland\b",
        r"\bdublin\b",
    ]),
    ("Netherlands", [
        r"\bnetherlands\b",
        r"\bholland\b",
        r"\bamsterdam\b",
    ]),
    ("France", [
        r"\bfrance\b",
        r"\bparis\b",
    ]),
    ("Japan", [
        r"\bjapan\b",
        r"\btokyo\b",
    ]),
    ("Switzerland", [
        r"\bswitzerland\b",
        r"\b(?:zurich|geneva)\b",
    ]),
    ("Israel", [
        r"\bisrael\b",
        r"\btel\s+aviv\b",
    ]),
    ("Poland", [
        r"\bpoland\b",
        r"\bwarsaw\b",
        r"\bkrakow\b",
    ]),
    ("Spain", [
        r"\bspain\b",
        r"\b(?:madrid|barcelona)\b",
    ]),
    ("Brazil", [
        r"\bbrazil\b",
        r"\bbrasil\b",
        r"\bsao\s+paulo\b",
    ]),
    ("Egypt", [
        r"\begypt\b",
        r"\bcairo\b",
    ]),
    ("South Korea", [
        r"\bsouth\s+korea\b",
        r"\bkorea\b",
        r"\bseoul\b",
    ]),
    ("China", [
        r"\bchina\b",
        r"\bbeijing\b",
        r"\bshanghai\b",
        r"\bshenzhen\b",
    ]),
    ("Mexico", [
        r"\bmexico\b",
        r"\bmexico\s+city\b",
    ]),
    ("Thailand", [
        r"\bthailand\b",
        r"\bbangkok\b",
    ]),
    ("Indonesia", [
        r"\bindonesia\b",
        r"\bjakarta\b",
    ]),
    ("Philippines", [
        r"\bphilippines\b",
        r"\bmanila\b",
    ]),
    ("South Africa", [
        r"\bsouth\s+africa\b",
        r"\bjohannesburg\b",
        r"\bcape\s+town\b",
    ]),
    ("Italy", [
        r"\bitaly\b",
        r"\bmilan\b",
        r"\brome\b",
    ]),
    ("Denmark", [
        r"\bdenmark\b",
        r"\bcopenhagen\b",
    ]),
]


def extract_country_from_location(location_str: str | None) -> str | None:
    """
    Deterministically extracts country name from a location string.
    Returns:
        Canonical country string (e.g. 'India', 'United States', 'United Kingdom')
        or None when unknown, ambiguous, or purely 'Remote'.
    """
    if not location_str or not location_str.strip():
        return None

    raw = location_str.strip()
    raw_lower = raw.lower()

    # Reject purely generic remote or unknown markers
    if raw_lower in ("remote", "unknown", "not specified", "any", "anywhere", "flexible", "n/a"):
        return None

    # Multi-location strings separated by semicolons/bullets/bars
    segments = [s.strip() for s in re.split(r"[;•|]", raw) if s.strip()]
    if not segments:
        segments = [raw]

    found_countries: set[str] = set()

    for seg in segments:
        seg_lower = seg.lower()

        # Check Indian Metro Clusters
        for canonical_city, aliases in INDIA_METRO_CLUSTERS.items():
            for alias in aliases:
                if re.search(r"\b" + re.escape(alias) + r"\b", seg_lower):
                    found_countries.add("India")
                    break
            if "India" in found_countries:
                break

        # Check vocabulary regexes
        for country_name, patterns in COUNTRY_DEFINITIONS:
            for pattern in patterns:
                if re.search(pattern, seg_lower, re.IGNORECASE):
                    found_countries.add(country_name)
                    break

    if len(found_countries) == 1:
        return next(iter(found_countries))
    elif len(found_countries) > 1:
        # Multi-country locations cannot be safely represented as a single country string
        return None

    return None


def is_location_match(
    candidate_preferred_locations: list[str] | None,
    job_location: str | None,
    job_is_remote: bool = False,
) -> bool | None:
    """
    Determines if candidate preferred locations match job location with alias tolerance.
    Returns:
      True: Confident match (e.g. Bangalore matches Bengaluru, or Remote matches Any/Remote)
      False: Confident mismatch (e.g. Pune vs Chennai when candidate is on-site only)
      None: Unknown / Unspecified (e.g. Job has no location and is not remote)
    """
    if job_is_remote:
        return True

    if not job_location or not job_location.strip():
        return None  # Do not assume remote or local without evidence

    if not candidate_preferred_locations:
        return None  # No candidate location preferences set

    job_canonical = normalize_india_location(job_location)
    job_lower = job_location.lower()

    for pref in candidate_preferred_locations:
        if not pref:
            continue
        pref_lower = pref.lower().strip()
        if pref_lower in ("any", "anywhere", "all india", "remote"):
            return True

        pref_canonical = normalize_india_location(pref)

        # Check canonical match
        if job_canonical and pref_canonical and job_canonical == pref_canonical:
            return True

        # Check Delhi NCR cluster overlap
        if pref_canonical == "Delhi NCR" and job_canonical in ("Gurugram", "Noida", "Delhi NCR"):
            return True
        if job_canonical == "Delhi NCR" and pref_canonical in ("Gurugram", "Noida", "Delhi NCR"):
            return True

        # Substring / token matching
        if pref_lower in job_lower or job_lower in pref_lower:
            return True

    return False


def detect_workplace_type(
    location: str | None,
    description: str | None = "",
    is_remote_flag: bool = False,
) -> str:
    """
    Detects workplace mode: REMOTE, HYBRID, ON_SITE, or UNKNOWN.
    """
    if is_remote_flag:
        return "REMOTE"

    combined = f"{location or ''} {description or ''}".lower()

    if not combined.strip():
        return "UNKNOWN"

    if re.search(r"\b(?:fully\s+remote|100%\s+remote|work\s+from\s+anywhere|remote\s+first|remote)\b", combined):
        # Guard against "not remote" or "remote: no"
        if not re.search(r"\b(?:not\s+remote|remote\s*:\s*no|no\s+remote)\b", combined):
            return "REMOTE"

    if re.search(r"\b(?:hybrid|flexible\s+work|hybrid\s+model|2-3\s+days\s+office)\b", combined):
        return "HYBRID"

    if location and location.strip():
        return "ON_SITE"

    return "UNKNOWN"


def is_india_opportunity(location: str | None, description: str | None = "", currency: str | None = None) -> bool:
    """
    Determines if an opportunity is India-focused strictly based on its location metadata.
    Company descriptions/boilerplate MUST NOT cause a foreign job to be marked as Indian.
    """
    if not location or not location.strip():
        return False

    raw = location.strip()
    raw_lower = raw.lower()

    # Reject purely generic remote or unknown markers without geographic anchor
    if raw_lower in ("remote", "unknown", "not specified", "any", "anywhere", "flexible", "n/a"):
        return False

    # Multi-location strings separated by semicolons, bullets, or bars
    segments = [s.strip() for s in re.split(r"[;•|]", raw) if s.strip()]
    if not segments:
        segments = [raw]

    # If ANY segment of the location is in India, the role is India-relevant
    for seg in segments:
        seg_lower = seg.lower()

        # Check explicit country extraction on segment
        country = extract_country_from_location(seg)
        if country == "India":
            return True

        # Check Indian Metro Clusters on segment
        for canonical_city, aliases in INDIA_METRO_CLUSTERS.items():
            for alias in aliases:
                if re.search(r"\b" + re.escape(alias) + r"\b", seg_lower):
                    return True

        # Check keywords on segment
        for kw in INDIA_LOCATION_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", seg_lower):
                if kw == "in" and not re.search(r"\b(?:,\s*in|india)\b", seg_lower):
                    continue
                return True

    return False
