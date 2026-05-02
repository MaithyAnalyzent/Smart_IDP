from __future__ import annotations
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import DocumentSchema, FieldSchema, ProcessingRule, TenantProfile
from core.schemas import (
    DocumentSchemaCreate,
    DocumentSchemaResponse,
    TenantCreate,
    TenantResponse,
)
from services.database.session import get_session
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/config", tags=["Configuration"])


# ─── Tenant Management ────────────────────────────────────────────────────────

@router.post("/tenants", response_model=dict, status_code=201)
async def create_tenant(
    payload: TenantCreate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Register a new tenant.

    Returns the tenant ID and a one-time API key — store it securely,
    it will not be shown again.
    """
    exists = await session.execute(
        select(TenantProfile).where(TenantProfile.name == payload.name)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A tenant with this name already exists.")

    api_key = secrets.token_urlsafe(32)
    tenant = TenantProfile(
        name=payload.name,
        api_key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
        settings=payload.settings,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    logger.info("tenant_created", tenant_id=tenant.id, name=tenant.name)
    return {
        "tenant_id": tenant.id,
        "name": tenant.name,
        "api_key": api_key,
        "note": "Store this API key securely — it will not be shown again.",
    }


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str, session: AsyncSession = Depends(get_session)
) -> TenantResponse:
    """Retrieve a tenant by ID."""
    tenant = await session.get(TenantProfile, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return TenantResponse.model_validate(tenant)


# ─── Document Schema Management ───────────────────────────────────────────────

@router.post(
    "/tenants/{tenant_id}/schemas",
    response_model=DocumentSchemaResponse,
    status_code=201,
)
async def create_schema(
    tenant_id: str,
    payload: DocumentSchemaCreate,
    session: AsyncSession = Depends(get_session),
) -> DocumentSchemaResponse:
    """Define a document schema for a tenant.

    A schema groups:
    - ``field_schemas``   — extractable field definitions (name, type, required)
    - ``rules``           — plain-English validation rules evaluated by the LLM
    """
    if not await session.get(TenantProfile, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found.")

    schema = DocumentSchema(
        tenant_id=tenant_id,
        doc_type=payload.doc_type,
        description=payload.description,
    )
    session.add(schema)
    await session.flush()

    for f in payload.field_schemas:
        session.add(FieldSchema(schema_id=schema.id, **f.model_dump()))
    for r in payload.rules:
        session.add(ProcessingRule(schema_id=schema.id, **r.model_dump()))

    await session.commit()
    await session.refresh(schema)
    logger.info("schema_created", schema_id=schema.id, doc_type=schema.doc_type)

    return DocumentSchemaResponse(
        id=schema.id,
        tenant_id=schema.tenant_id,
        doc_type=schema.doc_type,
        description=schema.description,
        is_active=schema.is_active,
        field_count=len(payload.field_schemas),
        rule_count=len(payload.rules),
    )


@router.get(
    "/tenants/{tenant_id}/schemas",
    response_model=list[DocumentSchemaResponse],
)
async def list_schemas(
    tenant_id: str, session: AsyncSession = Depends(get_session)
) -> list[DocumentSchemaResponse]:
    """List all active document schemas for a tenant."""
    result = await session.execute(
        select(DocumentSchema).where(
            DocumentSchema.tenant_id == tenant_id,
            DocumentSchema.is_active == True,
        )
    )
    return [
        DocumentSchemaResponse(
            id=s.id,
            tenant_id=s.tenant_id,
            doc_type=s.doc_type,
            description=s.description,
            is_active=s.is_active,
        )
        for s in result.scalars().all()
    ]


@router.delete("/tenants/{tenant_id}/schemas/{schema_id}", status_code=204)
async def deactivate_schema(
    tenant_id: str,
    schema_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Soft-delete a document schema (sets is_active=False)."""
    schema = await session.get(DocumentSchema, schema_id)
    if not schema or schema.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schema not found.")
    schema.is_active = False
    await session.commit()
