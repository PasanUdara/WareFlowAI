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
    register_user,
    validate_registration_input,
    get_current_user,
    USERS_DB,
    verify_google_id_token,
)
from .sanitization import sanitize_user_input, sanitize_prompt_input
from .encryption import encrypt_data, decrypt_data

__all__ = [
    "create_access_token",
    "verify_token",
    "get_password_hash",
    "verify_password",
    "authenticate_user",
    "register_user",
    "validate_registration_input",
    "get_current_user",
    "USERS_DB",
    "verify_google_id_token",
    "sanitize_user_input",
    "sanitize_prompt_input",
    "encrypt_data",
    "decrypt_data",
]
