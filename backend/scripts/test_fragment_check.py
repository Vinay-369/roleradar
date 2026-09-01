import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.resume.parsing.action_verbs import STRONG_ACTION_VERBS

_BULLET_PREFIX_RE = re.compile(r"^[•\-\*\s]+")
_DANGLING_ENDINGS = {"and", "or", "with", "for", "to", "by", "via", "using", "including", "such as", "as well as", "in"}
_DANGLING_STARTS = {"and", "or", "but", "nor", "so", "yet", "with", "for", "to", "by", "via", "of", "in order to", "as well as", "such as", "including"}

def detect_sentence_fragments_and_truncation(original: str, proposed: str) -> list[str]:
    if not proposed:
        return ["Empty proposed bullet"]
    
    clean_orig = _BULLET_PREFIX_RE.sub("", original).strip()
    clean_prop = _BULLET_PREFIX_RE.sub("", proposed).strip()
    
    if not clean_prop:
        return ["Empty proposed bullet content"]
        
    violations = []
    
    # 1. Structural headings and date lines are exempt
    if clean_orig.endswith(":") or (re.search(r"\b(?:\d{4}|present)\b", clean_orig, re.IGNORECASE) and len(clean_orig.split()) <= 12 and not clean_orig.endswith((".", ";", "!"))):
        return []
        
    orig_words = clean_orig.split()
    prop_words = clean_prop.split()
    
    # 2. Minimum length check for full bullets
    if len(orig_words) >= 5 and len(prop_words) < 3:
        violations.append(f"Bullet is an incomplete fragment ({len(prop_words)} words)")
        
    # 3. Lowercase lead check (lost capital or stripped opening word)
    if clean_prop[0].islower() and not (clean_orig and clean_orig[0].islower()):
        violations.append(f"Bullet begins with lowercase orphaned fragment: \"{clean_prop[:30]}...\"")
        
    # 4. Dangling start check (starts with conjunction/preposition without main clause)
    first_two = " ".join([w.lower() for w in prop_words[:2]]) if len(prop_words) >= 2 else ""
    first_w = prop_words[0].lower().rstrip(":,") if prop_words else ""
    if (first_w in _DANGLING_STARTS or first_two in _DANGLING_STARTS) and not (clean_orig.lower().startswith(first_w)):
        violations.append(f"Bullet starts with orphaned continuation (\"{first_w}\")")
        
    # 5. Missing action verb check (if original had a strong action lead, rewrite must not degrade to a headless noun fragment)
    orig_has_action = any(re.sub(r"[^a-zA-Z]", "", w).lower() in STRONG_ACTION_VERBS for w in orig_words[:4])
    prop_has_action = any(re.sub(r"[^a-zA-Z]", "", w).lower() in STRONG_ACTION_VERBS for w in prop_words[:4])
    if orig_has_action and not prop_has_action and not clean_prop.endswith(":"):
        violations.append("Bullet has lost its leading action verb and degraded to an incomplete fragment")
        
    # 6. Abrupt ending check
    if clean_prop.endswith((",", ";", " -", " –", " —", ":")) and not clean_orig.endswith(clean_prop[-1]):
        violations.append(f"Bullet is abruptly truncated with trailing punctuation: \"...{clean_prop[-10:]}\"")
    last_w = prop_words[-1].lower().rstrip(".,;!") if prop_words else ""
    if last_w in _DANGLING_ENDINGS:
        violations.append(f"Bullet ends abruptly with dangling word: \"{last_w}\"")
        
    return sorted(list(set(violations)))

cases = [
    ("Engineered a global CDN distribution optimized for low-latency communication.", "global CDN distribution optimized for low-latency communication."),
    ("Engineered a global CDN distribution optimized for low-latency communication.", "Engineered global CDN distribution for low latency."),
    ("Built automated CI/CD pipeline using GitHub Actions", "and deployed on AWS"),
    ("Developed scalable microservices with FastAPI", "Developed"),
    ("Optimized database queries for PostgreSQL", "Optimized database queries for,"),
    ("Software Engineer - 3 (April 2024 - Present)", "Software Engineer - 3 (April 2024 - Present)"),
]

for orig, prop in cases:
    v = detect_sentence_fragments_and_truncation(orig, prop)
    print("ORIG:", orig)
    print("PROP:", prop)
    print("VIOLATIONS:", v)
    print()
