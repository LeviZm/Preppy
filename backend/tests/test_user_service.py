"""Tests for user services."""

# pylint: disable=redefined-outer-name,unused-argument

import pytest
from ..services.exceptions import ValidationError, ConflictError, AuthError
from ..services import auth_services as auth_service

def test_register_requires_password(app_context):
    """Test that registering a user requires a password."""

    with pytest.raises(ValidationError, match="Password is required"):
        auth_service.register_user({"username": "ada", "email": "ada@example.com", "password": ""})

def test_register_enforces_minimum_length(app_context):
    """Test registering a user with a password that is too short."""

    with pytest.raises(ValidationError, match="at least 10 characters"):
        auth_service.register_user(
            {
            "username": "ada",
             "email": "ada@example.com",
             "password": "abc"
             }
        )

def test_register_rejects_duplicate_email(app_context, existing_user):
    """Test that registering a user with an existing email fails."""

    with pytest.raises(ConflictError):
        auth_service.register_user(
            {
            "username": "newname",
            "email": existing_user.email,
            "password": "validpassword1"
            }
        )

def test_authenticate_wrong_password(app_context, existing_user):
    """Test authentication with the wrong password."""

    with pytest.raises(AuthError, match="Invalid email or password"):
        auth_service.authenticate_user(existing_user.email, "wrongpassword")

def test_authenticate_unknown_email(app_context):
    with pytest.raises(AuthError, match="Invalid email or password"):
        auth_service.authenticate_user("ghost@example.com", "anypassword")