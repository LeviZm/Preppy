"""
User service for user management operations.

This service provides high-level user operations including registration,
authentication, and user retrieval following Phase 1 requirements.
"""

from typing import Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from ..models import User
from ..extensions import db
from .exceptions import ValidationError, ConflictError, AuthError, NotFoundError
from .transaction import atomic


def register_user(payload: dict) -> User:
    """
    Register a new user with validation and uniqueness checks.
    
    Args:
        payload: Dictionary containing user registration data
                - username: str (required)
                - email: str (required) 
                - password: str (required, min 8 chars)
    
    Returns:
        Created User object
    
    Raises:
        ValidationError: if input is invalid
        ConflictError: if username or email already exists
    """
    username = payload.get("username", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    
    # Validation
    if not username:
        raise ValidationError("Username is required.")
    if not email:
        raise ValidationError("Email is required.")
    if not password:
        raise ValidationError("Password is required.")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if len(username) > 50:
        raise ValidationError("Username must be 50 characters or less.")
    if len(email) > 120:
        raise ValidationError("Email must be 120 characters or less.")
    
    # Check uniqueness
    if User.query.filter_by(username=username).first():
        raise ConflictError("Username already exists.")
    if User.query.filter_by(email=email).first():
        raise ConflictError("Email already exists.")
    
    # Create user with atomic transaction
    with atomic():
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()  # Get the user ID before commit
        db.session.commit()
    
    return user


def authenticate_user(email: str, password: str) -> str:
    """
    Authenticate user credentials with timing-safe password checking.
    
    Args:
        email: User email address
        password: User password
    
    Returns:
        JWT access token
    
    Raises:
        ValidationError: if email or password is missing/invalid
        AuthError: if credentials are invalid (same message for both cases)
    """
    email = email.strip().lower()
    
    if not email or not password:
        raise ValidationError("Email and password are required.")
    
    user = User.query.filter_by(email=email).first()
    
    # Always check password hash to prevent timing attacks
    # even when user is None
    password_valid = False
    if user:
        password_valid = check_password_hash(user.password_hash, password)
    else:
        # Check dummy hash to maintain consistent timing
        check_password_hash("dummy_hash", password)
    
    if not password_valid:
        raise AuthError("Invalid email or password.")
    
    # Create JWT token with user ID as identity (converted to string for JWT)
    token = create_access_token(identity=str(user.id))
    return token


def get_user_by_id(user_id: int) -> User:
    """
    Retrieve user by primary key.
    
    Args:
        user_id: User's primary key ID
    
    Returns:
        User object
    
    Raises:
        NotFoundError: if user is not found
    """
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("User not found.")
    return user
