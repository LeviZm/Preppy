"""
Shared pytest fixtures for all backend tests.

Provides:
  - app_context: a Flask app context backed by an in-memory SQLite DB,
                 with all tables created and torn down per test.
  - db_session:  the SQLAlchemy session active inside app_context.
  - existing_user: a pre-registered User with a known hashed password,
                   used by auth service tests.
"""

# pylint: disable=redefined-outer-name

import os

# Set test environment BEFORE any imports (load_dotenv runs at module level)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from werkzeug.security import generate_password_hash

from ..app import create_app
from ..extensions import db as _db
from ..models import User


@pytest.fixture(scope="function")
def app_context():
    """
    Create a Flask app configured for testing with an in-memory SQLite DB.
    Yields the app context; all tables are created before the test and
    dropped after it, giving each test a clean slate.
    """
    app = create_app()
    app.config.update(
        TESTING=True,
        JWT_SECRET_KEY="test-secret-key",
    )

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app_context):
    """Flask test client for making HTTP requests."""
    return app_context.test_client()


def create_test_user(username: str, email: str, password: str = "ValidPassword1"):
    """Helper to create a test user in the database."""
    from ..models import User
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    _db.session.add(user)
    _db.session.commit()
    return user


def create_test_recipe(owner, name: str, instructions: str = ""):
    """Helper to create a test recipe in the database."""
    from ..models import Recipe
    recipe = Recipe(
        name=name,
        instructions=instructions,
        owner_user_id=owner.id,
    )
    _db.session.add(recipe)
    _db.session.commit()
    return recipe


@pytest.fixture(scope="function")
def db_session(app_context):
    """Expose the active SQLAlchemy session for direct DB assertions."""
    _ = app_context
    return _db.session


@pytest.fixture(scope="function")
def existing_user(app_context):
    """
    A User already in the database with a known password.
    Password is 'ValidPassword1' — satisfies the 10-character minimum.
    """
    _ = app_context
    user = User(
        username="existinguser",
        email="existing@example.com",
        password_hash=generate_password_hash("ValidPassword1"),
    )
    _db.session.add(user)
    _db.session.commit()
    return user


# Textbook fixtures for ownership testing
@pytest.fixture(scope="function")
def user_a(app_context):
    """Alice - first test user for ownership tests."""
    _ = app_context
    user = create_test_user("alice", "alice@test.com")
    return user


@pytest.fixture(scope="function")
def user_b(app_context):
    """Bob - second test user for ownership tests."""
    _ = app_context
    user = create_test_user("bob", "bob@test.com")
    return user


@pytest.fixture(scope="function")
def recipe_owned_by_a(app_context, user_a):
    """A recipe created by user_a (Alice) for ownership tests."""
    _ = app_context
    recipe = create_test_recipe(user_a, "Alice's Secret Recipe")
    return recipe
