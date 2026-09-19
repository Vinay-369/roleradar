import asyncio
import json
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")
from app.db.mongo import get_db, connect_to_mongo, close_mongo_connection
from app.modules.jobs.description_presentation import (
    normalize_job_description_presentation,
    clean_raw_description,
)

async def main():
    try:
        await connect_to_mongo()
        db = get_db()
        
        # 1. Blueberry Full Stack Developer
        bb = await db.jobs.find_one({
            "company": {"$regex": "Blueberry", "$options": "i"},
            "title": {"$regex": "Full Stack", "$options": "i"}
        })
        if not bb:
            bb = await db.jobs.find_one({"company": {"$regex": "Blueberry", "$options": "i"}})

        print("=" * 80, flush=True)
        print("TARGET 1: BLUEBERRY JOB", flush=True)
        print("=" * 80, flush=True)
        if bb:
            print(f"ID: {bb.get('id')}", flush=True)
            print(f"Title: {bb.get('title')}", flush=True)
            print(f"Company: {bb.get('company')}", flush=True)
            print(f"Location: {bb.get('location')}", flush=True)
            print(f"Canonical Responsibilities ({len(bb.get('responsibilities', []))}): {bb.get('responsibilities')}", flush=True)
            print(f"Canonical Qualifications ({len(bb.get('qualifications', []))}): {bb.get('qualifications')}", flush=True)
            print(f"Canonical Skills Required: {bb.get('skills_required')}", flush=True)
            print(f"Canonical Skills Preferred: {bb.get('skills_nice_to_have')}", flush=True)
            
            raw_desc = bb.get("description", "")
            print("\n--- RAW / SOURCE DESCRIPTION ---", flush=True)
            print(raw_desc, flush=True)
            
            res = normalize_job_description_presentation(
                description=raw_desc,
                responsibilities=bb.get("responsibilities"),
                qualifications=bb.get("qualifications"),
                skills_required=bb.get("skills_required"),
                skills_nice_to_have=bb.get("skills_nice_to_have"),
            )
            
            print("\n--- NORMALIZED PRESENTATION ---", flush=True)
            print(f"Job Summary Title: {res.summary.title if res.summary else None}", flush=True)
            if res.summary:
                for item in res.summary.items:
                    print(f"  - {item.text}", flush=True)
            print(f"\nFinal Responsibilities ({len(res.responsibilities)}):", flush=True)
            for r in res.responsibilities:
                print(f"  • {r}", flush=True)
            print(f"\nFinal Qualifications ({len(res.qualifications)}):", flush=True)
            for q in res.qualifications:
                print(f"  • {q}", flush=True)
            print(f"\nAdditional Info Title: {res.additional_info.title if res.additional_info else None}", flush=True)
            if res.additional_info:
                for item in res.additional_info.items:
                    print(f"  - {item.text}", flush=True)
            print(f"\nDetailed Sections ({len(res.detailed_sections)}):", flush=True)
            for idx, sec in enumerate(res.detailed_sections):
                print(f"  Section {idx+1}: [{sec.title}]", flush=True)
                for item in sec.items:
                    print(f"    {'• ' if item.is_bullet else '  '}{item.text}", flush=True)

            # Verification assertions
            titles = [sec.title.lower() for sec in res.detailed_sections if sec.title]
            assert titles.count("job description") == 0, "Repeated JOB DESCRIPTION found!"
            assert titles.count("qualifications") == 0, "Repeated QUALIFICATIONS found!"
            
            # Check duplicate responsibilities
            resp_set = {re.sub(r'[^a-z0-9]', '', r.lower()) for r in res.responsibilities}
            detailed_texts = [re.sub(r'[^a-z0-9]', '', i.text.lower()) for sec in res.detailed_sections for i in sec.items]
            for r_norm in resp_set:
                if r_norm:
                    assert r_norm not in detailed_texts, f"Responsibility duplicated in detailed section: {r_norm}"

            print("\n>>> BLUEBERRY VERIFICATION PASSED: No repeated headings, no duplicated canonical lists.", flush=True)
        else:
            print("ERROR: Blueberry record not found!", flush=True)

        # 2. Internship (find one with rich description)
        print("\n" + "=" * 80, flush=True)
        print("TARGET 2: REAL INTERNSHIP", flush=True)
        print("=" * 80, flush=True)
        intern = await db.jobs.find_one({
            "opportunity_type": "INTERNSHIP",
            "$expr": {"$gt": [{"$strLenCP": {"$ifNull": ["$description", ""]}}, 250]}
        })
        if not intern:
            intern = await db.jobs.find_one({"opportunity_type": "INTERNSHIP"})

        if intern:
            print(f"ID: {intern.get('id')}", flush=True)
            print(f"Title: {intern.get('title')}", flush=True)
            print(f"Company: {intern.get('company')}", flush=True)
            print(f"Location: {intern.get('location')}", flush=True)
            print(f"Canonical Responsibilities ({len(intern.get('responsibilities', []))}): {intern.get('responsibilities')}", flush=True)
            print(f"Canonical Qualifications ({len(intern.get('qualifications', []))}): {intern.get('qualifications')}", flush=True)
            print(f"Canonical Skills Required: {intern.get('skills_required')}", flush=True)
            
            raw_desc = intern.get("description", "")
            print("\n--- RAW / SOURCE DESCRIPTION ---", flush=True)
            print(raw_desc, flush=True)
            
            res = normalize_job_description_presentation(
                description=raw_desc,
                responsibilities=intern.get("responsibilities"),
                qualifications=intern.get("qualifications"),
                skills_required=intern.get("skills_required"),
                skills_nice_to_have=intern.get("skills_nice_to_have"),
            )
            
            print("\n--- NORMALIZED PRESENTATION ---", flush=True)
            print(f"Job Summary Title: {res.summary.title if res.summary else None}", flush=True)
            if res.summary:
                for item in res.summary.items:
                    print(f"  - {item.text}", flush=True)
            print(f"\nFinal Responsibilities ({len(res.responsibilities)}):", flush=True)
            for r in res.responsibilities:
                print(f"  • {r}", flush=True)
            print(f"\nFinal Qualifications ({len(res.qualifications)}):", flush=True)
            for q in res.qualifications:
                print(f"  • {q}", flush=True)
            print(f"\nAdditional Info Title: {res.additional_info.title if res.additional_info else None}", flush=True)
            if res.additional_info:
                for item in res.additional_info.items:
                    print(f"  - {item.text}", flush=True)
            print(f"\nDetailed Sections ({len(res.detailed_sections)}):", flush=True)
            for idx, sec in enumerate(res.detailed_sections):
                print(f"  Section {idx+1}: [{sec.title}]", flush=True)
                for item in sec.items:
                    print(f"    {'• ' if item.is_bullet else '  '}{item.text}", flush=True)

            # Verification assertions
            titles = [sec.title.lower() for sec in res.detailed_sections if sec.title]
            assert titles.count("job description") == 0, "Repeated JOB DESCRIPTION in internship!"
            assert titles.count("qualifications") == 0, "Repeated QUALIFICATIONS in internship!"

            print("\n>>> INTERNSHIP VERIFICATION PASSED: Clean hierarchy without redundant titles.", flush=True)
        else:
            print("ERROR: No internship record found!", flush=True)

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
