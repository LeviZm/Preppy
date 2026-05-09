"""Authentication service placeholders"""

from typing import Dict, Any

from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token
from ..models import User
from ..extensions import db
from .exceptions import ValidationError, ConflictError, AuthError, NotFoundError


def register_user(payload: dict) -> User:
    """
    Register a new user.
    """

    username = payload.get("username","")
    email = payload.get("email", "").strip().lower()
    password = payload.get("password","")

    # Validate username
    if not username:
        raise ValidationError("Username is required.")
    if len(username) < 3:
        raise ValidationError("Username must be at least 3 characters long.")
    if len(username) > 50:
        raise ValidationError("Username must be less than 50 characters long.")

    # Validate email
    if not email or "@" not in email:
        raise ValidationError("A valid email address is required.")

    # Validate password
    if not password:
        raise ValidationError("Password is required.")
    if len(password) < 10:
        raise ValidationError("Password must be at least 10 characters long.")
    if len(password) > 128:
        raise ValidationError("Password must be less than 128 characters long.")

    # Check uniqueness
    if User.query.filter_by(username=username).first():
        raise ConflictError("An account with that username or email already exists.")
    if User.query.filter_by(email=email).first():
        raise ConflictError("An account with that username or email already exists.")

    # Hash password and persists
    password_hash = generate_password_hash(password)
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return user

def authenticate_user(email: str, password: str) -> str:
    """
    Authenticate a user.
    Verify credentials and return a signed JWT on success.
    
    Raises:
        AuthError: if the email is not found or the password does not match.
                   both cases return the same message to prevent enumeration
    """

    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()

    # Check password even if user is None, to prevent timing attacks
    if not user or not check_password_hash(user.password_hash, password):
        raise AuthError("Invalid email or password.")

    token = create_access_token(identity=user.id)
    return token

def get_user_by_id(user_id: int) -> Dict[str, Any]:
    """
    Get user by ID. Placeholder implementation.
    
    Raises:
        NotFoundError: if the user is not found.
    """

    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("User not found.")
    return user
