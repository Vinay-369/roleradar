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
from typing import Any

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
    # Phase 4: Company-specific resume tailoring (High-Speed Compact Tailoring Plan)
    # ------------------------------------------------------------------
    async def generate_resume_rewrite(
        self,
        master_resume_json: str,
        jd_text: str,
        user_id: str | None = None,
        company: str = "",
        role: str = "",
    ) -> StructuredTailoringResult:
        from app.core.ai_service.schemas import CompactTailoringPlan
        from app.core.caching import (
            compute_sha256,
            get_cached_tailoring_plan,
            set_cached_tailoring_plan,
        )

        model_name = getattr(self._provider, "_model", self._settings.OLLAMA_MODEL)
        provider_name = self._provider.__class__.__name__
        prof_hash = compute_sha256(master_resume_json)
        jd_hash = compute_sha256(jd_text + f":{company}:{role}")

        # Check Cache (<10ms instant response on identical inputs for production local/cloud providers)
        use_cache = provider_name in ("OllamaProvider", "LMStudioProvider", "CloudFallbackProvider")
        if use_cache:
            cached_result = get_cached_tailoring_plan(prof_hash, jd_hash, f"{model_name}:{provider_name}")
            if cached_result is not None:
                return cached_result

        system_prompt = TAILORING_SYSTEM_PROMPT
        user_prompt = build_tailoring_user_prompt(master_resume_json, jd_text, company=company, role=role)

        try:
            # High-speed compact structured generation (350-500 tokens output)
            compact_plan = await generate_structured(
                provider=self._provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=CompactTailoringPlan,
                max_retries=self._settings.AI_MAX_RETRIES,
            )
            result = self._reconstruct_structured_result(master_resume_json, compact_plan, company=company, role=role)
            if use_cache:
                set_cached_tailoring_plan(prof_hash, jd_hash, f"{model_name}:{provider_name}", result)

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
            set_cached_tailoring_plan(prof_hash, jd_hash, model_name, fallback)
            await self._log_operation(
                operation="generate_resume_rewrite",
                user_id=user_id,
                status="fallback_success",
                meta={"prompt_version": TAILORING_PROMPT_VERSION, "error": str(exc)},
            )
            return fallback

    def _reconstruct_structured_result(
        self,
        master_resume_json: str,
        compact_plan: Any,
        company: str = "",
        role: str = "",
    ) -> StructuredTailoringResult:
        import json
        from app.core.ai_service.schemas import (
            BulletRewrite,
            ChangeStatus,
            SkillsTailoring,
            StructuredTailoringResult,
            SummaryTailoring,
        )

        try:
            master_data = json.loads(master_resume_json) if isinstance(master_resume_json, str) else master_resume_json
        except Exception:
            master_data = {}

        # 1. Summary
        orig_sum = master_data.get("summary") or ""
        prop_sum = compact_plan.summary or orig_sum
        summary = None
        if orig_sum:
            summary = SummaryTailoring(
                original=orig_sum,
                proposed=prop_sum,
                reason=f"Aligns professional summary with {role or 'target'} role at {company}." if company else f"Aligns summary with {role or 'target role'}.",
                source_evidence=orig_sum,
                confidence=0.95,
                status=ChangeStatus.PENDING if prop_sum.strip() != orig_sum.strip() else ChangeStatus.APPROVED,
            )

        # 2. Experience Bullets
        exp_bullets = master_data.get("experience_bullets", master_data.get("experience_raw", []))
        exp_rewrites_map = {r.bullet_index: r for r in getattr(compact_plan, "experience_rewrites", [])}
        reconstructed_exp = []
        for b_idx, b_text in enumerate(exp_bullets):
            orig_b = str(b_text)
            if b_idx in exp_rewrites_map:
                rw = exp_rewrites_map[b_idx]
                reconstructed_exp.append(BulletRewrite(
                    bullet_index=b_idx,
                    original=orig_b,
                    proposed=rw.proposed,
                    action="REWRITE",
                    reason=getattr(rw, "reason", "") or "Aligns technical impact and terminology with job description.",
                    source_evidence=orig_b,
                    confidence=0.95,
                    status=ChangeStatus.PENDING,
                ))
            else:
                reconstructed_exp.append(BulletRewrite(
                    bullet_index=b_idx,
                    original=orig_b,
                    proposed=orig_b,
                    action="KEEP",
                    reason="Already optimal and well-aligned with background.",
                    source_evidence=orig_b,
                    confidence=1.0,
                    status=ChangeStatus.APPROVED,
                ))

        # 3. Project Bullets
        proj_bullets = master_data.get("project_bullets", master_data.get("projects_raw", []))
        proj_rewrites_map = {r.bullet_index: r for r in getattr(compact_plan, "project_rewrites", [])}
        reconstructed_proj = []
        for b_idx, p_text in enumerate(proj_bullets):
            orig_p = str(p_text)
            if b_idx in proj_rewrites_map:
                rw = proj_rewrites_map[b_idx]
                reconstructed_proj.append(BulletRewrite(
                    bullet_index=b_idx,
                    original=orig_p,
                    proposed=rw.proposed,
                    action="REWRITE",
                    reason=getattr(rw, "reason", "") or "Aligns technical project contribution with job requirements.",
                    source_evidence=orig_p,
                    confidence=0.95,
                    status=ChangeStatus.PENDING,
                ))
            else:
                reconstructed_proj.append(BulletRewrite(
                    bullet_index=b_idx,
                    original=orig_p,
                    proposed=orig_p,
                    action="KEEP",
                    reason="Already optimal.",
                    source_evidence=orig_p,
                    confidence=1.0,
                    status=ChangeStatus.APPROVED,
                ))

        return StructuredTailoringResult(
            summary=summary,
            skills=SkillsTailoring(ordered_skills=master_data.get("skills", [])),
            experience_bullets=reconstructed_exp,
            project_bullets=reconstructed_proj,
            unmatched_gaps=getattr(compact_plan, "unmatched_gaps", []),
            changes=getattr(compact_plan, "changes", []),
        )

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
            orig_sum = summary.strip()
            summary_result = SummaryTailoring(
                original=orig_sum,
                proposed=orig_sum,
                reason=f"Retains verified professional summary aligned with {target_role}.",
                source_evidence=orig_sum,
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

        # 3. Exhaustive Experience Bullet Decisions (Grounding & Metric Preserving)
        from app.modules.resume.parsing.action_verbs import STRONG_ACTION_VERBS, strengthen_bullet_verb
        from app.modules.tailoring.export import (
            _is_project_title_line,
            _is_tech_stack_line,
            _clean_title_and_date,
            _BULLET_PREFIX_RE,
        )

        exp_results = []
        strong_verbs = ["Developed", "Engineered", "Implemented", "Built"]
        for idx, bullet in enumerate(experience):
            orig_b = bullet.strip()
            if not orig_b:
                continue

            if orig_b.endswith(":") or (re.search(r"\b(?:\d{4}|present)\b", orig_b, re.IGNORECASE) and len(orig_b.split()) <= 12 and not orig_b.endswith((".", ";", "!"))):
                exp_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=orig_b,
                    proposed=orig_b,
                    action="KEEP",
                    reason="Structural heading and role progression preserved intact.",
                    source_evidence=orig_b,
                    confidence=1.0,
                    status=ChangeStatus.APPROVED,
                    change_id=f"chg_exp_{idx}",
                ))
                continue

            chosen_verb = strong_verbs[idx % len(strong_verbs)]
            refined_b, was_chg = strengthen_bullet_verb(orig_b, default_verb=chosen_verb)

            exp_results.append(BulletRewrite(
                bullet_index=idx,
                original=orig_b,
                proposed=refined_b,
                action="REWRITE" if was_chg else "KEEP",
                reason=f"Enhances opening action verb for {target_role} while strictly preserving all source metrics and technologies.",
                source_evidence=orig_b,
                confidence=0.95,
                status=ChangeStatus.PENDING if was_chg else ChangeStatus.APPROVED,
                change_id=f"chg_exp_{idx}",
            ))

        # 4. Exhaustive Project Bullet Decisions (Grounding & Metric Preserving)
        # Project TITLES and Tech Stacks are structurally protected from verb-injection
        proj_results = []
        proj_verbs = ["Developed", "Engineered", "Implemented", "Built"]
        for idx, bullet in enumerate(projects):
            if isinstance(bullet, dict):
                orig_bullets = bullet.get("bullets", [])
                refined_bullets = []
                any_chg = False
                chosen_verb = proj_verbs[idx % len(proj_verbs)]
                for b_item in orig_bullets:
                    r_b, chg = strengthen_bullet_verb(str(b_item), default_verb=chosen_verb)
                    refined_bullets.append(r_b)
                    if chg:
                        any_chg = True
                new_proj_dict = dict(bullet)
                new_proj_dict["bullets"] = refined_bullets
                proj_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=json.dumps(bullet),
                    proposed=json.dumps(new_proj_dict),
                    action="REWRITE" if any_chg else "KEEP",
                    reason="Preserves project title and tech stack while optimizing delivery bullets.",
                    source_evidence=str(orig_bullets),
                    confidence=0.95,
                    status=ChangeStatus.PENDING,
                    change_id=f"chg_proj_{idx}",
                ))
                continue

            orig_b = str(bullet).strip()
            if not orig_b:
                continue
            chosen_verb = proj_verbs[idx % len(proj_verbs)]

            # Standalone project title or tech stack line (e.g. "AI-Based Ad Analyzer", "Cataract Prediction System")
            if _is_project_title_line(orig_b) or _is_tech_stack_line(orig_b) or _clean_title_and_date(orig_b):
                proj_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=orig_b,
                    proposed=orig_b,
                    action="KEEP",
                    reason="Preserves verified project title and heading unmodified.",
                    source_evidence=orig_b,
                    confidence=1.0,
                    status=ChangeStatus.APPROVED,
                    change_id=f"chg_proj_{idx}",
                ))
                continue

            # Multi-line project item: isolate header lines from actual bullet lines
            lines = orig_b.split("\n")
            if len(lines) > 1:
                header_lines = []
                bullet_lines = []
                for l in lines:
                    l_str = l.strip()
                    if not l_str:
                        continue
                    if _is_project_title_line(l_str) or _is_tech_stack_line(l_str) or _clean_title_and_date(l_str):
                        header_lines.append(l_str)
                    else:
                        bullet_lines.append(l_str)

                refined_bullet_lines = []
                any_chg = False
                for b_line in bullet_lines:
                    r_b, chg = strengthen_bullet_verb(b_line, default_verb=chosen_verb)
                    refined_bullet_lines.append(r_b)
                    if chg:
                        any_chg = True

                all_refined = header_lines + (refined_bullet_lines if refined_bullet_lines else bullet_lines)
                refined_b = "\n".join(all_refined)
                proj_results.append(BulletRewrite(
                    bullet_index=idx,
                    original=orig_b,
                    proposed=refined_b,
                    action="REWRITE" if any_chg else "KEEP",
                    reason="Preserves project title and tech stack while strengthening bullet action verbs.",
                    source_evidence=orig_b,
                    confidence=0.95,
                    status=ChangeStatus.PENDING,
                    change_id=f"chg_proj_{idx}",
                ))
                continue

            # Inline title + bullet format e.g. "AI-Based Ad Analyzer: Architected end-to-end..."
            clean_b = _BULLET_PREFIX_RE.sub("", orig_b).strip()
            if ":" in clean_b:
                t_cand, sep, b_cand = clean_b.partition(":")
                t_cand = t_cand.strip()
                b_cand = b_cand.strip()
                if 1 <= len(t_cand.split()) <= 12 and not any(w.lower() in STRONG_ACTION_VERBS for w in t_cand.split()[:2]) and len(b_cand.split()) >= 3:
                    r_bullet, chg = strengthen_bullet_verb(b_cand, default_verb=chosen_verb)
                    refined_b = f"{t_cand}: {r_bullet}"
                    proj_results.append(BulletRewrite(
                        bullet_index=idx,
                        original=orig_b,
                        proposed=refined_b,
                        action="REWRITE" if chg else "KEEP",
                        reason="Preserves project title while strengthening bullet action verb.",
                        source_evidence=orig_b,
                        confidence=0.95,
                        status=ChangeStatus.PENDING,
                        change_id=f"chg_proj_{idx}",
                    ))
                    continue

            # Standard project bullet line
            r_b, was_chg = strengthen_bullet_verb(orig_b, default_verb=chosen_verb)
            proj_results.append(BulletRewrite(
                bullet_index=idx,
                original=orig_b,
                proposed=r_b,
                action="REWRITE" if was_chg else "KEEP",
                reason="Applies strong technical action verb while maintaining verified project substance.",
                source_evidence=orig_b,
                confidence=0.95,
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
