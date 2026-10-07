"""Password hashing that matches the existing `users.password_hash` format.

Stored format: ``pbkdf2_sha256$<salt>$<hex digest>``
- PBKDF2-HMAC-SHA256 with 120,000 iterations (same as the seed data)
- a new random 16-hex-character salt for every password
- digest compared in constant time

Uses Python's standard `hashlib.pbkdf2_hmac` (OpenSSL-backed) and `secrets`.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000


def _digest(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    return f"{ALGORITHM}${salt}${_digest(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(_digest(password, salt), digest)


# Checked against when the email doesn't exist, so a wrong email takes as long as a wrong password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
