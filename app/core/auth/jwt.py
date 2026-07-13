import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from app.config.settings import settings
from app.core.utils.exceptions import TokenExpiredException, TokenInvalidException

def create_access_token(subject: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a secure HS256 JWT Access Token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "type": "access"
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT Access Token.
    Raises TokenExpiredException or TokenInvalidException.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise TokenInvalidException("Invalid token type inside token payload.")
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException("Access token has expired.")
    except JWTError:
        raise TokenInvalidException("Could not validate authorization credentials.")

def generate_refresh_token_string() -> str:
    """
    Generates a unique high-entropy random string representing a Refresh Token.
    """
    return f"rf_{uuid.uuid4().hex}{uuid.uuid4().hex}"
