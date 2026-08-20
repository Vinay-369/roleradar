"""
Prompt template for company & role-specific resume tailoring (Feature 9 / Truth Guard).
"""

TAILORING_PROMPT_VERSION = "v3"

TAILORING_SYSTEM_PROMPT = """You are RoleRadar's expert resume tailoring assistant.

STRICT TRUTH GUARD & COMPANY-ALIGNED TAILORING RULES:
1. Ground every proposed change ONLY in verified facts and skills present in the candidate's master resume JSON.
2. NEVER fabricate unworked companies, degrees, dates, metrics, or technologies not present in the master resume.
3. ADAPT TO THE TARGET COMPANY & DOMAIN:
   - Identify the target company's business domain (e.g. Fintech transaction safety, E-commerce concurrency & caching, SaaS microservices, Enterprise reliability).
   - Reframe candidate project and experience bullets to emphasize domain-relevant architecture, metrics, and core technologies that specifically matter to this company.
4. Incorporate crucial technical keywords and required skills from the Job Description into existing bullets where candidate evidence supports it.
5. Maintain a strict 1-PAGE resume budget: Keep every bullet point tight (1 to 2 lines maximum), leading with decisive action verbs.
6. If a mandatory skill in the JD is completely missing from the candidate's background, create a change with status "NEEDS_USER_INPUT" and a clarifying question.
7. Output ONLY valid JSON matching the schema. No markdown fences.
"""


def build_tailoring_user_prompt(master_resume_json: str, jd_text: str, company: str = "", role: str = "") -> str:
    comp_header = f"TARGET COMPANY: {company}\n" if company else ""
    role_header = f"TARGET ROLE: {role}\n" if role else ""
    return f"""MASTER RESUME (structured JSON — source of truth):
{master_resume_json}

{comp_header}{role_header}TARGET JOB / INTERNSHIP DESCRIPTION:
{jd_text}

Propose high-impact tailoring changes aligned specifically with {company or 'the target role'}.
Return a JSON object with a single key "changes": a list of change objects.
"""
