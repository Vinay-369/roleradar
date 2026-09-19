import sys
sys.path.insert(0, "backend")
import spacy
from spacy.matcher import PhraseMatcher
from app.modules.jobs.skill_vocabulary import KNOWN_SKILLS, ALIAS_MAP

ADDITIONAL_SKILLS = [
    "iOS", "iOS SDK", "Cocoa Touch", "UIKit", "Figma", "Sketch",
    "Dependency Injection", "MVVM", "MVC", "VIPER", "Android",
]

ADDITIONAL_ALIASES = {
    "ios": "iOS",
    "ios sdk": "iOS SDK",
    "cocoa touch": "Cocoa Touch",
    "uikit": "UIKit",
    "figma": "Figma",
    "sketch": "Sketch",
    "dependency injection": "Dependency Injection",
    "mvvm": "MVVM",
    "mvc": "MVC",
    "viper": "VIPER",
    "objective-c": "Objective-C",
    "objective c": "Objective-C",
    "restful apis": "REST APIs",
    "restful api": "REST APIs",
}

all_skills = list(KNOWN_SKILLS) + ADDITIONAL_SKILLS
all_aliases = dict(ALIAS_MAP)
all_aliases.update(ADDITIONAL_ALIASES)

nlp = spacy.blank("en")
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
matcher.add("SKILLS", [nlp.make_doc(s) for s in all_skills])
matcher.add("ALIASES", [nlp.make_doc(a) for a in all_aliases.keys()])

test_lines = [
    "Strong proficiency in Swift and/or Objective-C. (Specify preference if any, e.g., 'Strong preference for Swift.') and AOS platform Java/Kotlin",
    "In-depth understanding of the iOS SDK, Cocoa Touch, and UIKit framework.",
    "Experience integrating and working with core iOS & AOS communication frameworks",
    "Solid understanding of object-oriented programming (OOP) principles and design patterns (e.g., MVVM, MVC, VIPER).",
    "Experience with RESTful APIs to connect iOS applications to backend services",
    "Familiarity with dependency injection frameworks.",
    "Experience with CI/CD pipelines for mobile applications.",
    "Familiarity with Figma, Sketch, or other design tools."
]

for t in test_lines:
    doc = nlp(t)
    matches = matcher(doc)
    extracted = set()
    for match_id, start, end in matches:
        span_text = doc[start:end].text.lower()
        if span_text in all_aliases:
            extracted.add(all_aliases[span_text])
        else:
            extracted.add(doc[start:end].text)
    print(t[:60], "-->", sorted(list(extracted)))
