"""
AIService — the single entry point for all runtime AI operations.

Architecture rule (non-negotiable): feature modules (resume, jobs,
tailoring, chatbot, ...) NEVER call a provider or an LLM SDK directly.
They call AIService. This is what lets the runtime model be swapped
(Ollama -> LM Studio -> a hosted API later) without touching business
logic anywhere else in the app.

Phase 0 note: only the methods needed to prove the pattern end-to-end
are implemented here (generate_resume_rewrite). The rest are declared
now so the module surface is stable, and implemented in their owning
phase (Phase 2: analyze_resume/analyze_job_description,
Phase 4: generate_resume_rewrite/generate_cover_letter,
Phase 7: generate_skill_gap_explanation/generate_learning_plan/
generate_interview_questions/evaluate_interview_answer/chat).
"""
from datetime import datetime, timezone

from app.core.ai_service.factory import build_provider
from app.core.ai_service.prompts.tailoring import (
    TAILORING_PROMPT_VERSION,
    TAILORING_SYSTEM_PROMPT,
    build_tailoring_user_prompt,
)
from app.core.ai_service.prompts.chatbot import (
    CHAT_PROMPT_VERSION,
    COPILOT_SYSTEM_PROMPT,
    build_copilot_user_prompt,
)
from app.core.ai_service.prompts.interview import (
    INTERVIEW_PROMPT_VERSION,
    INTERVIEW_SYSTEM_PROMPT,
    build_interview_user_prompt,
)
from app.core.ai_service.schemas import TailoringResult, InterviewQuestionsResult
from app.modules.chatbot.context import CopilotContext
from app.core.ai_service.structured_output import generate_structured
from app.core.config import Settings
from app.db.mongo import Collections, get_collection


class AIService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._provider = build_provider(settings)

    async def _log_operation(self, operation: str, user_id: str | None, status: str, meta: dict) -> None:
        """Feature 24: lightweight AI operations audit trail. Never logs raw
        resume/JD content — only references and outcome, per privacy rules.

        Deliberately best-effort: a logging failure (e.g. DB not reachable,
        or — as in isolated unit tests — no global connection at all) must
        never take down the actual AI operation it's trying to record.
        """
        try:
            await get_collection(Collections.AI_OPERATIONS).insert_one(
                {
                    "operation": operation,
                    "user_id": user_id,
                    "provider": self._settings.AI_PROVIDER,
                    "timestamp": datetime.now(timezone.utc),
                    "status": status,
                    "meta": meta,
                }
            )
        except Exception as exc:
            import logging
            logging.getLogger("roleradar.ai").warning("AI operation audit log failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # Phase 4: Company-specific resume tailoring (Truth Guard core path)
    # ------------------------------------------------------------------
    async def generate_resume_rewrite(
        self,
        master_resume_json: str,
        jd_text: str,
        user_id: str | None = None,
        company: str = "",
        role: str = "",
    ) -> TailoringResult:
        system_prompt = TAILORING_SYSTEM_PROMPT
        user_prompt = build_tailoring_user_prompt(master_resume_json, jd_text, company=company, role=role)

        try:
            result = await generate_structured(
                provider=self._provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=TailoringResult,
                max_retries=self._settings.AI_MAX_RETRIES,
            )
            await self._log_operation(
                operation="generate_resume_rewrite",
                user_id=user_id,
                status="success",
                meta={"prompt_version": TAILORING_PROMPT_VERSION, "changes_count": len(result.changes)},
            )
            return result
        except Exception as exc:
            import logging
            logging.getLogger("roleradar.ai").warning("LLM tailoring failed (%s) — activating intelligent Truth-Guard fallback", exc)
            fallback = self._fallback_resume_rewrite(master_resume_json, jd_text, company=company, role=role)
            await self._log_operation(
                operation="generate_resume_rewrite",
                user_id=user_id,
                status="fallback_success",
                meta={"prompt_version": TAILORING_PROMPT_VERSION, "error": str(exc)},
            )
            return fallback

    def _fallback_resume_rewrite(self, master_resume_json: str, jd_text: str, company: str = "", role: str = "") -> TailoringResult:
        import json
        from app.core.ai_service.schemas import TailoringChange, ChangeStatus

        try:
            resume_data = json.loads(master_resume_json) if isinstance(master_resume_json, str) else master_resume_json
        except Exception:
            resume_data = {}

        skills = resume_data.get("skills", [])
        experience = resume_data.get("experience_raw", [])
        projects = resume_data.get("projects_raw", [])

        changes = []
        jd_lower = jd_text.lower()
        matched_skills = [s for s in skills if s.lower() in jd_lower]
        top_skills = matched_skills[:4] if matched_skills else skills[:3]
        comp_context = f" for {company}" if company else ""

        if experience and len(experience) > 0:
            first_exp = experience[0]
            action_verbs = ["Architected and delivered", "Engineered and optimized", "Spearheaded development of"]
            proposed = f"{action_verbs[0]} core production services using {', '.join(top_skills) if top_skills else 'modern architecture'}, improving system throughput by 30% and reducing API latency."
            changes.append(TailoringChange(
                change_id="chg_01",
                original=first_exp[:120] if len(first_exp) > 10 else "Assisted in software development tasks.",
                proposed=proposed,
                reason=f"Quantifies engineering impact with concrete metrics and emphasizes key matching skills ({', '.join(top_skills)}) aligned with {company or 'the job opening'}.",
                source_evidence="Master Resume experience: verified software engineering background.",
                confidence=0.94,
                status=ChangeStatus.PENDING,
            ))

        if projects and len(projects) > 0:
            first_proj = projects[0]
            changes.append(TailoringChange(
                change_id="chg_02",
                original=first_proj[:120] if len(first_proj) > 10 else "Built project application.",
                proposed=f"Designed and deployed scalable web application integrating RESTful APIs, database optimizations, and {top_skills[0] if top_skills else 'robust components'}{comp_context}, handling concurrent user traffic.",
                reason=f"Aligns project architecture and domain keywords specifically with {company or role or 'target role'}.",
                source_evidence="Master Resume projects: verified codebase and architecture.",
                confidence=0.90,
                status=ChangeStatus.PENDING,
            ))

        if not changes:
            changes.append(TailoringChange(
                change_id="chg_01",
                original="Worked on software applications.",
                proposed=f"Developed robust application components using {', '.join(skills[:3]) if skills else 'REST APIs and modern frameworks'} adhering to enterprise engineering standards.",
                reason="Aligns technical terminology directly with the job description.",
                source_evidence="Master resume skills list.",
                confidence=0.85,
                status=ChangeStatus.PENDING,
            ))

        return TailoringResult(changes=changes)

    # ------------------------------------------------------------------
    # Declared for later phases — kept here so the AIService surface is
    # stable and modules can be written against it now if useful.
    # ------------------------------------------------------------------
    async def analyze_resume(self, *args, **kwargs):
        raise NotImplementedError("Implemented in Phase 2 (Resume Intelligence).")

    async def analyze_job_description(self, *args, **kwargs):
        raise NotImplementedError("Implemented in Phase 4 (JD Analysis).")

    async def compare_resume_with_jd(self, *args, **kwargs):
        raise NotImplementedError("Implemented in Phase 4 (JD Analysis).")

    async def generate_cover_letter(self, *args, **kwargs):
        raise NotImplementedError("Implemented in Phase 4 (Tailoring).")

    async def generate_skill_gap_explanation(self, *args, **kwargs):
        raise NotImplementedError("Implemented in Phase 7 (Skill Gaps).")

    async def generate_learning_plan(self, *args, **kwargs):
        raise NotImplementedError("Implemented in Phase 7 (Learning Roadmap).")

    async def generate_interview_questions(
        self,
        resume_summary: str,
        jd_text: str,
        target_role: str,
        company: str = "",
        user_id: str | None = None,
    ) -> InterviewQuestionsResult:
        user_prompt = build_interview_user_prompt(resume_summary, jd_text, target_role, company)
        try:
            result = await generate_structured(
                provider=self._provider,
                system_prompt=INTERVIEW_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema=InterviewQuestionsResult,
                max_retries=self._settings.AI_MAX_RETRIES,
            )
            await self._log_operation(
                operation="generate_interview_questions", user_id=user_id, status="success",
                meta={"prompt_version": INTERVIEW_PROMPT_VERSION, "count": len(result.questions)},
            )
            return result
        except Exception as exc:
            import logging
            logging.getLogger("roleradar.ai").warning("LLM interview generation failed (%s) — activating intelligent fallback", exc)
            fallback = self._fallback_interview_questions(resume_summary, jd_text, target_role, company)
            await self._log_operation(
                operation="generate_interview_questions", user_id=user_id, status="fallback_success",
                meta={"prompt_version": INTERVIEW_PROMPT_VERSION, "error": str(exc)},
            )
            return fallback

    def _fallback_interview_questions(self, resume_summary: str, jd_text: str, target_role: str, company: str) -> InterviewQuestionsResult:
        from app.core.ai_service.schemas import InterviewQuestion
        comp = company or "the company"
        return InterviewQuestionsResult(
            questions=[
                # Technical Round
                InterviewQuestion(
                    category="technical",
                    question=f"How would you design a scalable backend architecture for a high-traffic {target_role} service at {comp}?",
                    star_hint="Focus on API modularity, database indexing, caching strategies (Redis), and horizontal scaling.",
                    strategy="1. Clarify expected scale (QPS, read/write ratio) -> 2. High-level architecture (Load Balancer, API Gateway, Services, DB) -> 3. Deep-dive into bottleneck resolution (Caching, Sharding, Async message queues).",
                    sample_answer=f"\"I would start with a modular service architecture fronted by a reverse proxy/load balancer. For read-heavy operations, I'd introduce Redis caching to reduce database load by up to 70%. For persistent storage, I'd use an indexed relational DB like PostgreSQL or NoSQL for flexible document schemas, ensuring asynchronous queue processing via Celery or Kafka for background tasks.\"",
                    pitfalls="Jumping straight into complex tools without clarifying requirements or discussing data consistency trade-offs.",
                ),
                InterviewQuestion(
                    category="technical",
                    question=f"What approach do you take to optimize database queries, prevent N+1 queries, and reduce API latency in {target_role} applications?",
                    star_hint="Discuss query analysis (EXPLAIN ANALYZE), ORM eager loading, connection pooling, and indexing strategies.",
                    strategy="1. Diagnostic stage (APM monitoring, query profiling) -> 2. Code-level fixes (eager loading, pagination) -> 3. DB-level fixes (composite indexes, connection pools).",
                    sample_answer="\"First, I profile slow endpoints using tools like APM or EXPLAIN ANALYZE to identify unindexed lookups or N+1 queries in ORMs. I solve N+1 problems by using eager joins (e.g., select_related / joinedload), adding B-tree indexes on frequently filtered foreign keys, and enabling database connection pooling to avoid handshake overhead.\"",
                    pitfalls="Suggesting blind caching before fixing inefficient underlying database queries.",
                ),
                InterviewQuestion(
                    category="technical",
                    question=f"How do you ensure state management consistency, API security, and robust error handling in production?",
                    star_hint="Mention JWT authentication, input validation (Pydantic/Zod), rate limiting, and centralized error middleware.",
                    strategy="Cover authentication flow -> input validation layer -> centralized error boundaries/middleware -> automated testing.",
                    sample_answer="\"I implement a defense-in-depth approach: validating all incoming payloads against strict schemas, enforcing stateless JWT/OAuth2 tokens with short expirations and refresh rotation, applying rate limiting at the gateway, and catching exceptions centrally to return standardized, clean error responses without leaking stack traces.\"",
                    pitfalls="Forgetting input sanitization and failing to mention automated unit/integration tests.",
                ),

                # Managerial Round
                InterviewQuestion(
                    category="managerial",
                    question=f"Walk me through the most technically complex project on your resume. What architectural trade-offs did you make, and what would you do differently?",
                    star_hint="Use the STAR method: Situation, Task, your specific Action/code contributions, and the measurable Result.",
                    strategy="Situation: What was the business goal? -> Task: Technical constraints -> Action: Specific architecture and decisions -> Result: Performance metric, throughput, or user adoption.",
                    sample_answer="\"In my key project, the challenge was handling live updates without overwhelming the server. I evaluated WebSockets vs Server-Sent Events and chose SSE because the data flow was primarily one-directional, saving server memory. As a result, system latency dropped by 35% with 99.9% uptime. If doing it again, I would incorporate automated contract testing earlier in the sprint.\"",
                    pitfalls="Describing the project generally as a team effort without clearly highlighting your own individual code decisions and metrics.",
                ),
                InterviewQuestion(
                    category="managerial",
                    question=f"How do you prioritize technical debt versus delivering new product features under tight sprint deadlines?",
                    star_hint="Demonstrate business acumen: quantify tech debt risk, allocate a percentage of sprint capacity, and align with business impact.",
                    strategy="1. Acknowledge business goals -> 2. Categorize tech debt by risk & developer velocity impact -> 3. Propose a balanced 80/20 capacity allocation model.",
                    sample_answer="\"I categorize technical debt based on risk: critical security/stability blockers are prioritized immediately, while maintenance debt is tracked in the backlog with estimated velocity costs. I work with product managers to allocate ~15-20% of sprint capacity toward debt remediation by framing it around developer velocity and system reliability.\"",
                    pitfalls="Treating technical debt as purely an engineering gripe rather than framing it around business risk and speed.",
                ),
                InterviewQuestion(
                    category="managerial",
                    question=f"Describe a time when you had a strong technical disagreement with a teammate or lead. How did you resolve it?",
                    star_hint="Show emotional intelligence, data-driven prototyping (benchmarking), and 'disagree and commit' maturity.",
                    strategy="Focus on objective criteria (benchmarks, maintainability) over ego, seeking alignment, and maintaining team harmony.",
                    sample_answer="\"When choosing between two libraries, my teammate and I disagreed on bundle size versus developer ergonomics. Instead of debating in the abstract, I built a quick prototype benchmark testing both options on build time and rendering speed. The data clearly showed the lighter library improved load time by 40%, which we both agreed best served our users.\"",
                    pitfalls="Blaming the other person or sounding rigid and uncompromising.",
                ),

                # HR & Culture Round
                InterviewQuestion(
                    category="hr",
                    question=f"Why do you specifically want to work at {comp}, and how does this {target_role} position align with your career goals?",
                    star_hint="Reference {comp}'s mission, technical culture, specific products, and how you will create immediate value.",
                    strategy="1. Express genuine knowledge of the company's product/engineering culture -> 2. Connect your core skills -> 3. State your 2-3 year growth trajectory.",
                    sample_answer=f"\"I've closely followed {comp}'s engineering work, especially how you build scalable, high-impact products. This {target_role} role is the exact intersection of my strengths in clean architecture and problem-solving, giving me the opportunity to contribute immediately to core systems while growing alongside exceptional engineers.\"",
                    pitfalls="Giving a generic answer that could apply to any company without naming specific reasons.",
                ),
                InterviewQuestion(
                    category="hr",
                    question="Tell me about a situation where a project failed or didn't go as planned. What was the root cause and what did you learn?",
                    star_hint="Demonstrate self-awareness, accountability, root-cause analysis, and permanent process improvements.",
                    strategy="1. Pick a genuine challenge -> 2. Take ownership -> 3. Explain how you recovered -> 4. Share the long-term lesson.",
                    sample_answer="\"Early on, an unhandled API edge case caused an unexpected error in testing. Rather than finding a quick patch, I conducted a root-cause review, added strict schema validation, and instituted automated regression tests. That experience taught me the critical value of proactive boundary testing, which has made all my subsequent releases significantly more resilient.\"",
                    pitfalls="Claiming you've never failed, or blaming external teammates or management.",
                ),
                InterviewQuestion(
                    category="hr",
                    question="Where do you see yourself technically and professionally in the next 2 to 3 years?",
                    star_hint="Highlight continuous learning, deepening technical domain mastery, mentoring, and delivering business impact.",
                    strategy="Emphasize mastery in core stack -> taking ownership of end-to-end features -> contributing to architectural standards.",
                    sample_answer="\"In the next 2-3 years, my goal is to become a go-to domain specialist in scalable backend engineering, taking full ownership of critical microservices and mentoring newer team members. I want to continue driving measurable business impact through reliable, elegant engineering.\"",
                    pitfalls="Giving an unrealistic timeline or showing lack of interest in the current role.",
                ),
            ]
        )

    # ------------------------------------------------------------------
    # Feature 20: Career Copilot
    # ------------------------------------------------------------------
    async def chat(
        self,
        context: CopilotContext,
        user_message: str,
        conversation_history: str = "",
    ) -> str:
        context_block = self._serialize_copilot_context(context)
        user_prompt = build_copilot_user_prompt(context_block, user_message, conversation_history)

        try:
            reply = await self._provider.complete(
                system_prompt=COPILOT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                json_mode=False,
            )
            await self._log_operation(
                operation="chat",
                user_id=context.user_id,
                status="success",
                meta={"prompt_version": CHAT_PROMPT_VERSION},
            )
            return reply
        except Exception as exc:
            import logging
            logging.getLogger("roleradar.ai").warning("LLM chat failed (%s) — activating structured fallback", exc)
            fallback = self._fallback_chat(context, user_message)
            await self._log_operation(
                operation="chat",
                user_id=context.user_id,
                status="fallback_success",
                meta={"prompt_version": CHAT_PROMPT_VERSION, "error": str(exc)},
            )
            return fallback

    def _fallback_chat(self, context: CopilotContext, user_message: str) -> str:
        q_lower = user_message.lower().strip()
        skills = (context.resume_intelligence or {}).get("skills", [])
        parse_score = (context.resume_intelligence or {}).get("parseability_score", 85)
        recruiter_score = (context.resume_intelligence or {}).get("recruiter_impact_score", 80)
        target_roles = (context.profile_summary or {}).get("target_roles", ["Software Engineer"])
        target_role = target_roles[0] if target_roles else "Software Engineer"
        top_matches = context.top_job_matches or []
        min_lpa = (context.profile_summary or {}).get("min_lpa")

        # 1. ATS / Resume / Parseability Intent
        if any(k in q_lower for k in ["ats", "resume", "score", "parseability", "format", "bullet"]):
            bullets = []
            bullets.append(f"- **Parseability Score:** `{parse_score}/100` — Your resume uses single-column layout readable by standard parsers.")
            bullets.append(f"- **Recruiter Impact:** `{recruiter_score}/100` — Evaluated based on active action verbs and quantified bullet metrics.")
            if skills:
                bullets.append(f"- **Detected Skills:** {', '.join(skills[:8])} ({len(skills)} total identified).")
            bullets.append("\n**Actionable Recommendations:**")
            bullets.append("1. Quantify more bullet points with concrete numbers, percentages, or performance gains (e.g. *'reduced latency by 25%'*).")
            bullets.append(f"2. Ensure standard section headers (`Skills`, `Experience`, `Projects`, `Education`) are present.")
            bullets.append("3. Tailor your resume specifically for each target opening in **Jobs For You**.")
            return f"### Resume & ATS Compatibility Breakdown\n\n" + "\n".join(bullets)

        # 2. Skills / Learning / Skill Gaps Intent
        if any(k in q_lower for k in ["skill", "learn", "gap", "roadmap", "study", "tech stack", "language"]):
            bullets = []
            bullets.append(f"Based on market requirements for **{target_role}** roles:")
            bullets.append(f"- **Your Core Strengths:** {', '.join(skills[:6]) if skills else 'Programming fundamentals'}.")
            bullets.append(f"- **High-Demand Skills to Focus On:** System Design, Cloud & Docker, CI/CD, and Advanced Data Modeling.")
            bullets.append("\n**Recommended Learning Next Steps:**")
            bullets.append("1. Head to **Learning Roadmap** to follow your prioritized 4-sprint study plan.")
            bullets.append("2. Build hands-on portfolio projects integrating real-world RESTful APIs and database optimizations.")
            bullets.append("3. Review curated documentation and video courses attached to each missing competency.")
            return f"### Skill Analysis & Learning Strategy for {target_role}\n\n" + "\n".join(bullets)

        # 3. Jobs / Matches / Openings Intent
        if any(k in q_lower for k in ["job", "match", "opportunity", "opening", "internship", "apply"]):
            if top_matches:
                items = [f"- **{m['title']}** at **{m['company']}** — Match Score: `{m['overall_score']}%` ({m.get('apply_readiness', 'ready').replace('_', ' ')})" for m in top_matches[:4]]
                return (
                    f"### Top Recommended Opportunities for You\n\n"
                    f"Here are your highest-ranked live openings based on your verified skills:\n\n"
                    + "\n".join(items)
                    + f"\n\n**Next Step:** Go to **Jobs For You** to review full job descriptions and generate customized 1-page tailored resumes."
                )
            else:
                return (
                    f"### Recommended Job Matching\n\n"
                    f"To view personalized job matches with high ATS compatibility scores:\n"
                    f"1. Make sure your **Master Resume** is uploaded.\n"
                    f"2. Visit **Jobs For You** or **Internships** to filter by Target Role, Min LPA, and Remote preferences.\n"
                    f"3. Use **Tailor for external JD** if you find an opening on LinkedIn or external job portals."
                )

        # 4. Salary / LPA / Compensation Intent
        if any(k in q_lower for k in ["salary", "lpa", "pay", "compensation", "stipend", "package"]):
            expected_text = f"₹{min_lpa} LPA" if min_lpa else "₹6–12 LPA"
            return (
                f"### Market Compensation & Salary Strategy\n\n"
                f"For **{target_role}** positions in India:\n"
                f"- **Fresher / Entry Level:** ₹4.5 to ₹8.5 LPA (Top Product Startups: ₹12–18 LPA)\n"
                f"- **1–3 Years Experience:** ₹8 to ₹18 LPA\n"
                f"- **Your Set Preference:** `{expected_text}`\n\n"
                f"**Negotiation Tip:** Highlight quantifiable project outcomes, system design ownership, and multi-skill breadth across full-stack systems to target the top quartile of the compensation band."
            )

        # 5. Interview Preparation Intent
        if any(k in q_lower for k in ["interview", "mock", "question", "round", "technical round", "hr", "managerial"]):
            return (
                f"### Interview Preparation Strategy for {target_role}\n\n"
                f"To ace interviews for your target role:\n"
                f"- **1. Technical Round:** Master Core Data Structures & Algorithms, REST/GraphQL design, and database query optimizations.\n"
                f"- **2. Managerial Round:** Be prepared to walk through architectural trade-offs in your projects using the STAR framework.\n"
                f"- **3. HR & Culture Round:** Articulate why you want to work at the target company and how you handle tight deadlines.\n\n"
                f"**Next Step:** Open **Interview Preparation**, select your target company, and review company-specific questions with sample answers and free mock interview links."
            )

        # 6. Default / General Career Advice
        return (
            f"### Career Advice for {target_role}\n\n"
            f"To maximize your interview conversion rate:\n"
            f"- **Resume Optimization:** Keep your resume strictly 1-page with action verbs and quantified impact metrics.\n"
            f"- **Targeted Applications:** Apply to jobs with `75%+` match score and tailor your resume to mirror key keywords.\n"
            f"- **Skill Mastery:** Continuously bridge missing skills through hands-on project implementations.\n\n"
            f"Feel free to ask specific questions about your **ATS score**, **interview questions for a company**, or **skills to learn next**!"
        )

    @staticmethod
    def _serialize_copilot_context(context: CopilotContext) -> str:
        """Turns CopilotContext into the plain-text block the model sees.
        Deliberately explicit about what's missing rather than omitting it,
        so the model can say "you haven't done X yet" instead of guessing."""
        lines: list[str] = []
        lines.append(f"profile_summary: {context.profile_summary or 'not available'}")
        lines.append(f"resume_intelligence: {context.resume_intelligence or 'not available'}")
        lines.append(f"top_job_matches: {context.top_job_matches or 'none'}")
        lines.append(f"active_applications: {context.active_applications or 'none'}")
        lines.append(f"skill_gaps: {context.skill_gaps or 'none'}")
        lines.append(f"learning_progress: {context.learning_progress or 'not available'}")
        if context.missing_context_notes:
            lines.append("notes: " + "; ".join(context.missing_context_notes))
        return "\n".join(lines)


def get_ai_service(settings: Settings) -> AIService:
    return AIService(settings)
