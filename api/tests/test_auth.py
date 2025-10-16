import os

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jose import jwt

# Ensure the secret key is deterministic for tests before importing app/auth.
os.environ["DASHBOARD_MASTER_PASSWORD"] = "test-secret"

from api.auth import (  # type: ignore  # pylint: disable=wrong-import-position
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    TokenData,
    create_access_token,
    verify_token,
)
from api.main import app  # type: ignore  # pylint: disable=wrong-import-position


client = TestClient(app)


def test_login_success_returns_signed_token():
    response = client.post("/auth/login", json={"master_password": "test-secret"})
    assert response.status_code == 200

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    payload = jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "dashboard_user"
    assert "Administrator" in payload["roles"]
    assert payload["read_only"] is False


def test_login_rejects_invalid_password():
    response = client.post("/auth/login", json={"master_password": "wrong"})
    assert response.status_code == 401


def test_create_access_token_preserves_claims():
    token = create_access_token(
        data={
            "sub": "unit-test-user",
            "roles": ["Moderator"],
            "scopes": ["dashboard:read"],
            "read_only": True,
        }
    )

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["roles"] == ["Moderator"]
    assert payload["scopes"] == ["dashboard:read"]
    assert payload["read_only"] is True


def test_verify_token_returns_token_data():
    token = create_access_token(data={"sub": "verifier", "roles": ["Viewer"]})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    token_data = verify_token(credentials)
    assert isinstance(token_data, TokenData)
    assert token_data.username == "verifier"
    assert token_data.roles == ["Viewer"]
