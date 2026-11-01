"""
Field-level encryption for personal details saved with an appointment request
(patient name, phone number, reason for visit).

Fernet = AES-128-CBC + HMAC-SHA256 (from the `cryptography` package). A database
file that leaks on its own does not reveal those fields.

Key: DATA_ENCRYPTION_KEY from .env if set, otherwise derived from SECRET_KEY.
IMPORTANT: if you change the key, old appointment details can no longer be read.
Set DATA_ENCRYPTION_KEY once and keep it separate from SECRET_KEY.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

PREFIX = "enc1:"


def _fernet() -> Fernet:
    raw = os.getenv("DATA_ENCRYPTION_KEY") or ("healthcare-data|" + (os.getenv("SECRET_KEY") or ""))
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def encrypt(value):
    if value is None or value == "":
        return value
    return PREFIX + _fernet().encrypt(str(value).encode("utf-8")).decode("ascii")


def decrypt(value):
    if not isinstance(value, str) or not value.startswith(PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return "[unreadable: encryption key changed]"
