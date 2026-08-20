"""
Prompt template for company-specific interview preparation with 3 categorized rounds.
"""

INTERVIEW_PROMPT_VERSION = "v2"

INTERVIEW_SYSTEM_PROMPT = """You are RoleRadar's expert interview preparation coach.

RULES:
1. Generate realistic, high-frequency interview questions tailored to the TARGET COMPANY and TARGET ROLE, grounded in the candidate's actual background and skills.
2. Group all questions into 3 distinct categories:
   - "technical": Core technical questions, data structures, algorithms, coding architecture, framework concepts, API and database optimizations.
   - "managerial": Technical leadership, system design trade-offs, project defense, sprint planning, handling scale and deadlines.
   - "hr": Behavioral & culture fit, "Tell me about yourself", "Why this company?", conflict resolution, strengths/weaknesses using the STAR framework (Situation, Task, Action, Result).
3. For EVERY question, you MUST provide:
   - strategy: Step-by-step framework on how to approach and structure the answer.
   - sample_answer: A concrete, realistic model response tailored to the candidate's skills and the company's domain.
   - pitfalls: 1-2 critical mistakes to avoid when answering this question.
   - star_hint: Brief summary hint.
4. Output ONLY valid JSON matching the schema. No markdown fences.
"""


def build_interview_user_prompt(resume_summary: str, jd_text: str, target_role: str, company: str = "") -> str:
    company_line = f"TARGET COMPANY: {company}\n" if company else "TARGET COMPANY: Industry Standard Enterprise\n"
    return f"""CANDIDATE PROFILE & RESUME:
{resume_summary}

TARGET ROLE: {target_role}
{company_line}

JOB CONTEXT:
{jd_text}

Generate 9-12 highly relevant interview questions (3-4 technical, 3-4 managerial, 3-4 hr) tailored for {company or 'the target role'}.
Return a JSON object with a single key "questions": a list of question objects with (question, category, star_hint, strategy, sample_answer, pitfalls).
"""
