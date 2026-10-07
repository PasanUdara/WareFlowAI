"""
Security Package [Member 4]
Provides JWT-based authentication, user authorization, input sanitization,
prompt injection defense, and cryptographic hashing.
"""

from .auth import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    authenticate_user,
    get_current_user,
    DEMO_USERS_DB,
)
from .sanitization import sanitize_user_input, sanitize_prompt_input
from .encryption import encrypt_data, decrypt_data

__all__ = [
    "create_access_token",
    "verify_token",
    "get_password_hash",
    "verify_password",
    "authenticate_user",
    "get_current_user",
    "DEMO_USERS_DB",
    "sanitize_user_input",
    "sanitize_prompt_input",
    "encrypt_data",
    "decrypt_data",
]
