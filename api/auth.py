"""
Authentication utilities for the API.

Manages JWT issuance and verification while exposing typed token data to the
rest of the application.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

ENV_PATH = Path(__file__).resolve().parent.parent / ".env.local"

# Load environment variables without clobbering process overrides
load_dotenv(ENV_PATH, override=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours
security = HTTPBearer()


@lru_cache()
def resolve_secret_key() -> str:
    """
    Resolve the master secret used for JWT signing.

    Priority: explicit environment variable, then .env.local fallback, finally
    a hard-coded development default (which should be overridden in prod).
    """
    secret = os.getenv("DASHBOARD_MASTER_PASSWORD")
    if secret:
        return secret
    return "default-secret-key-change-in-production"


SECRET_KEY = resolve_secret_key()


class TokenData(BaseModel):
    """
    Auth context propagated through dependencies.
    """

    username: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    read_only: bool = False

    @property
    def is_admin(self) -> bool:
        return any(role.lower() == "administrator" for role in self.roles)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Issue a signed JWT embedding optional role/scope metadata.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Verify a bearer token and return the associated auth context.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    username: Optional[str] = payload.get("sub")
    if username is None:
        raise credentials_exception

    roles = payload.get("roles") or []
    scopes = payload.get("scopes") or []
    read_only = bool(payload.get("read_only", False))

    if not isinstance(roles, list):
        roles = [str(roles)]
    if not isinstance(scopes, list):
        scopes = [str(scopes)]

    return TokenData(
        username=username,
        roles=[str(role) for role in roles],
        scopes=[str(scope) for scope in scopes],
        read_only=read_only,
    )


def get_current_user(token_data: TokenData = Depends(verify_token)) -> TokenData:
    """
    Dependency to ensure the caller is authenticated.
    """
    return token_data


def get_current_authenticated_user(token_data: TokenData = Depends(verify_token)) -> TokenData:
    """
    Legacy alias maintained for backwards compatibility.
    """
    return token_data
