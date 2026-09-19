import asyncio
import httpx
import json
import re
import sys
sys.path.insert(0, r"c:\VINAY\roleradar\backend")
sys.stdout.reconfigure(encoding="utf-8")

from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.jobs.smartrecruiters_provider import SmartRecruitersJobProvider, _clean_html_description
from app.modules.jobs.skill_vocabulary import extract_skills_from_text
from app.modules.jobs.taxonomy import _extract_experience_from_text
from app.modules.jobs.completeness import evaluate_opportunity_completeness

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["roleradar"]
    coll = db["jobs"]

    print("=================================================================")
    print("STEP 1: INSPECT AND HYDRATE 23 PARTIAL SMARTRECRUITERS RECORDS")
    print("=================================================================")
    
    partial_jobs = await coll.find({
        "country": "India",
        "verification_status": "VERIFIED_ACTIVE",
        "completeness_status": "VERIFIED_PARTIAL"
    }).to_list(length=None)

    print(f"Found {len(partial_jobs)} VERIFIED_PARTIAL records in DB.")

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        for idx, job in enumerate(partial_jobs, 1):
            jid = job.get("id")
            title = job.get("title")
            company = job.get("company")
            source = job.get("source")
            desc = job.get("description") or ""
            resps = job.get("responsibilities") or []
            quals = job.get("qualifications") or []
            skills = job.get("skills_required") or []
            
            print(f"\n[{idx}/{len(partial_jobs)}] ID: {jid}")
            print(f"  Company: {company} | Title: {title}")
            print(f"  Current DB Desc Len: {len(desc)} | Resps: {len(resps)} | Quals: {len(quals)} | Skills: {len(skills)}")

            if source == "smartrecruiters" and jid.startswith("smartrecruiters_"):
                parts = jid.split("_")
                if len(parts) >= 3:
                    company_sub = parts[1]
                    posting_id = parts[2]
                    
                    url = f"https://api.smartrecruiters.com/v1/companies/{company_sub}/postings/{posting_id}"
                    try:
                        resp = await http_client.get(url)
                        if resp.status_code == 200:
                            data = resp.json()
                            jobAd = data.get("jobAd", {})
                            sections = jobAd.get("sections", {})
                            
                            company_desc_raw = sections.get("companyDescription", {}).get("text", "")
                            job_desc_raw = sections.get("jobDescription", {}).get("text", "")
                            qualifications_raw = sections.get("qualifications", {}).get("text", "")
                            additional_info_raw = sections.get("additionalInformation", {}).get("text", "")
                            
                            company_desc = _clean_html_description(company_desc_raw)
                            job_desc = _clean_html_description(job_desc_raw)
                            qualifications_text = _clean_html_description(qualifications_raw)
                            additional_info = _clean_html_description(additional_info_raw)
                            
                            combined_desc = "\n\n".join([t for t in [company_desc, job_desc, qualifications_text, additional_info] if t]).strip()
                            
                            def split_bullets(text):
                                lines = []
                                for l in re.split(r"[\r\n•\-\*]+", text):
                                    cleaned = l.strip()
                                    if len(cleaned) > 10:
                                        lines.append(cleaned)
                                return lines

                            parsed_resps = split_bullets(job_desc)
                            parsed_quals = split_bullets(qualifications_text)
                            
                            full_text_for_skills = f"{job_desc} {qualifications_text} {additional_info}"
                            extracted_skills = extract_skills_from_text(full_text_for_skills)
                            
                            exp_min, exp_max, exp_raw = _extract_experience_from_text(f"{qualifications_text} {additional_info} {job_desc}")
                            
                            print(f"  -> Fetched Live ATS jobAd: Total chars = {len(combined_desc)}")
                            print(f"  -> Extracted: {len(parsed_resps)} resps, {len(parsed_quals)} quals, {len(extracted_skills)} skills, Exp: min={exp_min}, max={exp_max}")
                            
                            # Assess completeness with full text
                            test_opp = dict(job)
                            test_opp["description"] = combined_desc
                            test_opp["responsibilities"] = parsed_resps
                            test_opp["qualifications"] = parsed_quals
                            test_opp["skills_required"] = extracted_skills
                            test_opp["experience_min"] = exp_min
                            test_opp["experience_max"] = exp_max
                            
                            comp_res = evaluate_opportunity_completeness(test_opp)
                            status = comp_res.source_completeness.value
                            print(f"  -> New Completeness: {status} (Quality: {comp_res.recommendation_quality.value})")
                            
                            update_fields = {
                                "description": combined_desc,
                                "responsibilities": parsed_resps,
                                "qualifications": parsed_quals,
                                "skills_required": extracted_skills,
                                "completeness_status": status,
                                "completeness": comp_res.model_dump()
                            }
                            if exp_min is not None:
                                update_fields["experience_min"] = exp_min
                            if exp_max is not None:
                                update_fields["experience_max"] = exp_max
                                
                            await coll.update_one({"id": jid}, {"$set": update_fields})
                            print(f"  -> Updated in DB successfully.")
                        else:
                            print(f"  -> SmartRecruiters API returned HTTP {resp.status_code}")
                    except Exception as e:
                        print(f"  -> Failed to fetch/parse SmartRecruiters detail: {e}")

    print("\n=================================================================")
    print("STEP 2: AUDIT & CLEAN THE 5 CRED NUMERIC SALARY RECORDS")
    print("=================================================================")
    cred_jobs = await coll.find({
        "country": "India",
        "company": {"$regex": "cred", "$options": "i"},
        "salary_disclosed": True
    }).to_list(length=None)

    print(f"Found {len(cred_jobs)} Cred jobs with salary_disclosed=True in DB:")
    for cj in cred_jobs:
        cid = cj.get("id")
        ctitle = cj.get("title")
        smin = cj.get("salary_min")
        smax = cj.get("salary_max")
        url = cj.get("apply_url") or cj.get("direct_apply_url") or cj.get("url")
        desc = cj.get("description") or ""
        print(f"\nID: {cid} | Title: {ctitle}")
        print(f"  Salary: {smin} - {smax}")
        print(f"  URL: {url}")
        
        loan_matches = re.findall(r"(?:loan|offering|credit|lakh|₹)[\w\s,₹\-]+", desc, re.I)
        print(f"  Matching loan/lending snippets: {loan_matches[:3]}")

        await coll.update_one({"id": cid}, {
            "$set": {
                "salary_min": None,
                "salary_max": None,
                "salary_disclosed": False,
                "compensation_type": "UNDISCLOSED"
            }
        })
        print(f"  -> Restored to salary_disclosed=False, salary=None in DB.")

    print("\n=================================================================")
    print("STEP 3: FIX 'Internal Audit' INTERNSHIP MISCLASSIFICATION")
    print("=================================================================")
    paytm_audit = await coll.find_one({"id": "lever_paytm_12ba9ea0-bc18-4a55-8d80-b7d338b8c9f0"})
    if paytm_audit:
        print(f"Paytm Audit Job in DB: {paytm_audit.get('title')}")
        print(f"  Current opportunity_type: {paytm_audit.get('opportunity_type')}")
        print(f"  Current job_type: {paytm_audit.get('job_type')}")
        await coll.update_one({"id": "lever_paytm_12ba9ea0-bc18-4a55-8d80-b7d338b8c9f0"}, {
            "$set": {
                "opportunity_type": "FULL_TIME",
                "job_type": "full_time"
            }
        })
        print("  -> Updated Paytm Internal Audit to FULL_TIME in DB.")

    print("\n=================================================================")
    print("STEP 4: VERIFY RECONCILED INVENTORY IN DB")
    print("=================================================================")
    all_india = await coll.find({"country": "India", "verification_status": "VERIFIED_ACTIVE"}).to_list(length=None)
    print(f"Total VERIFIED_ACTIVE India documents: {len(all_india)}")
    
    from collections import Counter
    types = Counter(j.get("opportunity_type") for j in all_india)
    print(f"Opportunity Types: {types}")
    
    completeness_counts = Counter(j.get("completeness_status") for j in all_india)
    print(f"Completeness Statuses: {completeness_counts}")
    
    # Primary Recommendations (excluding INSUFFICIENT)
    primary = [j for j in all_india if j.get("completeness_status") != "INSUFFICIENT"]
    print(f"Primary Recommendations (completeness != INSUFFICIENT): {len(primary)}")
    primary_types = Counter(j.get("opportunity_type") for j in primary)
    print(f"Primary Recommendations by Type: {primary_types}")
    
    # Check salary disclosure across primary recommendations
    sal_disclosed = [j for j in primary if j.get("salary_disclosed") or j.get("salary_min") is not None]
    print(f"Salary Disclosed in Primary Recommendations: {len(sal_disclosed)}")
    
    # Check internships vs jobs
    internships = [j for j in primary if j.get("opportunity_type") == "INTERNSHIP"]
    jobs = [j for j in primary if j.get("opportunity_type") != "INTERNSHIP"]
    print(f"Reconciled Equation: {len(jobs)} Jobs + {len(internships)} Internships = {len(primary)} Primary Recommendations")
    print(f"Total in DB = {len(primary)} Primary Recommendations + {len(all_india) - len(primary)} Insufficient = {len(all_india)}")

if __name__ == "__main__":
    asyncio.run(main())
