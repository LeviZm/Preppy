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
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="test-secret-key",
    )

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


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
