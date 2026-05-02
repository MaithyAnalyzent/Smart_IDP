from __future__ import annotations
import time
from abc import ABC, abstractmethod

from src.pipeline.context import PipelineContext
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineStage(ABC):
    """Abstract base for every pipeline processing stage.

    Subclasses implement ``process()`` and declare a ``name`` property.
    Timing instrumentation and error logging are handled here automatically —
    stage authors only need to write the business logic.

    Stage contract
    --------------
    - Receive ``ctx``, mutate it, return it.
    - Call ``ctx.abort()`` to halt cleanly (no exception needed).
    - Raise an exception to signal an unrecoverable failure.
    - Never communicate with other stages except through ``ctx``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique slug used in logs and stage_timings. E.g. 'ingest'."""

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Execute this stage's logic. Must return ctx (mutated or not)."""

    async def __call__(self, ctx: PipelineContext) -> PipelineContext:
        start = time.monotonic()
        logger.info("stage_start", stage=self.name, job_id=ctx.job_id)
        try:
            ctx = await self.process(ctx)
        except Exception as exc:
            ctx.record_error(self.name, str(exc))
            logger.error(
                "stage_error", stage=self.name, job_id=ctx.job_id, error=str(exc)
            )
            raise
        finally:
            elapsed = round(time.monotonic() - start, 4)
            ctx.stage_timings[self.name] = elapsed
            logger.info(
                "stage_done",
                stage=self.name,
                job_id=ctx.job_id,
                elapsed_s=elapsed,
            )
        return ctx
