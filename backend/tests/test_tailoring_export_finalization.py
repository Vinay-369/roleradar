"""Regression tests for requiring finalized tailored resumes at export."""

from bson import ObjectId
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

from app.db.mongo import Collections
from app.modules.tailoring import repositories as tailoring_repo
from app.modules.tailoring import routes as tailoring_routes


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["roleradar_export_finalization_test"]


async def _create_version(db, *, finalized=False, changes=None):
    version = await tailoring_repo.create_version(
        db,
        user_id="test-user",
        job_id="test-job",
        job_title="Software Engineer",
        company="Example Co",
        changes=changes or [],
        parsed={
            "personal": {"name": "Test Candidate"},
            "summary": "Draft content containing a proposed change.",
            "skills": ["Python"],
        },
    )
    if finalized:
        version = await tailoring_repo.finalize_version(
            db,
            "test-user",
            str(version["_id"]),
            final_text="Final approved resume content.",
            parsed=version["parsed"],
        )
    return version


@pytest.mark.asyncio
@pytest.mark.parametrize("exporter", [tailoring_routes.export_pdf, tailoring_routes.export_docx])
async def test_unfinalized_version_cannot_be_exported(db, exporter):
    version = await _create_version(db)

    with pytest.raises(HTTPException) as exc_info:
        await exporter(str(version["_id"]), template="modern", current_user={"_id": "test-user"}, db=db)

    assert exc_info.value.status_code == 400
    assert "finalized" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_unapproved_proposal_does_not_make_draft_exportable(db):
    version = await _create_version(
        db,
        changes=[{
            "change_id": "proposal-1",
            "original": "Original bullet",
            "proposed": "Unapproved proposed bullet",
            "status": "PENDING",
        }],
    )
    await db[Collections.RESUME_VERSIONS].update_one(
        {"_id": version["_id"]},
        {"$set": {"final_text": "Draft text that must not be exported."}},
    )

    for exporter in (tailoring_routes.export_pdf, tailoring_routes.export_docx):
        with pytest.raises(HTTPException) as exc_info:
            await exporter(str(version["_id"]), template="modern", current_user={"_id": "test-user"}, db=db)
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exporter", "media_type"),
    [
        (tailoring_routes.export_pdf, "application/pdf"),
        (
            tailoring_routes.export_docx,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ],
)
async def test_finalized_version_can_still_be_exported(db, exporter, media_type):
    version = await _create_version(db, finalized=True)

    response = await exporter(str(version["_id"]), template="modern", current_user={"_id": "test-user"}, db=db)

    assert response.status_code == 200
    assert response.media_type == media_type
    assert response.body


@pytest.mark.asyncio
@pytest.mark.parametrize("exporter", [tailoring_routes.export_pdf, tailoring_routes.export_docx])
async def test_missing_or_invalid_version_ids_keep_existing_not_found_behavior(db, exporter):
    for version_id in ("not-an-object-id", str(ObjectId())):
        with pytest.raises(HTTPException) as exc_info:
            await exporter(version_id, template="modern", current_user={"_id": "test-user"}, db=db)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Version not found."
