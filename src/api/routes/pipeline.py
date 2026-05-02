from __future__ import annotations
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import DocumentSchema, FieldSchema, PipelineJob, ProcessingRule, TenantProfile
from core.schemas import JobStatusResponse, JobSubmitResponse
from services.database.session import get_session, get_session_factory
from services.llm import get_llm_provider
from services.storage.s3_store import S3Store
from src.pipeline.context import PipelineContext
from src.pipeline.runner import PipelineRunner
from src.pipeline.stages.classify import ClassifyStage
from src.pipeline.stages.extract import ExtractStage
from src.pipeline.stages.ingest import IngestStage
from src.pipeline.stages.validate import ValidateStage
from configs.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["Pipeline"])


def _build_runner() -> PipelineRunner:
    """Assemble the default four-stage pipeline from registered services."""
    settings = get_settings()
    storage = S3Store()
    llm = get_llm_provider()
    return PipelineRunner([
        IngestStage(storage, max_size_bytes=settings.MAX_FILE_SIZE_MB * 1024 * 1024),
        ClassifyStage(llm),
        ExtractStage(llm),
        ValidateStage(llm),
    ])


async def _load_schema_hints(
    session: AsyncSession, tenant_id: str, doc_type: str
) -> tuple[list[str], list[dict]]:
    """Fetch field hints and validation rules for a tenant+doc_type combination."""
    result = await session.execute(
        select(DocumentSchema).where(
            DocumentSchema.tenant_id == tenant_id,
            DocumentSchema.doc_type == doc_type,
            DocumentSchema.is_active == True,
        )
    )
    schema = result.scalar_one_or_none()
    if not schema:
        return [], []

    fields_result = await session.execute(
        select(FieldSchema).where(FieldSchema.schema_id == schema.id)
    )
    rules_result = await session.execute(
        select(ProcessingRule).where(
            ProcessingRule.schema_id == schema.id,
            ProcessingRule.is_active == True,
        )
    )
    field_hints = [f.field_name for f in fields_result.scalars().all()]
    rules = [
        {"rule_description": r.rule_description, "severity": r.severity}
        for r in rules_result.scalars().all()
    ]
    return field_hints, rules


async def _execute_pipeline(
    job_id: str,
    tenant_id: str,
    raw_bytes: bytes,
    filename: str,
    mime_type: str,
) -> None:
    """Background task: run the pipeline and persist results."""
    factory = get_session_factory()
    ctx = PipelineContext(
        job_id=job_id,
        tenant_id=tenant_id,
        raw_bytes=raw_bytes,
        filename=filename,
        mime_type=mime_type,
    )
    runner = _build_runner()
    final_status = "completed"

    try:
        ctx = await runner.run(ctx)

        # After classify, load schema-specific hints for a second extraction pass
        # if doc_type now matches a known schema for this tenant
        if ctx.document_type and not ctx.extracted_fields:
            async with factory() as session:
                hints, rules = await _load_schema_hints(
                    session, tenant_id, ctx.document_type
                )
                ctx.metadata["field_hints"] = hints
                ctx.metadata["validation_rules"] = rules

        if ctx.errors:
            final_status = "completed_with_errors"

    except Exception as exc:
        logger.error("pipeline_failed", job_id=job_id, error=str(exc))
        ctx.record_error("runner", str(exc))
        final_status = "failed"

    async with factory() as session:
        job = await session.get(PipelineJob, job_id)
        if job:
            job.status = final_status
            job.storage_key = ctx.storage_key
            job.document_type = ctx.document_type
            job.classification_confidence = ctx.classification_confidence
            job.extracted_fields = ctx.extracted_fields
            job.validation_status = ctx.validation_status
            job.validation_issues = ctx.validation_issues
            job.stage_timings = ctx.stage_timings
            job.errors = ctx.errors
            job.completed_at = datetime.now(timezone.utc)
        await session.commit()


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=JobSubmitResponse, status_code=202)
async def submit_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to process"),
    tenant_id: str = Form(..., description="Tenant identifier"),
    session: AsyncSession = Depends(get_session),
) -> JobSubmitResponse:
    """Submit a document for pipeline processing.

    Returns immediately with a job ID. Poll ``GET /api/v1/jobs/{job_id}``
    to retrieve status and results once processing completes.
    """
    tenant = await session.get(TenantProfile, tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Tenant not found or inactive.")

    raw_bytes = await file.read()
    job_id = str(uuid.uuid4())

    job = PipelineJob(
        id=job_id,
        tenant_id=tenant_id,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        status="queued",
    )
    session.add(job)
    await session.commit()

    background_tasks.add_task(
        _execute_pipeline,
        job_id=job_id,
        tenant_id=tenant_id,
        raw_bytes=raw_bytes,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
    )

    logger.info("job_submitted", job_id=job_id, tenant=tenant_id, file=file.filename)
    return JobSubmitResponse(job_id=job_id, status="queued")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobStatusResponse:
    """Retrieve the current status and results of a pipeline job."""
    job = await session.get(PipelineJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse.model_validate(job)
