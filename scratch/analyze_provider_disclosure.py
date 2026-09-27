"""
Deep diagnostic: Check what compensation data ATS providers are actually sending.
This will show raw API responses to see if providers disclose salary or not.
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

async def check_provider_disclosure():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings
    from app.db.mongo import Collections
    from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text

    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    print("=" * 80)
    print("ATS PROVIDER COMPENSATION DISCLOSURE ANALYSIS")
    print("=" * 80)

    # Get jobs from each provider
    providers = ['ashby', 'greenhouse', 'lever', 'smartrecruiters', 'curated_benchmark']

    for provider in providers:
        print(f"\n{'='*80}")
        print(f"PROVIDER: {provider.upper()}")
        print(f"{'='*80}")

        cursor = db[Collections.JOBS].find({"source": provider}).limit(5)
        jobs = await cursor.to_list(length=5)

        if not jobs:
            print(f"No jobs found from {provider}")
            continue

        print(f"Found {len(jobs)} sample jobs\n")

        for i, job in enumerate(jobs, 1):
            print(f"\n{i}. {job.get('title', 'Unknown')[:50]}")
            print(f"   Company: {job.get('company', 'Unknown')}")
            print("-" * 80)

            # Check database fields
            print("\nCURRENT DATABASE VALUES:")
            print(f"  salary_min: {job.get('salary_min')}")
            print(f"  salary_max: {job.get('salary_max')}")
            print(f"  compensation_text: {job.get('compensation_text')}")
            print(f"  compensation_type: {job.get('compensation_type')}")

            # Check raw_payload
            raw_payload = job.get('raw_payload')
            print("\nRAW PAYLOAD COMPENSATION FIELDS:")

            if raw_payload:
                # Ashby format
                if 'compensation' in raw_payload:
                    comp_obj = raw_payload['compensation']
                    print(f"  Ashby compensation object found:")
                    print(f"    summaryComponents: {comp_obj.get('summaryComponents')}")
                    print(f"    scrapeableCompensationSalarySummary: {comp_obj.get('scrapeableCompensationSalarySummary')}")
                    print(f"    compensationTierSummary: {comp_obj.get('compensationTierSummary')}")

                # Greenhouse format
                if 'pay' in raw_payload:
                    pay_obj = raw_payload['pay']
                    print(f"  Greenhouse pay object found:")
                    print(f"    min_value: {pay_obj.get('min_value')}")
                    print(f"    max_value: {pay_obj.get('max_value')}")
                    print(f"    unit: {pay_obj.get('unit')}")

                # Lever format
                if 'salaryRange' in raw_payload:
                    sal_obj = raw_payload['salaryRange']
                    print(f"  Lever salaryRange object found:")
                    print(f"    min: {sal_obj.get('min')}")
                    print(f"    max: {sal_obj.get('max')}")
                    print(f"    currency: {sal_obj.get('currency')}")

                # SmartRecruiters format
                if 'customField' in raw_payload:
                    cf = raw_payload['customField']
                    print(f"  SmartRecruiters customField found:")
                    print(f"    {json.dumps(cf, indent=4)[:200]}...")

                # Check if any compensation field exists
                has_structured_comp = any([
                    'compensation' in raw_payload,
                    'pay' in raw_payload,
                    'salaryRange' in raw_payload,
                    'customField' in raw_payload
                ])

                if not has_structured_comp:
                    print(f"  ✗ No structured compensation fields in raw_payload")
                    print(f"  Available fields: {list(raw_payload.keys())[:10]}")
            else:
                print(f"  ✗ No raw_payload stored")

            # Test extraction from JD text
            jd_text = job.get('jd_text') or job.get('description') or ''
            if jd_text:
                print("\nTESTING EXTRACTION FROM JD TEXT:")

                # Look for compensation patterns manually
                import re

                # LPA patterns
                lpa_matches = re.findall(r'(?:₹|INR|Rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:-|to)\s*(?:₹|INR|Rs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|per\s*annum)', jd_text, re.I)
                if lpa_matches:
                    print(f"  Found LPA pattern in text: {lpa_matches[0]}")

                # Stipend patterns
                stipend_matches = re.findall(r'(?:stipend|salary)\s*[:\-]?\s*(?:₹|INR|Rs\.?)\s*([0-9,]{4,})\s*(?:/|\s*per\s*)(?:month|pm)', jd_text, re.I)
                if stipend_matches:
                    print(f"  Found stipend pattern in text: {stipend_matches[0]}")

                # Qualitative patterns
                qual_matches = re.search(r'best\s*in\s*industry|competitive\s*(?:salary|compensation)|commensurate\s*with', jd_text, re.I)
                if qual_matches:
                    print(f"  Found qualitative pattern: {qual_matches.group()}")

                if not lpa_matches and not stipend_matches and not qual_matches:
                    print(f"  ✗ No compensation patterns found in JD text")
                    print(f"  JD text length: {len(jd_text)} chars")
                    print(f"  First 300 chars: {jd_text[:300]}...")

                # Now test our extractor
                is_intern = job.get('job_type') == 'internship'
                comp = extract_compensation_from_payload_and_text(
                    text=jd_text,
                    raw_payload=raw_payload,
                    is_internship=is_intern,
                )

                print("\nEXTRACTOR RESULT:")
                print(f"  Type: {comp.compensation_type}")
                print(f"  salary_min: {comp.salary_min}")
                print(f"  salary_max: {comp.salary_max}")
                print(f"  stipend_min: {comp.stipend_min}")
                print(f"  compensation_text: {comp.compensation_text}")

                if comp.compensation_type == "UNDISCLOSED":
                    print(f"  ✗ Extractor found nothing")
                else:
                    print(f"  ✓ Extractor found compensation!")

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)

    for provider in providers:
        total = await db[Collections.JOBS].count_documents({"source": provider})
        with_payload = await db[Collections.JOBS].count_documents({
            "source": provider,
            "raw_payload": {"$exists": True, "$ne": None}
        })
        with_salary = await db[Collections.JOBS].count_documents({
            "source": provider,
            "$or": [
                {"salary_min": {"$exists": True, "$ne": None}},
                {"salary_max": {"$exists": True, "$ne": None}}
            ]
        })
        with_any_comp = await db[Collections.JOBS].count_documents({
            "source": provider,
            "$or": [
                {"salary_min": {"$exists": True, "$ne": None}},
                {"compensation_text": {"$exists": True, "$ne": None}}
            ]
        })

        if total > 0:
            print(f"\n{provider.upper()}:")
            print(f"  Total jobs: {total}")
            print(f"  With raw_payload: {with_payload} ({with_payload/total*100:.1f}%)")
            print(f"  With salary data: {with_salary} ({with_salary/total*100:.1f}%)")
            print(f"  With any compensation: {with_any_comp} ({with_any_comp/total*100:.1f}%)")
            print(f"  Disclosure rate: {with_any_comp/total*100:.1f}%")

    await client.close()

if __name__ == "__main__":
    asyncio.run(check_provider_disclosure())
