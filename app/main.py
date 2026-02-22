"""FIRE — FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.persistence.database import engine
from app.infrastructure.api.routes_analytics import router as analytics_router
from app.infrastructure.api.routes_assistant import router as assistant_router
from app.infrastructure.api.routes_health import router as health_router
from app.infrastructure.api.routes_processing import router as processing_router
from app.infrastructure.api.routes_tickets import router as tickets_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    try:
        async with engine.begin():
            pass  # Connection pool warmed up
        logger.info("Database connection established")
    except Exception as e:
        logger.warning("Database not available on startup: %s", e)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="FIRE — Freedom Intelligent Routing Engine",
        description="Automatic ticket processing, AI enrichment, and smart assignment",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:3005",
            "http://127.0.0.1:3005",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router, prefix="/api")
    app.include_router(tickets_router, prefix="/api")
    app.include_router(processing_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(assistant_router, prefix="/api")

    return app


app = create_app()
