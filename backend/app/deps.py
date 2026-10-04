from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.content_repo import ContentRepository
from app.repositories.student_repo import StudentRepository
from app.repositories.session_repo import SessionRepository
from app.services.auth_service import AuthService
from app.services.tutor_service import TutorService
from app.services.rag_service import RAGService


# --- Repositories ---
def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_content_repo(db: AsyncSession = Depends(get_db)) -> ContentRepository:
    return ContentRepository(db)

def get_student_repo(db: AsyncSession = Depends(get_db)) -> StudentRepository:
    return StudentRepository(db)

def get_session_repo(db: AsyncSession = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


# --- Services ---
def get_auth_service(repo: UserRepository = Depends(get_user_repo)) -> AuthService:
    return AuthService(repo)

def get_tutor_service(
    s: SessionRepository = Depends(get_session_repo),
    st: StudentRepository = Depends(get_student_repo),
    c: ContentRepository = Depends(get_content_repo),
) -> TutorService:
    return TutorService(s, st, c)

def get_rag_service(c: ContentRepository = Depends(get_content_repo)) -> RAGService:
    return RAGService(c)