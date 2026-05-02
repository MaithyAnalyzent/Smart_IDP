from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, JSON, String, Text, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _new_id() -> str:
    return str(uuid.uuid4())


class TenantProfile(Base):
    """An independent organisation or user group registered on the platform.

    Every pipeline job, document schema, and API key is scoped to a tenant,
    enabling full multi-tenancy without any shared state between tenants.
    """
    __tablename__ = "tenant_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    schemas: Mapped[list[DocumentSchema]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[PipelineJob]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class DocumentSchema(Base):
    """Defines the expected structure for a named document category.

    A tenant may have many schemas (one per document type they process).
    Each schema carries field definitions and validation rules that guide
    the extract and validate pipeline stages at runtime.
    """
    __tablename__ = "document_schemas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenant_profiles.id"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped[TenantProfile] = relationship(back_populates="schemas")
    field_schemas: Mapped[list[FieldSchema]] = relationship(
        back_populates="document_schema", cascade="all, delete-orphan"
    )
    rules: Mapped[list[ProcessingRule]] = relationship(
        back_populates="document_schema", cascade="all, delete-orphan"
    )


class FieldSchema(Base):
    """Describes a single extractable field within a DocumentSchema."""
    __tablename__ = "field_schemas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    schema_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_schemas.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), default="string")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")
    example_value: Mapped[str] = mapped_column(String(200), default="")

    document_schema: Mapped[DocumentSchema] = relationship(back_populates="field_schemas")


class ProcessingRule(Base):
    """A natural-language validation rule attached to a DocumentSchema.

    Rules are evaluated by the ValidateStage using an LLM. Severity controls
    whether a failure blocks downstream processing (error) or just warns (warning).
    """
    __tablename__ = "processing_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    schema_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_schemas.id"), nullable=False
    )
    rule_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="error")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    document_schema: Mapped[DocumentSchema] = relationship(back_populates="rules")


class PipelineJob(Base):
    """Tracks the full lifecycle of a single document processing run.

    Created immediately on document submission (status=queued) and updated
    by the background runner as each pipeline stage completes.
    """
    __tablename__ = "pipeline_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenant_profiles.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(260), default="")
    mime_type: Mapped[str] = mapped_column(String(80), default="")
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")

    document_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    extracted_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    validation_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    validation_issues: Mapped[list[dict]] = mapped_column(JSON, default=list)

    stage_timings: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    errors: Mapped[list[dict]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped[TenantProfile] = relationship(back_populates="jobs")
