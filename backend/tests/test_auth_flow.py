"""
Backend auth flow tests for MyHostIQ.
Verifies fixes for register/login endpoints post the 500-error deploy bug.
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://thesis-deployment.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

# Unique per test run to avoid rate-limit collisions & duplicates from re-runs
RUN_ID = uuid.uuid4().hex[:8]
NEW_USER_EMAIL = f"test.debug+{RUN_ID}@example.com"
NEW_USER_PASSWORD = "TestPass123!"
NEW_USER_NAME = "Test Debug User"
NEW_USER_PHONE = "+1234567890"

EXISTING_USER_EMAIL = "test.debug@example.com"
EXISTING_USER_PASSWORD = "TestPass123!"


@pytest.fixture(scope="session")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def registration_result(api_client):
    """Register the new unique user for this run. Shared across tests."""
    payload = {
        "email": NEW_USER_EMAIL,
        "password": NEW_USER_PASSWORD,
        "full_name": NEW_USER_NAME,
        "phone": NEW_USER_PHONE,
    }
    resp = api_client.post(f"{API}/auth/register", json=payload)
    return resp


# ---------- Basic API health ----------
class TestBasics:
    def test_api_root(self, api_client):
        r = api_client.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0


# ---------- Registration ----------
class TestRegistration:
    def test_register_success(self, registration_result):
        r = registration_result
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "access_token" in data and isinstance(data["access_token"], str) and len(data["access_token"]) > 0
        assert data.get("token_type") == "bearer"
        assert "user" in data
        assert data["user"]["email"] == NEW_USER_EMAIL
        assert data["user"]["full_name"] == NEW_USER_NAME
        assert "id" in data["user"]

    def test_register_duplicate_email_returns_400(self, api_client, registration_result):
        # Ensure prior registration succeeded before checking duplicate handling
        assert registration_result.status_code == 200
        payload = {
            "email": NEW_USER_EMAIL,
            "password": NEW_USER_PASSWORD,
            "full_name": NEW_USER_NAME,
            "phone": NEW_USER_PHONE,
        }
        r = api_client.post(f"{API}/auth/register", json=payload)
        # Must be 400, not 500 (the reported bug)
        assert r.status_code == 400, f"Expected 400 for duplicate email, got {r.status_code}: {r.text}"
        body = r.json()
        msg = (body.get("detail") or body.get("message") or "").lower()
        assert "already registered" in msg or "email" in msg, f"Unexpected error body: {body}"

    def test_register_invalid_email_returns_422(self, api_client):
        payload = {
            "email": "not-an-email",
            "password": "TestPass123!",
            "full_name": "Invalid Email User",
            "phone": "+1234567890",
        }
        r = api_client.post(f"{API}/auth/register", json=payload)
        assert r.status_code == 422, f"Expected 422 for invalid email, got {r.status_code}: {r.text}"


# ---------- Login ----------
class TestLogin:
    def test_login_success_new_user(self, api_client, registration_result):
        assert registration_result.status_code == 200
        r = api_client.post(f"{API}/auth/login", json={
            "email": NEW_USER_EMAIL,
            "password": NEW_USER_PASSWORD,
        })
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "access_token" in data and len(data["access_token"]) > 0
        assert data["user"]["email"] == NEW_USER_EMAIL

    def test_login_wrong_password_returns_401(self, api_client, registration_result):
        assert registration_result.status_code == 200
        r = api_client.post(f"{API}/auth/login", json={
            "email": NEW_USER_EMAIL,
            "password": "WrongPassword!!!",
        })
        # Must be 401, not 500 (the reported bug)
        assert r.status_code == 401, f"Expected 401 for wrong password, got {r.status_code}: {r.text}"
        body = r.json()
        msg = (body.get("detail") or body.get("message") or "").lower()
        assert "invalid" in msg or "credentials" in msg, f"Unexpected error body: {body}"

    def test_login_nonexistent_user_returns_401(self, api_client):
        r = api_client.post(f"{API}/auth/login", json={
            "email": f"nonexistent-{RUN_ID}@example.com",
            "password": "AnyPass123!",
        })
        assert r.status_code == 401, f"Expected 401 for unknown user, got {r.status_code}: {r.text}"


# ---------- Authenticated endpoints ----------
@pytest.fixture(scope="session")
def access_token(api_client, registration_result):
    if registration_result.status_code != 200:
        pytest.skip(f"Registration failed, cannot get access token: {registration_result.status_code}")
    return registration_result.json()["access_token"]


class TestAuthenticated:
    def test_get_me(self, api_client, access_token):
        r = api_client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert r.status_code == 200, f"/auth/me failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["email"] == NEW_USER_EMAIL
        assert data["full_name"] == NEW_USER_NAME
        assert "id" in data

    def test_get_me_without_token_unauthorized(self, api_client):
        r = api_client.get(f"{API}/auth/me")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_get_apartments_with_token(self, api_client, access_token):
        r = api_client.get(f"{API}/apartments", headers={"Authorization": f"Bearer {access_token}"})
        assert r.status_code == 200, f"/apartments failed: {r.status_code} {r.text}"
        data = r.json()
        # Response should be a list (may be empty for new user)
        assert isinstance(data, list), f"Expected list from /apartments, got {type(data).__name__}: {data}"

    def test_get_apartments_without_token_unauthorized(self, api_client):
        r = api_client.get(f"{API}/apartments")
        assert r.status_code in (401, 403), f"Expected 401/403 for unauth, got {r.status_code}"
