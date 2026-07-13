from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class STSException(HTTPException):
    """Base system unified exception class."""
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message

class AuthInvalidException(STSException):
    def __init__(self, message: str = "Invalid credentials provided."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTH_INVALID",
            message=message,
            headers={"WWW-Authenticate": "Bearer"}
        )

class TokenExpiredException(STSException):
    def __init__(self, message: str = "Token has expired."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_EXPIRED",
            message=message
        )

class TokenInvalidException(STSException):
    def __init__(self, message: str = "Token is invalid."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_INVALID",
            message=message
        )

class OTPExpiredException(STSException):
    def __init__(self, message: str = "OTP code has expired."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="OTP_EXPIRED",
            message=message
        )

class OTPInvalidException(STSException):
    def __init__(self, message: str = "Invalid OTP code."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="OTP_INVALID",
            message=message
        )

class UserNotFoundException(STSException):
    def __init__(self, message: str = "User not found."):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message=message
        )

class EmailExistsException(STSException):
    def __init__(self, message: str = "Email already registered."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="EMAIL_EXISTS",
            message=message
        )

class InsufficientPermissionsException(STSException):
    def __init__(self, message: str = "Insufficient permissions to access this resource."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="INSUFFICIENT_PERMISSIONS",
            message=message
        )

class RateLimitExceededException(STSException):
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message=message
        )
