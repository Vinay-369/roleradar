from datetime import datetime
from pydantic import BaseModel, Field


class AttachmentPayload(BaseModel):
    filename: str
    file_type: str
    extracted_text: str
    file_data: str | None = None
    is_resume: bool = False


class AttachmentUploadOut(BaseModel):
    filename: str
    file_type: str
    extracted_text: str
    file_data: str | None = None
    char_count: int
    is_resume: bool
    resume_hint: str | None = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    attachment: AttachmentPayload | None = None


class ChatResponse(BaseModel):
    reply: str
    grounded: bool
    is_fallback: bool = False
    conversation_id: str | None = None
    resume_suggestion: str | None = None


class ChatMessageOut(BaseModel):
    role: str
    text: str
    grounded: bool | None = None
    is_fallback: bool | None = None
    attachment: AttachmentPayload | None = None
    created_at: str | None = None


class ChatHistoryOut(BaseModel):
    messages: list[ChatMessageOut]


class ConversationSummaryOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    last_preview: str


class ConversationDetailOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessageOut]


class CreateConversationRequest(BaseModel):
    title: str | None = None
    initial_message: str | None = None


class UpdateTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
