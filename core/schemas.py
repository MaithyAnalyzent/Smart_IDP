from __future__ import annotations
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Tenant ───────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    settings: dict[str, Any] = Field(default_factory=dict)


class TenantResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Document Schema ──────────────────────────────────────────────────────────

class FieldSchemaCreate(BaseModel):
    field_name: str = Field(..., min_length=1, max_length=80)
    field_type: str = Field("string", pattern="^(string|number|date|boolean|list|object)$")
    required: bool = False
    description: str = ""
    example_value: str = ""


class ProcessingRuleCreate(BaseModel):
    rule_description: str = Field(..., min_length=5)
    severity: str = Field("error", pattern="^(error|warning)$")


class DocumentSchemaCreate(BaseModel):
    doc_type: str = Field(..., min_length=1, max_length=80)
    description: str = ""
    field_schemas: list[FieldSchemaCreate] = Field(default_factory=list)
    rules: list[ProcessingRuleCreate] = Field(default_factory=list)


class DocumentSchemaResponse(BaseModel):
    id: str
    tenant_id: str
    doc_type: str
    description: str
    is_active: bool
    field_count: int = 0
    rule_count: int = 0

    model_config = {"from_attributes": True}


# ─── Pipeline Job ─────────────────────────────────────────────────────────────

class JobSubmitResponse(BaseModel):
    job_id: str
    status: str
    message: str = "Job accepted and queued for processing."


class JobStatusResponse(BaseModel):
    job_id: str
    tenant_id: str
    filename: str
    status: str
    document_type: str | None
    classification_confidence: float
    extracted_fields: dict[str, Any]
    validation_status: str | None
    validation_issues: list[dict]
    stage_timings: dict[str, float]
    errors: list[dict]
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    job_id: str
    filename: str
    status: str
    document_type: str | None
    validation_status: str | None
    created_at: datetime
    completed_at: datetime | None


class JobExportResponse(BaseModel):
    job_id: str
    document_type: str | None
    extracted_fields: dict[str, Any]
    validation_status: str | None
    processing_time_ms: int
