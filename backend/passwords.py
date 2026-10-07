"""Password hashing with PBKDF2-HMAC-SHA256.

Two stored formats, both verified:
- New:    ``pbkdf2_sha256$<iterations>$<salt>$<hex digest>``   (iterations stored in the hash)
- Legacy: ``pbkdf2_sha256$<salt>$<hex digest>``                (seed data; always 120,000 iterations)

New hashes use 600,000 iterations (OWASP's current recommendation for PBKDF2-HMAC-SHA256)
and a new random 16-hex-character salt each time. Existing rows are never rewritten.
Digests are compared in constant time.

Uses Python's standard `hashlib.pbkdf2_hmac` (OpenSSL-backed) and `secrets`.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # for new hashes
LEGACY_ITERATIONS = 120_000  # hashes without a stored count (the seed data)
MAX_ITERATIONS = 5_000_000  # refuse absurd stored counts instead of hanging the server


def _digest(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    return f"{ALGORITHM}${ITERATIONS}${salt}${_digest(password, salt, ITERATIONS)}"


def _parse(stored: str) -> tuple[int, str, str] | None:
    """Return (iterations, salt, digest) for either format, or None if unrecognized."""
    parts = stored.split("$")
    if not parts or parts[0] != ALGORITHM:
        return None
    if len(parts) == 3:
        _, salt, digest = parts
        return LEGACY_ITERATIONS, salt, digest
    if len(parts) == 4:
        _, count, salt, digest = parts
        if not count.isdigit() or not 1 <= int(count) <= MAX_ITERATIONS:
            return None
        return int(count), salt, digest
    return None


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse(stored)
    if parsed is None:
        return False
    iterations, salt, digest = parsed
    return hmac.compare_digest(_digest(password, salt, iterations), digest)


# Checked against when the email doesn't exist, so a wrong email costs as much as a wrong password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
