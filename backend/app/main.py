from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import settings
from app.api.router import api_router
from app.db.session import engine

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", env=settings.ENV)
    yield
    await engine.dispose()
    logger.info("shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS — must be the OUTERMOST middleware so errors also get CORS headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Catch-all exception handler that still returns CORS-friendly JSON
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.ENV}
