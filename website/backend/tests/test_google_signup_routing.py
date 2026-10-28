"""The OAuth callback distinguishes account creation from ordinary sign-in."""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.mark.parametrize("kind", ["new", "returning", "linked"])
def test_google_login_reports_only_actual_account_creation(monkeypatch, kind):
    from src.auth import service
    from src.auth.models import AuthProvider, UserDocument

    now = datetime.now(timezone.utc)
    user = UserDocument(id="u_existing", email="shopper@example.com", name="Shopper", created_at=now, updated_at=now, auth_providers=[AuthProvider(provider="google", provider_user_id="google-id")])
    raw = user.to_mongo()
    results = {"new": [None, None], "returning": [raw], "linked": [None, raw, raw]}[kind]
    users = SimpleNamespace(find_one=AsyncMock(side_effect=results), insert_one=AsyncMock(), update_one=AsyncMock())
    monkeypatch.setattr(service, "users_col", lambda: users)
    monkeypatch.setattr(service, "_issue_tokens", AsyncMock(return_value=("access", "refresh", now)))
    result = asyncio.run(service.google_login("google-id", "shopper@example.com", True, "Shopper"))
    assert result[-1] is (kind == "new")
    assert users.insert_one.await_count == (1 if kind == "new" else 0)
    assert users.update_one.await_count == (1 if kind == "linked" else 0)


@pytest.mark.parametrize("new_account", [False, True])
def test_callback_marks_new_accounts_without_losing_studio_context(monkeypatch, new_account):
    from src.auth import controller
    from src.config import Settings

    monkeypatch.setattr(controller, "get_settings", lambda: Settings(app_env="development"))
    monkeypatch.setattr(controller.google_oauth, "exchange_code", AsyncMock(return_value={"access_token": "token"}))
    monkeypatch.setattr(controller.google_oauth, "fetch_userinfo", AsyncMock(return_value={"sub": "id", "email": "shopper@example.com", "email_verified": True}))
    monkeypatch.setattr(controller.service, "google_login", AsyncMock(return_value=(None, "access", "refresh", datetime.now(timezone.utc) + timedelta(days=1), new_account)))
    response = asyncio.run(controller.google_callback("code", "state", None, "state", "/studio?product=coat"))
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["next"] == ["/studio?product=coat"]
    assert query.get("newAccount") == (["1"] if new_account else None)
    assert "mirra_refresh=" in response.headers["set-cookie"]
