"""
Authoritative Re-evaluation and Backfill Script for All Live Indian Opportunities.
Applies canonical normalization, unescapes entities, populates structured requirements,
qualifications, responsibilities, opportunity_type, and completeness_status deterministically.
"""
import asyncio
import html
import logging
import sys
sys.path.insert(0, "backend")
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.db.mongo import Collections
from app.modules.jobs.taxonomy import analyze_job_description
from app.modules.jobs.completeness import evaluate_opportunity_completeness, RecommendationQuality
from app.modules.jobs.compensation_extractor import extract_compensation_from_payload_and_text
from app.modules.jobs.location_normalization import is_india_opportunity, extract_country_from_location

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("resync_indian_inventory")

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Query all active Indian opportunities
    # Country == India or location has India markers
    cursor = db[Collections.JOBS].find({
        "verification_status": "VERIFIED_ACTIVE",
    })
    all_active = await cursor.to_list(length=10000)
    logger.info(f"Total active opportunities in DB: {len(all_active)}")

    # Filter to Indian opportunities
    indian_opps = [
        opp for opp in all_active
        if opp.get("country") == "India"
        or is_india_opportunity(opp.get("location", ""), opp.get("description", ""))
    ]
    logger.info(f"Total verified active Indian opportunities: {len(indian_opps)}")

    stats = {
        "total": len(indian_opps),
        "by_provider": {},
        "by_quality": {},
        "by_type": {"FULL_TIME": 0, "INTERNSHIP": 0},
        "with_salary_numeric": 0,
        "with_stipend_numeric": 0,
        "qualitative_comp": 0,
        "undisclosed_comp": 0,
        "updated_count": 0,
    }

    for opp in indian_opps:
        provider = opp.get("source", "unknown")
        stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1

        title = opp.get("title", "")
        desc = opp.get("description", "")
        raw_html = opp.get("raw_html", "")

        # Unescape HTML entities if needed (especially for greenhouse)
        if "&lt;" in desc or "&amp;" in desc or "&#" in desc:
            desc = html.unescape(desc)
        if "&lt;" in raw_html or "&amp;" in raw_html or "&#" in raw_html:
            raw_html = html.unescape(raw_html)

        # Detect opportunity_type
        title_lower = title.lower()
        is_intern = (
            opp.get("job_type") == "internship"
            or opp.get("opportunity_type") == "INTERNSHIP"
            or "intern" in title_lower
            or "trainee" in title_lower
            or "apprentice" in title_lower
        )
        opp_type = "INTERNSHIP" if is_intern else "FULL_TIME"
        stats["by_type"][opp_type] += 1

        # Run taxonomy analysis
        reqs = analyze_job_description(desc, title)
        responsibilities = reqs.responsibilities or opp.get("responsibilities") or []
        qualifications = reqs.qualifications or opp.get("qualifications") or []
        skills_required = list(dict.fromkeys(reqs.must_have_skills or reqs.required_skills or opp.get("skills_required") or []))
        skills_nice = list(dict.fromkeys(reqs.preferred_skills or opp.get("skills_nice_to_have") or []))

        # Re-evaluate compensation
        comp = extract_compensation_from_payload_and_text(
            text=f"{desc} {raw_html}",
            raw_payload=opp.get("raw_payload") or {},
            is_internship=is_intern,
        )

        salary_min = comp.salary_min if comp.salary_min is not None else opp.get("salary_min")
        salary_max = comp.salary_max if comp.salary_max is not None else opp.get("salary_max")
        stipend_min = comp.stipend_min if comp.stipend_min is not None else opp.get("stipend_min")
        stipend_max = comp.stipend_max if comp.stipend_max is not None else opp.get("stipend_max")
        comp_text = comp.compensation_text or opp.get("compensation_text")
        comp_type = comp.compensation_type or opp.get("compensation_type")

        if comp.salary_min or comp.salary_max or (salary_min and salary_min > 0):
            stats["with_salary_numeric"] += 1
        elif comp.stipend_min or comp.stipend_max or (stipend_min and stipend_min > 0):
            stats["with_stipend_numeric"] += 1
        elif comp_type == "QUALITATIVE":
            stats["qualitative_comp"] += 1
        else:
            stats["undisclosed_comp"] += 1

        # Preserve canonical experience
        exp_min = opp.get("experience_min")
        exp_max = opp.get("experience_max")
        if exp_min is None and reqs.min_years_experience is not None:
            exp_min = int(reqs.min_years_experience)
        if exp_max is None and reqs.max_years_experience is not None:
            exp_max = int(reqs.max_years_experience)
        if is_intern and exp_min is None:
            exp_min = 0
            exp_max = 2

        # Evaluate completeness deterministically
        eval_payload = {
            "title": title,
            "company": opp.get("company", ""),
            "location": opp.get("location", ""),
            "country": "India",
            "is_india_opportunity": True,
            "opportunity_type": opp_type,
            "description": desc,
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "skills_required": skills_required,
            "skills_nice_to_have": skills_nice,
            "verification_status": opp.get("verification_status", "VERIFIED_ACTIVE"),
            "apply_url": opp.get("apply_url", ""),
            "is_direct_apply": opp.get("is_direct_apply", True),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "stipend_min": stipend_min,
            "stipend_max": stipend_max,
            "compensation_text": comp_text,
            "experience_min": exp_min,
            "experience_max": exp_max,
        }

        comp_eval = evaluate_opportunity_completeness(eval_payload)
        quality_str = comp_eval.recommendation_quality.value
        completeness_str = comp_eval.source_completeness.value
        stats["by_quality"][completeness_str] = stats["by_quality"].get(completeness_str, 0) + 1

        # Prepare update dict
        update_doc = {
            "description": desc,
            "opportunity_type": opp_type,
            "job_type": "internship" if is_intern else "full_time",
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "structured_requirements": reqs.model_dump(mode="json"),
            "skills_required": skills_required,
            "skills_nice_to_have": skills_nice,
            "completeness_status": completeness_str,
            "recommendation_quality": quality_str,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "stipend_min": stipend_min,
            "stipend_max": stipend_max,
            "compensation_text": comp_text,
            "compensation_type": comp_type,
            "experience_min": exp_min,
            "experience_max": exp_max,
            "is_india_opportunity": True,
            "country": "India",
        }

        await db[Collections.JOBS].update_one(
            {"id": opp["id"]},
            {"$set": update_doc}
        )
        stats["updated_count"] += 1

    print("\n--- AUTHORITATIVE RESYNC RESULTS ---")
    print(f"Total Indian records processed: {stats['total']}")
    print(f"By Provider: {stats['by_provider']}")
    print(f"By Quality: {stats['by_quality']}")
    print(f"By Type: {stats['by_type']}")
    print(f"Numeric Salary: {stats['with_salary_numeric']}")
    print(f"Numeric Stipend: {stats['with_stipend_numeric']}")
    print(f"Qualitative Comp: {stats['qualitative_comp']}")
    print(f"Undisclosed Comp: {stats['undisclosed_comp']}")
    print(f"Total Updated in DB: {stats['updated_count']}")

if __name__ == "__main__":
    asyncio.run(main())
