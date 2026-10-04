from fastapi import APIRouter
from app.api.v1 import auth, curriculum, tutor, ingest, dashboard

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
api_router.include_router(tutor.router, prefix="/tutor", tags=["tutor"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])