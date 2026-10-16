import datetime as dt
import hashlib
import hmac
import re
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import SESSION_DAYS
from .db import get_db
from .models import SessionToken, User, utcnow

PBKDF2_ITERATIONS = 240_000


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_contact(raw: str) -> str | None:
    """Email jadi huruf kecil; nomor HP jadi angka saja dengan awalan 0 (6281.. / +6281.. -> 081..)."""
    value = raw.strip()
    if "@" in value:
        value = value.lower()
        return value if EMAIL_RE.match(value) else None
    digits = re.sub(r"\D", "", value)
    if digits.startswith("62"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 15 and digits.startswith("0") else None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(SessionToken(token_hash=_token_hash(token), user_id=user.id,
                        expires_at=utcnow() + dt.timedelta(days=SESSION_DAYS)))
    user.last_login_at = utcnow()
    return token


def delete_session(db: Session, token: str) -> None:
    row = db.get(SessionToken, _token_hash(token))
    if row:
        db.delete(row)


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise api_error(401, "unauthorized", "Silakan login dulu.")
    return authorization[7:].strip()


def current_user(token: str = Depends(bearer_token), db: Session = Depends(get_db)) -> User:
    row = db.get(SessionToken, _token_hash(token))
    if not row or row.expires_at < utcnow():
        raise api_error(401, "session_expired", "Sesi login sudah habis. Silakan login lagi.")
    return row.user
