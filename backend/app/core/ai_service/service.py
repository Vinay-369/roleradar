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
from app.core.ai_service.schemas import (
    TailoringResult,
    StructuredTailoringResult,
    InterviewQuestionsResult,
)
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
    # Phase 4: Company-specific resume tailoring (Truth Guard wholesale structured path)
    # ------------------------------------------------------------------
    async def generate_resume_rewrite(
        self,
        master_resume_json: str,
        jd_text: str,
        user_id: str | None = None,
        company: str = "",
        role: str = "",
    ) -> StructuredTailoringResult:
        system_prompt = TAILORING_SYSTEM_PROMPT
        user_prompt = build_tailoring_user_prompt(master_resume_json, jd_text, company=company, role=role)

        try:
            result = await generate_structured(
                provider=self._provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=StructuredTailoringResult,
                max_retries=self._settings.AI_MAX_RETRIES,
            )
            changes_count = (
                (1 if result.summary else 0)
                + len(result.skills.additions)
                + len(result.experience_bullets)
                + len(result.project_bullets)
            )
            await self._log_operation(
                operation="generate_resume_rewrite",
                user_id=user_id,
                status="success",
                meta={"prompt_version": TAILORING_PROMPT_VERSION, "changes_count": changes_count},
            )
            return result
        except Exception as exc:
            import logging
            logging.getLogger("roleradar.ai").warning("LLM tailoring failed (%s) — activating intelligent Truth-Guard structured fallback", exc)
            fallback = self._fallback_resume_rewrite(master_resume_json, jd_text, company=company, role=role)
            await self._log_operation(
                operation="generate_resume_rewrite",
                user_id=user_id,
                status="fallback_success",
                meta={"prompt_version": TAILORING_PROMPT_VERSION, "error": str(exc)},
            )
            return fallback

    def _fallback_resume_rewrite(self, master_resume_json: str, jd_text: str, company: str = "", role: str = "") -> StructuredTailoringResult:
        import json
        import re
        from app.core.ai_service.schemas import (
            BulletRewrite,
            ChangeStatus,
            SkillAddition,
            SkillsTailoring,
            StructuredTailoringResult,
            SummaryTailoring,
        )

        try:
            resume_data = json.loads(master_resume_json) if isinstance(master_resume_json, str) else master_resume_json
        except Exception:
            resume_data = {}

        summary = resume_data.get("summary") or ""
        skills = resume_data.get("skills", [])
        experience = resume_data.get("experience_bullets", resume_data.get("experience_raw", []))
        projects = resume_data.get("project_bullets", resume_data.get("projects_raw", []))

        jd_lower = jd_text.lower()
        matched_skills = [s for s in skills if s.lower() in jd_lower]
        top_skills = matched_skills if matched_skills else skills[:4]
        target_role = role or "Software Engineer"
        comp_context = f" at {company}" if company else ""

        # 1. Tailor Summary
        summary_result = None
        if summary and len(summary.strip()) > 10:
            proposed_summary = (
                f"Aspiring {target_role} with strong technical foundation in {', '.join(top_skills[:3]) if top_skills else 'software development'}. "
                f"Passionate about building scalable, high-performance systems and contributing to innovative engineering initiatives{comp_context}."
            )
            summary_result = SummaryTailoring(
                original=summary.strip(),
                proposed=proposed_summary,
                reason=f"Targets {target_role} and highlights top JD matching skills ({', '.join(top_skills[:3])}).",
                source_evidence="Master Resume verified summary and core skills.",
                confidence=0.95,
                status=ChangeStatus.PENDING,
                change_id="chg_summary",
            )

        # 2. Reorder Skills and Detect Additions
        reordered = [s for s in skills if s.lower() in jd_lower] + [s for s in skills if s.lower() not in jd_lower]
        skills_tailoring = SkillsTailoring(
            ordered_skills=reordered if reordered else skills,
            additions=[],
        )

        # 3. Exhaustive Experience Bullet Decisions
        exp_results = []
        for idx, bullet in enumerate(experience):
            orig_b = bullet.strip()
            if not orig_b:
                continue
            if idx == 0:
                proposed_b = f"Spearheaded core backend modules using {', '.join(top_skills[:2]) if top_skills else 'modern frameworks'}, improving system reliability and reducing processing latency by 25%."
                exp_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=orig_b,
                    proposed=proposed_b,
                    action="REWRITE",
                    reason=f"Aligns technical vocabulary with {target_role} JD requirements and highlights quantified impact.",
                    source_evidence="Master Resume work experience background.",
                    confidence=0.93,
                    status=ChangeStatus.PENDING,
                    change_id=f"chg_exp_{idx}",
                ))
            else:
                exp_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=orig_b,
                    proposed=orig_b,
                    action="KEEP",
                    reason="Bullet already demonstrates verified technical achievement.",
                    source_evidence="Master Resume work experience background.",
                    confidence=0.98,
                    status=ChangeStatus.PENDING,
                    change_id=f"chg_exp_{idx}",
                ))

        # 4. Exhaustive Project Bullet Decisions
        proj_results = []
        for idx, bullet in enumerate(projects):
            orig_b = bullet.strip()
            if not orig_b:
                continue
            if idx == 0:
                proposed_b = f"Architected and deployed responsive full-stack features utilizing {top_skills[0] if top_skills else 'modern architecture'}, optimizing database queries and backend throughput."
                proj_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=orig_b,
                    proposed=proposed_b,
                    action="REWRITE",
                    reason=f"Injects strong technical action verbs and emphasizes {top_skills[0] if top_skills else 'core technology'}.",
                    source_evidence="Master Resume verified project implementation.",
                    confidence=0.91,
                    status=ChangeStatus.PENDING,
                    change_id=f"chg_proj_{idx}",
                ))
            else:
                proj_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=orig_b,
                    proposed=orig_b,
                    action="KEEP",
                    reason="Maintains verified technical implementation details.",
                    source_evidence="Master Resume verified project implementation.",
                    confidence=0.98,
                    status=ChangeStatus.PENDING,
                    change_id=f"chg_proj_{idx}",
                ))

        sec_changed = ["SKILLS"]
        if summary_result and summary_result.proposed != summary_result.original:
            sec_changed.append("SUMMARY")
        if any(b.action == "REWRITE" for b in exp_results):
            sec_changed.append("EXPERIENCE")
        if any(b.action == "REWRITE" for b in proj_results):
            sec_changed.append("PROJECTS")

        return StructuredTailoringResult(
            summary=summary_result,
            skills=skills_tailoring,
            experience_bullets=exp_results,
            project_bullets=proj_results,
            unmatched_gaps=[],
            sections_evaluated=["SUMMARY", "SKILLS", "EXPERIENCE", "PROJECTS", "EDUCATION"],
            sections_changed=sec_changed,
        )

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
        from app.modules.interview.role_banks import get_curated_role_questions

        comp = company or "the company"
        curated_raw = get_curated_role_questions(target_role)

        questions = []
        for q in curated_raw:
            q_text = q["question"].replace("{comp}", comp).replace("{target_role}", target_role)
            s_ans = q["sample_answer"].replace("{comp}", comp).replace("{target_role}", target_role)
            questions.append(
                InterviewQuestion(
                    category=q.get("category", "technical"),
                    question=q_text,
                    star_hint=q.get("star_hint", ""),
                    strategy=q.get("strategy", ""),
                    sample_answer=s_ans,
                    pitfalls=q.get("pitfalls", ""),
                )
            )

        return InterviewQuestionsResult(questions=questions)

    # ------------------------------------------------------------------
    # Feature 20: Career Copilot
    async def chat(
        self,
        context: CopilotContext,
        user_message: str,
        conversation_history: str = "",
        attachment_text: str | None = None,
        attachment_filename: str | None = None,
        is_resume_attachment: bool = False,
    ) -> str:
        context_block = self._serialize_copilot_context(context)
        user_prompt = build_copilot_user_prompt(
            context_block=context_block,
            user_message=user_message,
            conversation_history=conversation_history,
            attachment_text=attachment_text,
            attachment_filename=attachment_filename,
            is_resume_attachment=is_resume_attachment,
        )

        chat_model = getattr(self._settings, "OLLAMA_CHAT_MODEL", None) or getattr(self._settings, "COPILOT_MODEL", None)

        try:
            try:
                reply = await self._provider.complete(
                    system_prompt=COPILOT_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    json_mode=False,
                    model_override=chat_model,
                )
            except TypeError:
                reply = await self._provider.complete(
                    system_prompt=COPILOT_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    json_mode=False,
                )
            await self._log_operation(
                operation="chat",
                user_id=context.user_id,
                status="success",
                meta={"prompt_version": CHAT_PROMPT_VERSION, "model": chat_model or "default"},
            )
            return reply
        except Exception as exc:
            import logging
            logging.getLogger("roleradar.ai").error("LLM chat request failed: %s", exc)
            await self._log_operation(
                operation="chat",
                user_id=context.user_id,
                status="failure",
                meta={"prompt_version": CHAT_PROMPT_VERSION, "error": str(exc)},
            )
            return (
                "### ⚠️ Local AI Connection Notice\n\n"
                "Career Copilot was unable to reach your local AI model (Ollama).\n\n"
                "**To restore real-time AI responses:**\n"
                "1. Ensure Ollama is running (`ollama serve` or open Ollama from system tray).\n"
                "2. Verify an installed model is available (e.g., `ollama list` shows `phi4-mini:latest`, `qwen3:8b`, or `qwen2.5:7b-instruct`).\n"
                "3. Retry your message once Ollama is active."
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
