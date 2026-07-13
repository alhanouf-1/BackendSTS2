from app.routers.auth import router as auth_router
from app.routers.public import router as public_router
from app.routers.health import router as health_router
from app.routers.student import router as student_router
from app.routers.teacher import router as teacher_router
from app.routers.ai_engine import router as ai_engine_router

__all__ = [
    "auth_router",
    "public_router",
    "health_router",
    "student_router",
    "teacher_router",
    "ai_engine_router",
]
