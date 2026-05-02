from __future__ import annotations
from services.storage.base import IStorage
from src.pipeline.context import PipelineContext
from src.pipeline.stages.base import PipelineStage
from core.exceptions import UnsupportedFileTypeError, FileTooLargeError
from utils.file_handler import detect_mime_type, is_supported, extension_for, human_size
from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


class IngestStage(PipelineStage):
    """Validates and stores the incoming document in object storage.

    Responsibilities
    ----------------
    1. Enforce file size limit.
    2. Detect MIME type from magic bytes (ignores the Content-Type header).
    3. Reject unsupported MIME types before they touch the LLM pipeline.
    4. Upload the raw bytes to object storage and record the storage key.
    """

    name = "ingest"

    def __init__(
        self,
        storage: IStorage,
        max_size_bytes: int = _DEFAULT_MAX_BYTES,
    ) -> None:
        self._storage = storage
        self._max_size = max_size_bytes

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        # ── Size guard ───────────────────────────────────────────────────────
        if len(ctx.raw_bytes) > self._max_size:
            msg = (
                f"File size {human_size(len(ctx.raw_bytes))} exceeds "
                f"limit of {human_size(self._max_size)}"
            )
            ctx.abort(self.name, msg)
            raise FileTooLargeError(msg)

        # ── MIME detection ───────────────────────────────────────────────────
        detected = detect_mime_type(ctx.raw_bytes)
        if not is_supported(detected):
            msg = f"File type '{detected}' is not supported by this platform"
            ctx.abort(self.name, msg)
            raise UnsupportedFileTypeError(msg)

        ctx.mime_type = detected

        # ── Object storage ───────────────────────────────────────────────────
        ext = extension_for(detected)
        storage_key = f"{ctx.tenant_id}/{ctx.job_id}/source{ext}"
        await self._storage.upload(storage_key, ctx.raw_bytes, content_type=detected)
        ctx.storage_key = storage_key

        logger.info(
            "ingest_ok",
            job_id=ctx.job_id,
            key=storage_key,
            mime=detected,
            size=human_size(len(ctx.raw_bytes)),
        )
        return ctx
