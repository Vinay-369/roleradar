import sys
import re
sys.path.insert(0, "backend")

from app.modules.jobs.skill_vocabulary import extract_skills_from_text

REQ_PREDICATES = [
    r"strong\s+proficiency\s+(?:in|with)",
    r"proficiency\s+(?:in|with)",
    r"proficient\s+(?:in|with)",
    r"(?:in-depth|solid|strong|deep|thorough|sound|good|working|practical)\s+understanding\s+of",
    r"(?:hands-on\s+|proven\s+|demonstrated\s+|prior\s+)?experience\s+(?:with|in|integrating|building|developing|working\s+with)",
    r"(?:working\s+|sound\s+|deep\s+|solid\s+|practical\s+)?knowledge\s+of",
    r"skilled\s+(?:in|with)",
    r"expertise\s+(?:in|with)",
    r"must\s+have",
    r"required\s+(?:to\s+have|skills?)",
    r"candidates?\s+should\s+have",
    r"familiarity\s+with",
    r"ability\s+to",
]

REQ_PREDICATE_RE = re.compile(
    r"\b(?:" + "|".join(REQ_PREDICATES) + r")\b",
    re.IGNORECASE
)

PREF_PREDICATES = [
    r"good\s+to\s+have",
    r"nice\s+to\s+have",
    r"bonus(?:\s+points)?",
    r"plus",
    r"preferred",
    r"preference\s+for",
    r"desirable",
    r"advantageous",
]

PREF_PREDICATE_RE = re.compile(
    r"\b(?:" + "|".join(PREF_PREDICATES) + r")\b",
    re.IGNORECASE
)

test_lines = [
    "Strong proficiency in Swift and/or Objective-C. (Specify preference if any, e.g., 'Strong preference for Swift.') and AOS platform Java/Kotlin",
    "In-depth understanding of the iOS SDK, Cocoa Touch, and UIKit framework.",
    "Experience integrating and working with core iOS & AOS communication frameworks",
    "Solid understanding of object-oriented programming (OOP) principles and design patterns (e.g., MVVM, MVC, VIPER).",
    "Experience with RESTful APIs to connect iOS applications to backend services",
    "Strong understanding of memory management, threading, and performance optimization for iOS apps.",
    "Good to have: Familiarity with dependency injection frameworks.",
    "Experience with CI/CD pipelines for mobile applications.",
    "Familiarity with Figma, Sketch, or other design tools.",
    "Design, build, and maintain advanced applications for the iOS platform using Swift/Objective-C",
    "Collaborate with cross-functional teams to define, design, and ship new features.",
    "Our team uses Python for backend microservices.",
    "where every story begins with a spark of inspiration and a dash of entrepreneurship",
]

for line in test_lines:
    has_req = bool(REQ_PREDICATE_RE.search(line))
    has_pref = bool(PREF_PREDICATE_RE.search(line))
    skills = extract_skills_from_text(line)
    cat = "PREFERRED" if has_pref else ("REQUIRED" if has_req else "CONTEXTUAL/ACTION")
    print(f"[{cat:17s}] skills={skills} | Line: {line[:70]}...")
