"""
Chatbot routes. Protected by real auth -- every message and every
history read/clear is scoped to the authenticated user, never a
caller-supplied id.
"""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai_service.service import AIService, get_ai_service
from app.core.config import get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.chatbot import repositories as repo
from app.modules.chatbot.schemas import ChatHistoryOut, ChatRequest, ChatResponse
from app.modules.chatbot.services import handle_chat_message

router = APIRouter()


def _get_ai_service() -> AIService:
    return get_ai_service(get_settings())


@router.get("/history", response_model=ChatHistoryOut)
async def get_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    messages = await repo.get_conversation(db, str(current_user["_id"]))
    return ChatHistoryOut(messages=messages)


@router.delete("/history", status_code=204)
async def clear_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await repo.clear_conversation(db, str(current_user["_id"]))


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    ai_service: AIService = Depends(_get_ai_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    reply, grounded = await handle_chat_message(
        ai_service, user_id=str(current_user["_id"]), message=body.message, db=db
    )
    return ChatResponse(reply=reply, grounded=grounded)
