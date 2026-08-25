"""
Chatbot service layer.
Handles multi-session conversation threads, document/image attachment injection,
proactive resume-audit suggestions, and delegates language generation to AIService.chat().
Fully backwards-compatible with legacy positional arguments.
"""
from datetime import datetime, timezone
from typing import Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai_service.service import AIService
from app.modules.chatbot import repositories as repo
from app.modules.chatbot.context import build_copilot_context
from app.modules.chatbot.schemas import AttachmentPayload

HISTORY_TURNS_FOR_PROMPT = 6  # last N messages included as conversation context


def _format_history(messages: list[dict]) -> str:
    if not messages:
        return ""
    recent = messages[-HISTORY_TURNS_FOR_PROMPT:]
    lines = [f"{m.get('role', 'user').upper()}: {m.get('text', '')}" for m in recent]
    return "\n".join(lines)


async def handle_chat_message(
    ai_service: AIService,
    user_id: str,
    message: str,
    db: AsyncIOMotorDatabase | Any = None,
    conversation_id: str | None = None,
    attachment: AttachmentPayload | None = None,
    **kwargs,
) -> tuple[str, bool, str, str | None]:
    """
    Executes a chat turn with full context, attachment awareness, and multi-session persistence.
    Returns: (reply, grounded, conversation_id, resume_suggestion)
    """
    # Handle callers that passed conversation_id in db position or vice-versa
    if isinstance(conversation_id, AsyncIOMotorDatabase) and db is None:
        db = conversation_id
        conversation_id = None
    if "db" in kwargs and kwargs["db"] is not None:
        db = kwargs["db"]
    if "conversation_id" in kwargs:
        conversation_id = kwargs["conversation_id"]
    if "attachment" in kwargs:
        attachment = kwargs["attachment"]

    context = await build_copilot_context(user_id, db)

    history_text = ""
    target_conv_id = conversation_id
    if db is not None:
        conv = await repo.get_conversation_thread(db, user_id, conversation_id)
        if conv:
            target_conv_id = conv["id"]
            history_text = _format_history(conv.get("messages", []))

    attachment_text = attachment.extracted_text if attachment else None
    attachment_filename = attachment.filename if attachment else None
    is_resume_attachment = attachment.is_resume if attachment else False

    reply = await ai_service.chat(
        context=context,
        user_message=message,
        conversation_history=history_text,
        attachment_text=attachment_text,
        attachment_filename=attachment_filename,
        is_resume_attachment=is_resume_attachment,
    )
    grounded = len(context.missing_context_notes) == 0

    resume_suggestion = None
    if is_resume_attachment:
        resume_suggestion = (
            "This document appears to be a resume. For a full 4-pillar ATS benchmark, "
            "keyword optimization, and exportable formatting, you can upload it directly to Master Resume."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    user_msg_dict: dict = {
        "role": "user",
        "text": message,
        "created_at": now_iso,
    }
    if attachment:
        user_msg_dict["attachment"] = attachment.model_dump()

    assistant_msg_dict: dict = {
        "role": "assistant",
        "text": reply,
        "grounded": grounded,
        "created_at": now_iso,
    }

    resulting_conv_id = target_conv_id or ""
    if db is not None:
        updated_conv = await repo.append_messages_to_conversation(
            db=db,
            user_id=user_id,
            conv_id=target_conv_id,
            new_messages=[user_msg_dict, assistant_msg_dict],
        )
        resulting_conv_id = updated_conv["id"]

    return reply, grounded, resulting_conv_id, resume_suggestion
