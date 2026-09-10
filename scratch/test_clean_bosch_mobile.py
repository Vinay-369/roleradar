import re
import html

def clean_html(text: str) -> str:
    if not text:
        return ""
    t = html.unescape(text)
    
    # Pre-break embedded subheadings when glued to previous text or punctuation
    subheadings = [
        r"Tasks\s*/\s*Responsibilities\s*:",
        r"Key\s+Responsibilities\s*:",
        r"Responsibilities\s*:",
        r"Expected\s+skill\s*set\s*:",
        r"Required\s+Skills\s*:",
        r"Requirements\s*:",
        r"Qualifications\s*:",
        r"Good\s+to\s+have\s*:",
        r"Nice\s+to\s+have\s*:",
        r"Preferred\s*:",
        r"Preferred\s+Qualifications\s*:",
        r"Additional\s+Information\s*:",
    ]
    for sh in subheadings:
        t = re.sub(rf"(?<=[^\n])\s*(?={sh})", "\n\n", t, flags=re.IGNORECASE)

    # Convert all common bullet/separator artifacts into markdown bullets
    # including \xb7 (\u00b7 middle dot), \u00d8 (Ø), \ufffd, • (\u2022), \uf0b7, \uf0a7, \u25aa, etc.
    bullet_chars = r"[\u00d8\ufffd•\u00b7\uf0b7\uf0a7\u25aa\u25b6\u25c6·]"
    t = re.sub(rf"[\s\xa0]*{bullet_chars}[\s\xa0]*", "\n- ", t)

    # Convert HTML line breaks and list items to proper newlines
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<li>", "\n- ", t, flags=re.I)
    t = re.sub(r"</li>", "\n", t, flags=re.I)
    t = re.sub(r"</(?:p|div|tr|h\d)>", "\n\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)

    lines = [re.sub(r"[\t\xa0 ]+", " ", l).strip() for l in t.split("\n")]
    clean = "\n".join(lines)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean

raw_jd_html = '<p>Tasks / Responsibilities:·\xa0\xa0\xa0\xa0\xa0\xa0 Design, build, and maintain advanced applications for the iOS platform using Swift/Objective-C and AOS platform Java/Kotlin·\xa0\xa0\xa0\xa0\xa0\xa0 Collaborate with cross-functional teams to define, design, and ship new features.·\xa0\xa0\xa0\xa0\xa0\xa0 Ensure the performance, quality, and responsiveness of applications.·\xa0\xa0\xa0\xa0\xa0\xa0 Identify and correct bottlenecks, fix bugs, and improve application performance.·\xa0\xa0\xa0\xa0\xa0\xa0 Help maintain code quality, organization, and automatization.·\xa0\xa0\xa0\xa0\xa0\xa0 Continuously discover, evaluate, and implement new technologies to maximize development efficiency.·\xa0\xa0\xa0\xa0\xa0\xa0 Unit-test code for robustness, including edge cases, usability, and general reliability.·\xa0\xa0\xa0\xa0\xa0\xa0 Work with APIs and third-party libraries.·\xa0\xa0\xa0\xa0\xa0\xa0 Participate in code reviews to ensure code quality and share knowledge.·\xa0\xa0\xa0\xa0\xa0\xa0 Stay up-to-date with the latest trends, architectural patterns, and best practices in iOS development.Expected skill set:·\xa0\xa0\xa0\xa0\xa0\xa0 Strong proficiency in Swift and/or Objective-C. (Specify preference if any, e.g., "Strong preference for Swift.") and AOS platform Java/Kotlin·\xa0\xa0\xa0\xa0\xa0\xa0 In-depth understanding of the iOS SDK, Cocoa Touch, and UIKit framework. ·\xa0\xa0\xa0\xa0\xa0\xa0 Experience integrating and working with core iOS & AOS communication frameworks·\xa0\xa0\xa0\xa0\xa0\xa0 Solid understanding of object-oriented programming (OOP) principles and design patterns (e.g., MVVM, MVC, VIPER). ·\xa0\xa0\xa0\xa0\xa0\xa0 Experience with RESTful APIs to connect iOS applications to backend services·\xa0\xa0\xa0\xa0\xa0\xa0 Strong understanding of memory management, threading, and performance optimization for iOS apps.Good to have:Familiarity with dependency injection frameworks. Experience with CI/CD pipelines for mobile applications. ·\xa0\xa0\xa0\xa0\xa0\xa0 Familiarity with Figma, Sketch, or other design tools.</p>'

cleaned = clean_html(raw_jd_html)
print("=== CLEANED TEXT ===")
print(cleaned)
