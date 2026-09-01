"""
Prompt template for company & role-specific resume tailoring.
Includes:
- v8_compact_fast: High-speed compact diff generation (350-500 tokens output)
- v7_structured: Wholesale structured fallback engine
"""

TAILORING_PROMPT_VERSION = "v8_compact_fast"

COMPACT_TAILORING_SYSTEM_PROMPT = """You are RoleRadar's expert enterprise ATS optimization and technical recruiter engine.
Your mission is to boost the candidate's ATS Match Score to 90%+ with 100% truthfulness and zero fabrication.

COMPACT TAILORING PLAN INSTRUCTIONS:
1. Summary:
   - Provide a concise 1-2 sentence tailored professional summary aligned with the target role and backed by verified candidate experience.

2. Targeted Bullet Rewrites (ONLY for bullets that benefit from alignment):
   - You do NOT need to rewrite all bullets.
   - For bullets that can be sharpened with stronger action verbs or better JD context, output ONLY:
     {"bullet_index": <int>, "proposed": "<rewritten bullet>", "reason": "<short justification>"}
   - Standardized Formula: ACTION VERB + TASK + METHOD/TECHNOLOGY + RESULT/PURPOSE.
   - Do NOT echo back the original text.
   - Do NOT output unchanged bullets.

3. Strict Anti-Fabrication & Metric Preservation:
   - PRESERVE ALL METRICS, DATES, AND PERCENTAGES (e.g. 70%, 99.8%, 40k, $200k+, 60 FPS).
   - NEVER invent new technologies or tools that were not in the candidate's background.

4. Unmatched Gaps:
   - List any mandatory JD skills that the candidate completely lacks in `unmatched_gaps`. NEVER hallucinate them into candidate bullets.

Output ONLY valid JSON matching this schema:
{
  "summary": "...",
  "experience_rewrites": [{"bullet_index": 0, "proposed": "...", "reason": "..."}],
  "project_rewrites": [{"bullet_index": 0, "proposed": "...", "reason": "..."}],
  "unmatched_gaps": ["..."]
}
"""

TAILORING_SYSTEM_PROMPT = COMPACT_TAILORING_SYSTEM_PROMPT


def build_compact_tailoring_user_prompt(
    candidate_summary: str,
    experience_bullets: list[dict],
    project_bullets: list[dict],
    skills: list[str],
    jd_role: str,
    jd_company: str,
    jd_must_haves: list[str],
    jd_responsibilities: list[str],
) -> str:
    exp_formatted = "\n".join([f"[{b['index']}] ({b.get('entity', '')}) {b['text']}" for b in experience_bullets])
    proj_formatted = "\n".join([f"[{b['index']}] ({b.get('entity', '')}) {b['text']}" for b in project_bullets])
    must_haves = ", ".join(jd_must_haves[:10])
    resps = "\n".join([f"- {r}" for r in jd_responsibilities[:5]])

    return f"""TARGET ROLE: {jd_role} at {jd_company}
KEY REQUIREMENTS: {must_haves}
KEY RESPONSIBILITIES:
{resps}

CANDIDATE PROFILE:
Summary: {candidate_summary}
Verified Skills: {', '.join(skills[:25])}

EXPERIENCE BULLETS:
{exp_formatted or '(None)'}

PROJECT BULLETS:
{proj_formatted or '(None)'}

Output the compact JSON tailoring plan. Rewrite only bullets that benefit from JD alignment."""


def build_tailoring_user_prompt(editable_resume_json: str, jd_text: str, company: str = "", role: str = "") -> str:
    comp_header = f"TARGET COMPANY: {company}\n" if company else ""
    role_header = f"TARGET ROLE: {role}\n" if role else ""
    return f"""EDITABLE RESUME SUB-OBJECT:
{editable_resume_json}

{comp_header}{role_header}TARGET JOB DESCRIPTION:
{jd_text}

Output the compact JSON tailoring plan. Rewrite only bullets that benefit from JD alignment."""

