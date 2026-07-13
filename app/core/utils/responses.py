from contextvars import ContextVar
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field
from app.config.settings import settings

# Thread/Async-safe context variable to capture current request language preference
current_lang: ContextVar[str] = ContextVar("current_lang", default=settings.DEFAULT_LANG)

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    """Standardized Application API Response Structure."""
    success: bool = True
    code: str = "SUCCESS"
    message: str = "Operation completed successfully"
    logo_url: str = Field(default_factory=lambda: settings.LOGO_URL)
    lang: str = Field(default_factory=lambda: current_lang.get())
    data: Optional[T] = None

def make_response(
    data: Any = None,
    success: bool = True,
    code: str = "SUCCESS",
    message: str = "Operation completed successfully"
) -> dict:
    """Helper function to build consistent dict payloads (e.g. within handlers)."""
    return {
        "success": success,
        "code": code,
        "message": message,
        "logo_url": settings.LOGO_URL,
        "lang": current_lang.get(),
        "data": data or {}
    }
