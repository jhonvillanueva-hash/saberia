import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Optional

from app.core.config import settings


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""
    pass


class TokenInvalidError(Exception):
    """Raised when a JWT token is invalid (not expired)."""
    pass


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    password_bytes = password.encode('utf-8')
    password_hash_bytes = password_hash.encode('utf-8')
    return bcrypt.checkpw(password_bytes, password_hash_bytes)


def create_access_token(user_id: UUID) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> UUID:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = UUID(payload["sub"])
        return user_id
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except (jwt.InvalidTokenError, jwt.DecodeError, KeyError, ValueError) as e:
        raise TokenInvalidError(f"Invalid token: {str(e)}")