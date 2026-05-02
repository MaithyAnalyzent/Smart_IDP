from __future__ import annotations
from src.pipeline.context import PipelineContext
from src.pipeline.stages.base import PipelineStage
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineRunner:
    """Executes an ordered sequence of PipelineStages, threading PipelineContext
    through each one.

    This is the sole orchestration primitive in the platform.  There are no
    external frameworks, no message brokers, and no state machines — just a
    plain Python loop that calls each stage in turn.

    Abort behaviour
    ---------------
    If a stage sets ``ctx.should_abort = True`` the runner logs the remaining
    stages as skipped and exits early without raising.  The job is then
    persisted with whatever partial results were collected.

    Error behaviour
    ---------------
    Unhandled exceptions propagate out of ``run()`` to the background task
    wrapper in the API layer, which catches them, marks the job as failed, and
    persists the error details.
    """

    def __init__(self, stages: list[PipelineStage]) -> None:
        self._stages = stages

    @property
    def stage_names(self) -> list[str]:
        return [s.name for s in self._stages]

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        logger.info("pipeline_start", job_id=ctx.job_id, stages=self.stage_names)

        for stage in self._stages:
            if ctx.should_abort:
                remaining = [
                    s.name for s in self._stages[self._stages.index(stage):]
                ]
                logger.warning(
                    "pipeline_aborted",
                    job_id=ctx.job_id,
                    skipped=remaining,
                )
                break
            ctx = await stage(ctx)

        logger.info(
            "pipeline_complete",
            job_id=ctx.job_id,
            doc_type=ctx.document_type,
            validation_status=ctx.validation_status,
            errors=len(ctx.errors),
        )
        return ctx
