import sys
sys.path.insert(0, "backend")
from app.modules.jobs.skill_vocabulary import extract_skills_from_text

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
    print(t[:60], "-->", extract_skills_from_text(t))
