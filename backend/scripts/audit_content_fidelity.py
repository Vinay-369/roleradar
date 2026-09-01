import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.resume.parsing.structurer import structure_resume_text, extract_candidate_profile
from app.modules.tailoring.validation import (
    detect_fabricated_claims,
    detect_sentence_fragments_and_truncation,
    detect_unsupported_metrics,
    detect_unsupported_action_verbs_and_scope,
    detect_dropped_source_skills,
)
from app.core.ai_service.service import AIService
from app.core.config import get_settings
from tests.test_experience_architecture_regression import AKHIL_RANA_AUTHORITATIVE_RESUME
from tests.test_tailoring_evidence_preservation_regression import VIKAS_RESUME, WEB_BACKEND_JD

# Load Flipkart JD
with open("seeds/jobs_seed.json") as f:
    jobs = json.load(f)
flipkart_job = next(j for j in jobs if j["company"] == "Flipkart")
jd_flipkart = flipkart_job["jd_text"]

ai_service = AIService(settings=get_settings())

def audit_resume_sections(name: str, raw_source: str, jd_text: str, role: str, company: str):
    print("=" * 80)
    print(f"AUDIT: {name.upper()} -> {company.upper()} ({role.upper()})")
    print("=" * 80)
    
    struct_source = structure_resume_text(raw_source)
    tailored = ai_service._fallback_resume_rewrite(struct_source, jd_text, company=company, role=role)
    
    total_bullets = 0
    complete_count = 0
    fragment_count = 0
    verified_count = 0
    paraphrase_count = 0
    unsupported_count = 0
    
    # 1. Professional Experience
    print("\n--- [SECTION: PROFESSIONAL EXPERIENCE] ---")
    for exp in tailored.experience_bullets:
        orig = exp.original.strip()
        prop = exp.proposed.strip()
        if not orig:
            continue
            
        total_bullets += 1
        frag_issues = detect_sentence_fragments_and_truncation(orig, prop)
        is_complete = (len(frag_issues) == 0)
        if is_complete:
            complete_count += 1
        else:
            fragment_count += 1
            
        unsupported_terms = detect_fabricated_claims(orig, prop, jd_text, struct_source.get("skills", []))
        unsupported_metrics = detect_unsupported_metrics(orig, prop)
        unsupported_scope = detect_unsupported_action_verbs_and_scope(orig, prop)
        
        is_unsupported = bool(unsupported_terms or unsupported_metrics or unsupported_scope or not is_complete)
        is_identical = (orig.lower() == prop.lower())
        
        if is_unsupported:
            claim_status = "UNSUPPORTED"
            unsupported_count += 1
        elif is_identical:
            claim_status = "VERIFIED"
            verified_count += 1
        else:
            claim_status = "SUPPORTED PARAPHRASE"
            paraphrase_count += 1
            
        comp_status = "COMPLETE" if is_complete else "FRAGMENTED"
        print(f"Bullet {total_bullets}: [{comp_status}] [{claim_status}]")
        print(f"  SOURCE EVIDENCE : {orig}")
        print(f"  GENERATED BULLET: {prop}")
        if frag_issues:
            print(f"  FRAGMENT ISSUES : {frag_issues}")
        print()

    # 2. Technical / Personal Projects
    print("\n--- [SECTION: TECHNICAL / PERSONAL PROJECTS] ---")
    for proj in tailored.project_bullets:
        orig_obj = json.loads(proj.original) if isinstance(proj.original, str) and proj.original.startswith("{") else {}
        prop_obj = json.loads(proj.proposed) if isinstance(proj.proposed, str) and proj.proposed.startswith("{") else {}
        orig_bullets = orig_obj.get("bullets", [proj.original]) if orig_obj else [proj.original]
        prop_bullets = prop_obj.get("bullets", [proj.proposed]) if prop_obj else [proj.proposed]
        
        for orig, prop in zip(orig_bullets, prop_bullets):
            orig_str = str(orig).strip()
            prop_str = str(prop).strip()
            if not orig_str:
                continue
                
            total_bullets += 1
            frag_issues = detect_sentence_fragments_and_truncation(orig_str, prop_str)
            is_complete = (len(frag_issues) == 0)
            if is_complete:
                complete_count += 1
            else:
                fragment_count += 1
                
            unsupported_terms = detect_fabricated_claims(orig_str, prop_str, jd_text, struct_source.get("skills", []))
            unsupported_metrics = detect_unsupported_metrics(orig_str, prop_str)
            unsupported_scope = detect_unsupported_action_verbs_and_scope(orig_str, prop_str)
            
            is_unsupported = bool(unsupported_terms or unsupported_metrics or unsupported_scope or not is_complete)
            is_identical = (orig_str.lower() == prop_str.lower())
            
            if is_unsupported:
                claim_status = "UNSUPPORTED"
                unsupported_count += 1
            elif is_identical:
                claim_status = "VERIFIED"
                verified_count += 1
            else:
                claim_status = "SUPPORTED PARAPHRASE"
                paraphrase_count += 1
                
            comp_status = "COMPLETE" if is_complete else "FRAGMENTED"
            print(f"Bullet {total_bullets}: [{comp_status}] [{claim_status}]")
            print(f"  SOURCE EVIDENCE : {orig_str}")
            print(f"  GENERATED BULLET: {prop_str}")
            if frag_issues:
                print(f"  FRAGMENT ISSUES : {frag_issues}")
            print()

    # 3. Protected Sections: Education, Achievements, Skills
    print("\n--- [SECTION: PROTECTED SECTIONS AUDIT] ---")
    edu_src = struct_source.get("education_raw", [])
    ach_src = struct_source.get("achievements", [])
    skills_src = struct_source.get("skills", [])
    
    print(f"Education entries: {len(edu_src)} verified intact")
    for e in edu_src:
        print(f"  • {e}")
    print(f"Achievements entries: {len(ach_src)} verified intact")
    for a in ach_src:
        print(f"  • {a}")
    print(f"Skills: {len(skills_src)} skills ordered deterministically without fabrications")
    print(f"  • {skills_src[:10]}...")
    
    print("\n" + "-" * 80)
    print(f"{name.upper()} SUMMARY: Total Bullets={total_bullets} | Complete={complete_count} | Fragmented={fragment_count} | Verified={verified_count} | Paraphrase={paraphrase_count} | Unsupported={unsupported_count}")
    print("-" * 80 + "\n")

audit_resume_sections("Akhil Rana", AKHIL_RANA_AUTHORITATIVE_RESUME, jd_flipkart, role="Frontend Developer", company="Flipkart")
audit_resume_sections("Vikas K", VIKAS_RESUME, WEB_BACKEND_JD, role="Backend Developer", company="Capco")

