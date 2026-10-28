import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import init_db
from app.routers import academics, ai, auth, courses, dashboard, documents
from app.services import predictor

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    predictor.ensure_model()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="EduPilot AI API",
    version="1.0.0",
    description="Academic performance and study management - REST API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    logging.getLogger("app").warning("Integrity error: %s", exc.orig)
    return JSONResponse(status_code=409, content={"detail": "This record conflicts with existing data or violates a constraint"})


for r in (auth.router, auth.admin_router, courses.router, academics.router, dashboard.router, ai.router, documents.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "database": "postgresql" if settings.is_postgres else "sqlite", "llm_enabled": settings.llm_enabled}
