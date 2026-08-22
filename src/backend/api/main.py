from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.backend.db.connection import engine, Base

from src.backend.api.routes_tle import router as tle_router
from src.backend.api.routes_conjunction import router as conjunction_router
from src.backend.api.routes_risk import router as risk_router
from src.backend.api.routes_maneuver import router as maneuver_router
from src.backend.api.routes_dashboard import router as dashboard_router
from src.backend.api.routes_ingest import router as ingest_router
from src.backend.api.websocket import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("RADAR Backend starting up...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")
    yield
    # Shutdown
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
app.include_router(tle_router)
app.include_router(conjunction_router)
app.include_router(risk_router)
app.include_router(maneuver_router)
app.include_router(dashboard_router)
app.include_router(ingest_router)
app.include_router(websocket_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    return {"message": "Welcome to RADAR Backend API. See /docs for the interactive documentation."}
