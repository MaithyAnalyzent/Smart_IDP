from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import PipelineJob
from core.schemas import JobExportResponse, JobListItem
from services.database.session import get_session
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/results", tags=["Results"])


@router.get("/tenants/{tenant_id}/jobs", response_model=list[JobListItem])
async def list_jobs(
    tenant_id: str,
    status: str | None = Query(None, description="Filter by job status"),
    doc_type: str | None = Query(None, description="Filter by detected document type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[JobListItem]:
    """List pipeline jobs for a tenant with optional filters."""
    conditions = [PipelineJob.tenant_id == tenant_id]
    if status:
        conditions.append(PipelineJob.status == status)
    if doc_type:
        conditions.append(PipelineJob.document_type == doc_type)

    result = await session.execute(
        select(PipelineJob)
        .where(and_(*conditions))
        .order_by(PipelineJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        JobListItem(
            job_id=j.id,
            filename=j.filename,
            status=j.status,
            document_type=j.document_type,
            validation_status=j.validation_status,
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in result.scalars().all()
    ]


@router.get("/jobs/{job_id}/export", response_model=JobExportResponse)
async def export_job(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> JobExportResponse:
    """Return a flat export of extracted fields suitable for downstream systems."""
    job = await session.get(PipelineJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status not in ("completed", "completed_with_errors"):
        raise HTTPException(
            status_code=409,
            detail=f"Job results are not yet available (status: {job.status}).",
        )
    total_ms = int(sum(job.stage_timings.values()) * 1000)
    return JobExportResponse(
        job_id=job.id,
        document_type=job.document_type,
        extracted_fields=job.extracted_fields,
        validation_status=job.validation_status,
        processing_time_ms=total_ms,
    )


@router.get("/jobs/{job_id}/issues")
async def get_validation_issues(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    """Return validation issues for a completed job."""
    job = await session.get(PipelineJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "job_id": job.id,
        "validation_status": job.validation_status,
        "issues": job.validation_issues,
        "issue_count": len(job.validation_issues),
    }
