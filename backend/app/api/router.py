from fastapi import APIRouter
from app.api.v1 import (
    auth, curriculum, tutor, ingest, dashboard, concepts,
    teacher, teacher_ingest, public, analytics,
)

api_router = APIRouter()
api_router.include_router(public.router, prefix="/public", tags=["public"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
api_router.include_router(teacher.router, prefix="/teacher", tags=["teacher"])
api_router.include_router(teacher_ingest.router, prefix="/teacher/ingest", tags=["teacher-ingest"])
api_router.include_router(tutor.router, prefix="/tutor", tags=["tutor"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
