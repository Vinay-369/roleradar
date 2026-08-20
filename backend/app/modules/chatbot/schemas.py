from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    grounded: bool


class ChatMessageOut(BaseModel):
    role: str
    text: str
    grounded: bool | None = None


class ChatHistoryOut(BaseModel):
    messages: list[ChatMessageOut]
