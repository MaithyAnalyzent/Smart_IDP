from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware import RequestLoggingMiddleware
from src.api.routes import config, pipeline, results
from services.database.session import create_tables
from configs.settings import get_settings
from utils.logger import get_logger, setup_logging

settings = get_settings()
setup_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.APP_NAME, env=settings.APP_ENV)
    await create_tables()
    yield
    logger.info("shutdown", app=settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Doc Intelligence Platform",
        description=(
            "A generic, pipeline-based document intelligence API. "
            "Define your document types and validation rules via the config endpoints, "
            "then submit documents for automatic classification, extraction, and validation."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — locked by default.
    # Set ALLOWED_ORIGINS in .env to a comma-separated list of permitted origins.
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(pipeline.router, prefix="/api/v1")
    app.include_router(config.router,   prefix="/api/v1")
    app.include_router(results.router,  prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": "1.0.0", "app": settings.APP_NAME}

    return app


app = create_app()
