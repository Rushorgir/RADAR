from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.backend.api.routes_conjunction import router as conjunction_router
from src.backend.api.routes_dashboard import router as dashboard_router
from src.backend.api.routes_dataset import router as dataset_router
from src.backend.api.routes_ingest import router as ingest_router
from src.backend.api.routes_launch import router as launch_router
from src.backend.api.routes_maneuver import router as maneuver_router
from src.backend.api.routes_reentry import router as reentry_router
from src.backend.api.routes_risk import router as risk_router
from src.backend.api.routes_tle import router as tle_router
from src.backend.api.websocket import router as websocket_router
from src.backend.db.connection import Base, engine

# Keep a reference so the task isn't garbage-collected.
_background_tasks: set[asyncio.Task] = set()


async def _run_pipeline_background():
    """Run the ingestion pipeline in the background after startup."""
    try:
        await asyncio.sleep(5)
        logger.info("Starting automatic dataset ingestion pipeline...")
        process = await asyncio.create_subprocess_exec(
            sys.executable, "scripts/run_radar_pipeline.py", "--post-to-backend",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            logger.info("Automatic pipeline completed successfully.")
        else:
            logger.error(f"Pipeline failed (rc={process.returncode}): {stderr.decode()}")
    except Exception as e:
        logger.error(f"Failed to run pipeline in background: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RADAR Backend starting up...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    if os.getenv("RADAR_AUTO_INGEST", "").lower() in ("1", "true", "yes"):
        task = asyncio.create_task(_run_pipeline_background())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    else:
        logger.info("Auto-ingest disabled (set RADAR_AUTO_INGEST=1 to enable).")

    yield
    logger.info("RADAR Backend shutting down.")


app = FastAPI(
    title="RADAR Backend API",
    description="API for the RADAR/OrbitGuard project",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dataset_router)
app.include_router(tle_router)
app.include_router(conjunction_router)
app.include_router(risk_router)
app.include_router(maneuver_router)
app.include_router(dashboard_router)
app.include_router(ingest_router)
app.include_router(reentry_router)
app.include_router(launch_router)
app.include_router(websocket_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    return {"message": "Welcome to RADAR Backend API. See /docs for the interactive documentation."}
