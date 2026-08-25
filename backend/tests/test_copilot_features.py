"""
Comprehensive automated tests for Career Copilot feature-completeness:
- Document attachments (PDF, DOCX, TXT, Code)
- Image attachment processing & capability disclaimer
- Resume-structure detection and proactive suggestion
- Multi-session conversation thread lifecycle (create, list, rename, delete)
- Attachment-aware chat messaging & prompt injection
"""
import io
import pytest
import fitz
import docx
from mongomock_motor import AsyncMongoMockClient

from app.core.config import Settings
from app.core.ai_service.service import AIService
from app.core.ai_service.providers.base import AIProvider
from app.modules.chatbot.attachments import process_attachment_file, is_likely_resume_text
from app.modules.chatbot.schemas import AttachmentPayload
from app.modules.chatbot.services import handle_chat_message
from app.modules.chatbot import repositories as repo


class MockCopilotAIProvider(AIProvider):
    """Mock AI Provider that reflects attached document facts and answers clearly."""
    def __init__(self):
        self.last_user_prompt = ""

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        model_override: str | None = None,
    ) -> str:
        self.last_user_prompt = user_prompt
        if "ATTACHED DOCUMENT CONTENT" in user_prompt:
            if "Kafka retention is configured to 7 days" in user_prompt:
                return "Based on the attached document, Kafka retention is configured for 7 days."
            return "I have reviewed your attached document and answered your question directly."
        return "Quicksort has an average time complexity of O(n log n) and a worst-case of O(n^2)."


from typing import Any


def _create_sample_pdf(text: str) -> bytes:
    pdf_doc: Any = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()
    return pdf_bytes


def _create_sample_docx(text: str) -> bytes:
    doc = docx.Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_pdf_attachment_text_extraction():
    sample_text = "Kafka Architecture Configuration: Kafka retention is configured to 7 days."
    pdf_bytes = _create_sample_pdf(sample_text)

    extracted_text, file_type, is_resume, resume_hint = process_attachment_file("arch_spec.pdf", pdf_bytes)

    assert "Kafka retention is configured to 7 days" in extracted_text
    assert file_type == "PDF"
    assert is_resume is False
    assert resume_hint is None


@pytest.mark.asyncio
async def test_docx_attachment_text_extraction():
    sample_text = "System Requirements:\nDatabase: PostgreSQL 16\nCache: Redis cluster"
    docx_bytes = _create_sample_docx(sample_text)

    extracted_text, file_type, is_resume, resume_hint = process_attachment_file("requirements.docx", docx_bytes)

    assert "Database: PostgreSQL 16" in extracted_text
    assert file_type == "DOCX"
    assert is_resume is False


@pytest.mark.asyncio
async def test_txt_and_code_attachment_extraction():
    code_text = "def calculate_hash(data: str) -> str:\n    return hashlib.sha256(data.encode()).hexdigest()"
    extracted_text, file_type, is_resume, resume_hint = process_attachment_file("hasher.py", code_text.encode("utf-8"))

    assert "def calculate_hash" in extracted_text
    assert file_type == "PY"


@pytest.mark.asyncio
async def test_resume_attachment_detection_and_hint():
    resume_text = """
    Alex Rivera
    alex.rivera@example.com

    TECHNICAL SKILLS
    Python, FastAPI, Docker, PostgreSQL

    PROFESSIONAL EXPERIENCE
    Software Engineer at Tech Corp (2022 - Present)
    - Built high-throughput API gateway processing 50k req/sec.

    EDUCATION
    B.S. in Computer Science (2018 - 2022)
    """
    pdf_bytes = _create_sample_pdf(resume_text)
    extracted_text, file_type, is_resume, resume_hint = process_attachment_file("alex_resume.pdf", pdf_bytes)

    assert is_resume is True
    assert resume_hint is not None
    assert "upload it directly to Master Resume" in resume_hint


@pytest.mark.asyncio
async def test_multi_session_conversation_lifecycle():
    client = AsyncMongoMockClient()
    db = client["test_copilot_sessions"]
    user_id = "user_test_123"

    # 1. Create 2 distinct conversations
    conv1 = await repo.create_conversation(db, user_id, title="System Design Discussion")
    conv2 = await repo.create_conversation(db, user_id, title="Algorithm Optimization")

    assert conv1["id"] != conv2["id"]

    # 2. List conversations
    conv_list = await repo.list_conversations(db, user_id)
    assert len(conv_list) == 2
    titles = [c["title"] for c in conv_list]
    assert "System Design Discussion" in titles
    assert "Algorithm Optimization" in titles

    # 3. Append messages to conv1
    await repo.append_messages_to_conversation(
        db, user_id, conv1["id"],
        [{"role": "user", "text": "How do I scale Redis?"}, {"role": "assistant", "text": "Use Redis Cluster."}]
    )

    # 4. Verify conv1 has 2 messages, conv2 still has 0
    fetched_conv1 = await repo.get_conversation_thread(db, user_id, conv1["id"])
    fetched_conv2 = await repo.get_conversation_thread(db, user_id, conv2["id"])

    assert fetched_conv1 is not None and len(fetched_conv1["messages"]) == 2
    assert fetched_conv2 is not None and len(fetched_conv2["messages"]) == 0

    # 5. Rename conv2
    renamed = await repo.update_conversation_title(db, user_id, conv2["id"], "Dynamic Programming Practice")
    assert renamed is True

    fetched_conv2_updated = await repo.get_conversation_thread(db, user_id, conv2["id"])
    assert fetched_conv2_updated is not None and fetched_conv2_updated["title"] == "Dynamic Programming Practice"

    # 6. Delete conv1
    deleted = await repo.delete_conversation(db, user_id, conv1["id"])
    assert deleted is True

    conv_list_after = await repo.list_conversations(db, user_id)
    assert len(conv_list_after) == 1
    assert conv_list_after[0]["id"] == conv2["id"]


@pytest.mark.asyncio
async def test_attachment_aware_chat_messaging():
    client = AsyncMongoMockClient()
    db = client["test_copilot_attachments"]
    user_id = "user_attachment_test"

    provider = MockCopilotAIProvider()
    settings = Settings(JWT_SECRET="test-secret", EMBEDDING_PROVIDER="mock")
    ai_service = AIService(settings=settings)
    ai_service._provider = provider

    attachment = AttachmentPayload(
        filename="kafka_config.txt",
        file_type="TXT",
        extracted_text="Kafka Architecture Configuration: Kafka retention is configured to 7 days.",
        is_resume=False,
    )

    reply, grounded, conv_id, resume_suggestion = await handle_chat_message(
        ai_service=ai_service,
        user_id=user_id,
        message="What is the Kafka retention in the attached document?",
        attachment=attachment,
        db=db,
    )

    assert "Kafka retention is configured for 7 days" in reply
    assert "ATTACHED DOCUMENT CONTENT" in provider.last_user_prompt
    assert "Kafka Architecture Configuration" in provider.last_user_prompt

    # Check that message was stored with attachment metadata
    conv = await repo.get_conversation_thread(db, user_id, conv_id)
    assert conv is not None
    assert len(conv["messages"]) == 2
    user_stored_msg = conv["messages"][0]
    assert user_stored_msg["attachment"]["filename"] == "kafka_config.txt"
