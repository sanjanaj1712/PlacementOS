"""Shared fixtures for the PlacementOS API tests.

The tests run against a real, disposable PostgreSQL database given by
TEST_DATABASE_URL. They wipe user data between tests, so they refuse to
run against anything other than a local database.
"""

import os
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import jwt
import psycopg
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres@127.0.0.1:54329/placementos_test"
)

if urlparse(TEST_DATABASE_URL).hostname not in ("localhost", "127.0.0.1", "::1"):
    raise RuntimeError(
        "TEST_DATABASE_URL must point at a local, disposable database"
    )

TEST_SUPABASE_URL = "http://supabase.test"
TEST_JWT_SECRET = "test-jwt-secret-that-is-at-least-32-bytes-long"

# Set before importing the app so load_dotenv() does not pick up real values.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SUPABASE_URL"] = TEST_SUPABASE_URL
os.environ["SUPABASE_KEY"] = "test-publishable-key"
os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET

sys.path.insert(0, str(BACKEND_DIR))

import app as app_module  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    """Load the schema and seed data into the test database."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as connection:
        for path in (
            BACKEND_DIR / "tests" / "sql" / "supabase_stub.sql",
            BACKEND_DIR / "db" / "schema.sql",
            BACKEND_DIR / "db" / "seed.sql",
        ):
            connection.execute(path.read_text())


@pytest.fixture(autouse=True)
def clean_users():
    """Remove all users; foreign keys cascade to their data."""
    yield
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as connection:
        connection.execute("DELETE FROM auth.users")


@pytest.fixture
def db():
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as connection:
        yield connection


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def make_token(user_id, email=None, **overrides):
    claims = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iss": f"{TEST_SUPABASE_URL}/auth/v1",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    claims = {key: value for key, value in claims.items() if value is not None}
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


class ApiUser:
    def __init__(self, client, user_id, email):
        self.client = client
        self.id = user_id
        self.email = email
        self.token = make_token(user_id, email)

    def request(self, method, path, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        return self.client.open(path, method=method, headers=headers, **kwargs)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)


@pytest.fixture
def make_user(client, db):
    def factory(email=None):
        user_id = str(uuid.uuid4())
        email = email or f"{user_id[:8]}@example.com"
        db.execute(
            "INSERT INTO auth.users (id, email) VALUES (%s, %s)",
            (user_id, email)
        )
        return ApiUser(client, user_id, email)

    return factory


@pytest.fixture
def user_a(make_user):
    return make_user("a@example.com")


@pytest.fixture
def user_b(make_user):
    return make_user("b@example.com")
