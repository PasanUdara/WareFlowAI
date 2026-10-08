"""
Data Encryption Module [Member 4]
Provides payload data encryption and decryption capabilities using cryptography.
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Derive a consistent Fernet key from secret key
_raw_secret = os.getenv("JWT_SECRET_KEY", "wareflow_super_secret_jwt_key_change_in_production").encode()
_kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"wareflow_salt_constant",
    iterations=100000,
)
_key = base64.urlsafe_b64encode(_kdf.derive(_raw_secret))
_fernet = Fernet(_key)


def encrypt_data(plain_text: str) -> str:
    """Encrypt raw text into ciphertext base64 string."""
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt_data(cipher_text: str) -> str:
    """Decrypt ciphertext base64 string back into raw text."""
    if not cipher_text:
        return ""
    return _fernet.decrypt(cipher_text.encode()).decode()
