"""Tests for request identity resolution (X-QCrBox-User + service token / Remote-User)."""

import pytest
from litestar import Litestar, get
from litestar.di import Provide
from litestar.testing import TestClient

from pyqcrbox.registry.server.api.identity import get_current_user
from pyqcrbox.settings import settings

TOKEN = "test-service-token"


@get(path="/whoami", sync_to_thread=False)
def whoami(current_user: str | None) -> dict:
    return {"user": current_user}


@pytest.fixture
def identity_client():
    app = Litestar(route_handlers=[whoami], dependencies={"current_user": Provide(get_current_user)})
    with TestClient(app=app) as client:
        yield client


@pytest.fixture
def auth_settings():
    original_token = settings.auth.service_token
    original_trust = settings.auth.trust_remote_user_headers
    settings.auth.service_token = TOKEN
    settings.auth.trust_remote_user_headers = True
    yield settings.auth
    settings.auth.service_token = original_token
    settings.auth.trust_remote_user_headers = original_trust


def whoami_response(client, headers):
    return client.get("/whoami", headers=headers).json()["user"]


def test_no_headers_is_anonymous(identity_client, auth_settings):
    assert whoami_response(identity_client, {}) is None


def test_claimed_user_with_valid_token(identity_client, auth_settings):
    headers = {"X-QCrBox-User": "alice", "X-QCrBox-Service-Token": TOKEN}
    assert whoami_response(identity_client, headers) == "alice"


def test_claimed_user_with_wrong_token_is_ignored(identity_client, auth_settings):
    headers = {"X-QCrBox-User": "alice", "X-QCrBox-Service-Token": "wrong"}
    assert whoami_response(identity_client, headers) is None


def test_claimed_user_without_token_is_ignored(identity_client, auth_settings):
    assert whoami_response(identity_client, {"X-QCrBox-User": "alice"}) is None


def test_claimed_user_ignored_when_no_token_configured(identity_client, auth_settings):
    auth_settings.service_token = None
    headers = {"X-QCrBox-User": "alice", "X-QCrBox-Service-Token": "anything"}
    assert whoami_response(identity_client, headers) is None


def test_remote_user_is_trusted_by_default(identity_client, auth_settings):
    assert whoami_response(identity_client, {"Remote-User": "bob"}) == "bob"


def test_remote_user_not_trusted_when_disabled(identity_client, auth_settings):
    auth_settings.trust_remote_user_headers = False
    assert whoami_response(identity_client, {"Remote-User": "bob"}) is None


def test_valid_service_claim_takes_precedence_over_remote_user(identity_client, auth_settings):
    headers = {"X-QCrBox-User": "alice", "X-QCrBox-Service-Token": TOKEN, "Remote-User": "bob"}
    assert whoami_response(identity_client, headers) == "alice"


def test_invalid_service_claim_falls_back_to_remote_user(identity_client, auth_settings):
    headers = {"X-QCrBox-User": "alice", "X-QCrBox-Service-Token": "wrong", "Remote-User": "bob"}
    assert whoami_response(identity_client, headers) == "bob"
