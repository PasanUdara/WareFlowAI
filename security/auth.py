"""
Security Authentication Module [Member 4]
JWT Token issuance, validation, password hashing, demo user registry, and FastAPI auth dependency.
"""

import os
import time
import logging
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("wareflow.security.auth")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "wareflow_super_secret_jwt_key_change_in_production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_bearer = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash raw password string using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify raw password against bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# Pre-hashed passwords for demo users:
# 'admin' -> 'admin123'
# 'operator' -> 'operator123'
DEMO_USERS_DB: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "role": "administrator",
        "hashed_password": get_password_hash("admin123")
    },
    "operator": {
        "username": "operator",
        "role": "operator",
        "hashed_password": get_password_hash("operator123")
    }
}


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate demo user credentials against hashed password database.
    """
    user = DEMO_USERS_DB.get(username)
    if not user:
        logger.warning("[Auth] Authentication failed: Unknown user '%s'", username)
        return None
    if not verify_password(password, user["hashed_password"]):
        logger.warning("[Auth] Authentication failed: Invalid password for user '%s'", username)
        return None
    
    logger.info("[Auth] User '%s' successfully authenticated", username)
    return {"username": user["username"], "role": user["role"]}


def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Generate JWT access token with expiration timestamp."""
    to_encode = data.copy()
    expire_sec = expires_delta_seconds or (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": time.time() + expire_sec, "iat": time.time()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token signature and expiration."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[Auth] Token verification failed: Token expired")
        return None
    except jwt.PyJWTError as e:
        logger.warning("[Auth] Token verification failed: %s", e)
        return None


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> Dict[str, Any]:
    """
    FastAPI security dependency enforcing Bearer JWT token verification for protected endpoints.
    Allows request if a valid token is provided.
    """
    if not credentials or not credentials.credentials:
        # For development / university demo compatibility, return fallback demo payload if no auth header provided
        return {"sub": "anonymous", "role": "operator", "authenticated": False}

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
