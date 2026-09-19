import sys
sys.path.insert(0, "backend")

from app.modules.jobs.taxonomy import analyze_job_description

test_jd = """
## Company Description
Bosch Global Software Technologies Private Limited is a subsidiary of Robert Bosch GmbH.

## Job Description
Tasks / Responsibilities:
- Design, build, and maintain advanced applications for the iOS platform using Swift/Objective-C and AOS platform Java/Kotlin
- Collaborate with cross-functional teams to define, design, and ship new features.
- Ensure the performance, quality, and responsiveness of applications.
- Identify and correct bottlenecks, fix bugs, and improve application performance.
- Help maintain code quality, organization, and automatization.
- Continuously discover, evaluate, and implement new technologies to maximize development efficiency.
- Unit-test code for robustness, including edge cases, usability, and general reliability.
- Work with APIs and third-party libraries.
- Participate in code reviews to ensure code quality and share knowledge.
- Stay up-to-date with the latest trends, architectural patterns, and best practices in iOS development.

Expected skill set:
- Strong proficiency in Swift and/or Objective-C. (Specify preference if any, e.g., "Strong preference for Swift.") and AOS platform Java/Kotlin
- In-depth understanding of the iOS SDK, Cocoa Touch, and UIKit framework.
- Experience integrating and working with core iOS & AOS communication frameworks
- Solid understanding of object-oriented programming (OOP) principles and design patterns (e.g., MVVM, MVC, VIPER).
- Experience with RESTful APIs to connect iOS applications to backend services
- Strong understanding of memory management, threading, and performance optimization for iOS apps.

Good to have:
- Familiarity with dependency injection frameworks.
- Experience with CI/CD pipelines for mobile applications.
- Familiarity with Figma, Sketch, or other design tools.

## Qualifications
B.E or B.Tech

## Additional Information
5 - 8 Years
"""

reqs = analyze_job_description(test_jd, "Senior Mobile APP (IOS/AOS) Developer")

print("=== TAXONOMY ANALYSIS RESULTS ===")
print("Required skills:", reqs.must_have_skills)
print("Preferred skills:", reqs.preferred_skills)
print("Responsibilities count:", len(reqs.responsibilities))
for r in reqs.responsibilities[:3]:
    print("  Resp:", r)
print("Qualifications:", reqs.qualifications)
print("Experience:", reqs.min_years_experience, "to", reqs.max_years_experience)
print("Domain:", reqs.domain)
print("Seniority:", reqs.seniority)
