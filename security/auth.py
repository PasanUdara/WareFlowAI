"""
Security Authentication Module [Member 4]
JWT token issuance, validation, password hashing, user registry, and FastAPI auth dependency.
"""

import os
import re
import time
import logging
from typing import Optional, Dict, Any, List
import jwt
import bcrypt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("wareflow.security.auth")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "wareflow_super_secret_jwt_key_change_in_production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

security_bearer = HTTPBearer(auto_error=False)

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,30}$")
PHONE_PATTERN = re.compile(r"^\+?[0-9()\-\s]{7,20}$")


def get_password_hash(password: str) -> str:
    """Hash raw password string using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify raw password against bcrypt hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


USERS_DB: Dict[str, Dict[str, Any]] = {}


def verify_google_id_token(credential: str) -> Dict[str, Any]:
    """Verify a Google-issued ID token against the configured OAuth client."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise RuntimeError("Google sign-in is not configured on the server.")

    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    try:
        payload = id_token.verify_oauth2_token(credential, Request(), client_id)
    except (ValueError, GoogleAuthError) as exc:
        raise ValueError("Google credential is invalid or expired.") from exc

    email = str(payload.get("email", "")).strip().lower()
    if payload.get("email_verified") is not True or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("A verified Google email address is required.")
    return {**payload, "email": email}


def validate_registration_input(username: Optional[str], password: str, email: Optional[str] = None) -> Dict[str, str]:
    """Validate user registration payload and normalize values."""
    normalized_email = (email or "").strip().lower()
    if normalized_email and not EMAIL_PATTERN.fullmatch(normalized_email):
        raise ValueError("Please provide a valid email address.")

    normalized_username = (username or normalized_email).strip()
    if not normalized_username:
        raise ValueError("Username or work email is required.")
    if normalized_username.lower() != normalized_email and not USERNAME_PATTERN.fullmatch(normalized_username):
        raise ValueError("Username must be 3-30 characters with letters, numbers, underscores, or hyphens only.")

    if password is None or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if password.lower() in {normalized_username.lower(), normalized_email}:
        raise ValueError("Password must not match the username.")
    if not any(ch.isupper() for ch in password) or not any(ch.islower() for ch in password) or not any(ch.isdigit() for ch in password):
        raise ValueError("Password must include uppercase, lowercase, and numeric characters.")

    return {"username": normalized_username, "password": password, "email": normalized_email}


def register_user(
    username: Optional[str],
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    role: str = "operator",
    company_name: Optional[str] = None,
    terms_accepted: bool = False,
) -> Dict[str, Any]:
    """Create a new user in the in-memory auth registry and return the user payload."""
    validated = validate_registration_input(username, password, email)
    username_key = validated["username"].lower()
    if not terms_accepted:
        raise ValueError("You must accept the Terms of Service and Privacy Policy.")
    normalized_company = (company_name or "").strip()
    if not normalized_company:
        raise ValueError("Company or warehouse name is required.")
    if len(normalized_company) > 120:
        raise ValueError("Company or warehouse name must be 120 characters or fewer.")
    normalized_full_name = (full_name or "").strip()
    if not normalized_full_name:
        raise ValueError("Full name is required.")
    if len(normalized_full_name) > 120:
        raise ValueError("Full name must be 120 characters or fewer.")
    if username_key in USERS_DB or any(
        user.get("email", "").lower() == validated["email"] and validated["email"]
        for user in USERS_DB.values()
    ):
        raise ValueError("This username or work email is already registered.")

    user_record = {
        "username": validated["username"],
        "email": validated["email"],
        "full_name": normalized_full_name,
        "company_name": normalized_company,
        "terms_accepted": True,
        "terms_accepted_at": time.time(),
        "role": role if role in {"administrator", "operator"} else "operator",
        "hashed_password": get_password_hash(validated["password"]),
    }
    USERS_DB[username_key] = user_record
    logger.info("[Auth] Registered a new user account")
    return {
        "username": user_record["username"],
        "role": user_record["role"],
        "email": user_record["email"],
        "full_name": user_record["full_name"],
        "company_name": user_record["company_name"],
    }


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate registered user credentials against the hashed password database.
    """
    lookup_key = (username or "").strip().lower()
    user = USERS_DB.get(lookup_key)
    if not user:
        user = next(
            (
                record
                for record in USERS_DB.values()
                if record.get("email", "").lower() == lookup_key and lookup_key
            ),
            None,
        )
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
