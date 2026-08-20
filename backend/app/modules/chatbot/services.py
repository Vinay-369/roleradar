"""
Chatbot service layer. Delegates fact-gathering to
build_copilot_context() and language generation to AIService.chat() --
it does not itself decide what's true. Now also persists conversation
history so it survives across sessions/page refreshes.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai_service.service import AIService
from app.modules.chatbot import repositories as repo
from app.modules.chatbot.context import build_copilot_context

HISTORY_TURNS_FOR_PROMPT = 6  # last N messages included as conversation context


def _format_history(messages: list[dict]) -> str:
    if not messages:
        return ""
    recent = messages[-HISTORY_TURNS_FOR_PROMPT:]
    lines = [f"{m['role'].upper()}: {m['text']}" for m in recent]
    return "\n".join(lines)


async def handle_chat_message(
    ai_service: AIService, user_id: str, message: str, db: AsyncIOMotorDatabase | None = None
) -> tuple[str, bool]:
    context = await build_copilot_context(user_id, db)

    history_text = ""
    if db is not None:
        existing = await repo.get_conversation(db, user_id)
        history_text = _format_history(existing)

    reply = await ai_service.chat(context=context, user_message=message, conversation_history=history_text)
    grounded = len(context.missing_context_notes) == 0

    if db is not None:
        await repo.append_messages(db, user_id, [
            {"role": "user", "text": message},
            {"role": "assistant", "text": reply, "grounded": grounded},
        ])

    return reply, grounded
