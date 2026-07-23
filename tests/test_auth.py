import os
import pytest
import jwt
from fastapi import HTTPException
from unittest.mock import patch

os.environ.setdefault("RECOUP_SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("RECOUP_SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("RECOUP_SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("RECOUP_SUPABASE_JWT_SECRET", "test-jwt-secret")

from app.auth import get_current_user  # noqa: E402
from app.config import get_settings  # noqa: E402


class FakeRequest:
    def __init__(self, token=None):
        self.cookies = {"access_token": token} if token else {}
        self.headers = {}


@pytest.mark.asyncio
async def test_forged_unsigned_token_is_rejected():
    """A token forged with alg=none (no valid signature) must be rejected,
    not silently trusted. Regression test for the verify_signature=False bug."""
    get_settings.cache_clear()
    forged = jwt.encode(
        {"sub": "attacker-uuid", "email": "admin@example.com"},
        key="",
        algorithm="none",
    )
    request = FakeRequest(token=forged)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_signed_token_is_accepted():
    get_settings.cache_clear()
    settings = get_settings()
    token = jwt.encode(
        {"sub": "user-uuid", "email": "user@example.com", "aud": "authenticated"},
        key=settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    request = FakeRequest(token=token)
    fake_profile = type("R", (), {"data": {"organization_id": "org-1", "role": "member"}})()
    with patch("app.auth.get_supabase_admin") as mock_admin:
        mock_admin.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = fake_profile
        user = await get_current_user(request)
    assert user.id == "user-uuid"
    assert user.organization_id == "org-1"
