"""
Test compensation extraction with sample cases to verify the logic is working.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

# Test cases
test_cases = [
    {
        "name": "LPA Range",
        "text": "Salary: 12-15 LPA with excellent benefits",
        "payload": None,
        "is_internship": False,
    },
    {
        "name": "Stipend Monthly",
        "text": "Stipend: Rs.25000/month for this internship role",
        "payload": None,
        "is_internship": True,
    },
    {
        "name": "Best in Industry",
        "text": "We offer best in industry salary and competitive benefits",
        "payload": None,
        "is_internship": False,
    },
    {
        "name": "Competitive Compensation",
        "text": "Competitive compensation package commensurate with experience",
        "payload": None,
        "is_internship": False,
    },
    {
        "name": "Ashby Structured Payload",
        "text": "",
        "payload": {
            "compensation": {
                "summaryComponents": [
                    {
                        "compensationType": "Salary",
                        "minValue": 800000,
                        "maxValue": 1200000,
                        "currencyCode": "INR"
                    }
                ]
            }
        },
        "is_internship": False,
    },
    {
        "name": "Lever Salary Range",
        "text": "",
        "payload": {
            "salaryRange": {
                "min": 600000,
                "max": 900000,
                "currency": "INR"
            }
        },
        "is_internship": False,
    },
    {
        "name": "INR Full Range",
        "text": "Annual compensation: INR 800000 to 1200000",
        "payload": None,
        "is_internship": False,
    },
    {
        "name": "Single LPA",
        "text": "CTC: 10 LPA",
        "payload": None,
        "is_internship": False,
    },
    {
        "name": "Paid Internship",
        "text": "This is a paid internship with learning opportunities",
        "payload": None,
        "is_internship": True,
    },
]

print("=" * 70)
print("COMPENSATION EXTRACTION TEST")
print("=" * 70)

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print("-" * 70)

    result = extract_compensation_from_payload_and_text(
        text=test["text"],
        raw_payload=test["payload"],
        is_internship=test["is_internship"],
    )

    print(f"Compensation Type: {result.compensation_type}")
    print(f"Salary Disclosed:  {result.salary_disclosed}")

    if result.salary_min or result.salary_max:
        print(f"Salary Range:      {result.salary_min} - {result.salary_max} {result.salary_currency}")

    if result.stipend_min or result.stipend_max:
        print(f"Stipend Range:     {result.stipend_min} - {result.stipend_max}")

    if result.compensation_text:
        print(f"Compensation Text: {result.compensation_text}")

    if result.compensation_type == "UNDISCLOSED":
        print("Result: NO COMPENSATION EXTRACTED")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
