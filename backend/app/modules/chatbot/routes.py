"""
Chatbot routes. Protected by auth -- every conversation, attachment, and message
is scoped to the authenticated user.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai_service.service import AIService, get_ai_service
from app.core.config import get_settings
from app.db.mongo import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.chatbot import repositories as repo
from app.modules.chatbot.attachments import process_attachment_file
from app.modules.chatbot.schemas import (
    AttachmentUploadOut,
    ChatHistoryOut,
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    ConversationDetailOut,
    ConversationSummaryOut,
    CreateConversationRequest,
    UpdateTitleRequest,
)
from app.modules.chatbot.services import handle_chat_message

router = APIRouter()

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB limit


def _get_ai_service() -> AIService:
    return get_ai_service(get_settings())


# ------------------------------------------------------------------
# Attachment Upload & Processing
# ------------------------------------------------------------------
@router.post("/attachment", response_model=AttachmentUploadOut)
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    contents = await file.read()
    if len(contents) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Attachment exceeds 10MB limit.",
        )

    filename = file.filename or "uploaded_file"
    extracted_text, file_type, is_resume, resume_hint = process_attachment_file(filename, contents)

    # Encode original binary contents into a base64 data URL for native browser rendering
    import base64
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext == "pdf":
        mime_type = "application/pdf"
    elif ext in ["png", "jpg", "jpeg", "webp", "gif", "svg"]:
        mime_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
    elif ext in ["txt", "md", "py", "ts", "js", "json", "csv", "sql", "html", "css"]:
        mime_type = "text/plain"
    elif ext in ["docx", "doc"]:
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        mime_type = file.content_type or "application/octet-stream"

    b64_str = base64.b64encode(contents).decode("utf-8")
    file_data = f"data:{mime_type};base64,{b64_str}"

    return AttachmentUploadOut(
        filename=filename,
        file_type=file_type,
        extracted_text=extracted_text,
        file_data=file_data,
        char_count=len(extracted_text),
        is_resume=is_resume,
        resume_hint=resume_hint,
    )


# ------------------------------------------------------------------
# Multi-Session Conversations Management
# ------------------------------------------------------------------
@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def list_user_conversations(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    return await repo.list_conversations(db, user_id)


@router.post("/conversations", response_model=ConversationDetailOut)
async def create_new_conversation(
    body: CreateConversationRequest | None = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    title = body.title if body else None
    conv = await repo.create_conversation(db, user_id, title=title)
    return ConversationDetailOut(
        id=conv["id"],
        title=conv["title"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        messages=[ChatMessageOut(**m) for m in conv.get("messages", [])],
    )


@router.get("/conversations/{conv_id}", response_model=ConversationDetailOut)
async def get_conversation_detail(
    conv_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    conv = await repo.get_conversation_thread(db, user_id, conv_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return ConversationDetailOut(
        id=conv["id"],
        title=conv["title"],
        created_at=conv["created_at"],
        updated_at=conv["updated_at"],
        messages=[ChatMessageOut(**m) for m in conv.get("messages", [])],
    )


@router.patch("/conversations/{conv_id}")
async def rename_conversation(
    conv_id: str,
    body: UpdateTitleRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    success = await repo.update_conversation_title(db, user_id, conv_id, body.title)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return {"success": True, "title": body.title}


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_thread(
    conv_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    success = await repo.delete_conversation(db, user_id, conv_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")


# ------------------------------------------------------------------
# Chat Messaging & Legacy Routes
# ------------------------------------------------------------------
@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    ai_service: AIService = Depends(_get_ai_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    reply, grounded, conv_id, resume_suggestion = await handle_chat_message(
        ai_service=ai_service,
        user_id=user_id,
        message=body.message,
        db=db,
        conversation_id=body.conversation_id,
        attachment=body.attachment,
    )
    return ChatResponse(
        reply=reply,
        grounded=grounded,
        conversation_id=conv_id,
        resume_suggestion=resume_suggestion,
    )


@router.get("/history", response_model=ChatHistoryOut)
async def get_legacy_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    raw_msgs = await repo.get_conversation(db, user_id)
    messages = [ChatMessageOut(**m) for m in raw_msgs]
    return ChatHistoryOut(messages=messages)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = str(current_user["_id"])
    await repo.clear_all_conversations(db, user_id)
