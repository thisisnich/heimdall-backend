"""
Auth — JWT-based authentication for Heimdall.

Single-user (personal assistant) model — no database user table needed yet.
Credentials are stored in .env (ADMIN_USERNAME / ADMIN_PASSWORD).

Endpoints:
  POST /auth/login     → returns access_token
  GET  /auth/me        → returns current user info (requires token)
  POST /auth/refresh   → issues a fresh token given a valid one

FastAPI dependency:
  require_auth  → use as Depends(require_auth) on any protected route

Token lifetime: JWT_EXPIRE_MINUTES (default 7 days — convenient for personal use)
"""

import os
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Config ────────────────────────────────────────────────────────────────────
JWT_SECRET    = os.getenv("JWT_SECRET", "insecure-default-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE    = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

_ph = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Pre-hash the admin password at startup
_ADMIN_HASH = _ph.hash(ADMIN_PASSWORD)


# ── Models ────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class TokenData(BaseModel):
    username: str


class UserInfo(BaseModel):
    username: str
    is_admin: bool = True


# ── Helpers ───────────────────────────────────────────────────────────────────
def _create_token(username: str, expire_minutes: int = JWT_EXPIRE) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            raise JWTError("Missing subject")
        return TokenData(username=username)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Dependency ────────────────────────────────────────────────────────────────
async def require_auth(token: str = Depends(oauth2_scheme)) -> UserInfo:
    """
    FastAPI dependency. Add to any route that should require login:
      async def my_route(user: UserInfo = Depends(require_auth)):
    """
    token_data = _decode_token(token)
    if token_data.username != ADMIN_USERNAME:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return UserInfo(username=token_data.username)


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    Standard OAuth2 password flow. Returns a JWT bearer token.
    Use with: Authorization: Bearer <token>
    """
    if form.username != ADMIN_USERNAME or not _verify_password(form.password, _ADMIN_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _create_token(form.username)
    logger.info(f"Login: {form.username}")
    return Token(access_token=token, expires_in_minutes=JWT_EXPIRE)


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(require_auth)):
    """Returns current authenticated user info."""
    return user


@router.post("/refresh", response_model=Token)
async def refresh(user: UserInfo = Depends(require_auth)):
    """Issues a new token given a valid existing token. Extends the session."""
    token = _create_token(user.username)
    return Token(access_token=token, expires_in_minutes=JWT_EXPIRE)
