"""
Settings for the Flask application.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

from urllib.parse import quote

load_dotenv()


def _require_secret_key() -> str:
    """
    Fail fast when SECRET_KEY is missing.

    The application signs JWTs with this value, so starting without it would
    create a confusing runtime failure later in the auth flow.
    """
    raise EnvironmentError(
        "SECRET_KEY environment variable is not set. "
        "This key is required to sign JWT tokens for user authentication. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )


def build_uri() -> str:
    """
    Build the SQLAlchemy database URI from environment variables.

    This prefers DATABASE_URL when it is available because that is the most
    portable deployment shape for production hosts. If DATABASE_URL is absent,
    the function falls back to composing a PostgreSQL URI from individual
    environment values for local development.
    """
    # Get the database URL from environment variables
    database_url = os.environ.get("DATABASE_URL")

    # SQLAlchemy requires "postgresql://"
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    # If no database URL is found, build it from the environment
    user = os.environ.get("USER")
    password = os.environ.get("PASSWORD")
    host = os.environ.get("HOST")
    port = os.environ.get("PORT")
    dbname = os.environ.get("DBNAME")

    # Check required fields
    if not all([user, password, host, port, dbname]):
        raise ValueError("Missing required environment variables for database connection")

    # Build the database URI
    assert password is not None
    encoded_password = quote(password, safe="")

    return (
        f"postgresql://{user}:{encoded_password}"
        f"@{host}:{port}/{dbname}"
    )

class Config:
    """
    Base Flask configuration for the backend.

    The values here are loaded by the app factory so the same code can run in
    development, tests, and production with different environment variables.
    """

    SQLALCHEMY_DATABASE_URI: str = build_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    SECRET_KEY: str = os.environ.get("SECRET_KEY") or _require_secret_key()

    # JWT Configuration
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=30)

    # Security settings
    SESSION_COOKIE_SECURE: bool = False  # Set True in production for HTTPS only
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    # API settings
    JSON_SORT_KEYS: bool = False
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB max request size
