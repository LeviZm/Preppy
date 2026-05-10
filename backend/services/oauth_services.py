"""
OAuth services for Google, Apple, and Microsoft authentication.

All providers follow the same flow:
1. Verify the token with the provider's API
2. Extract email from the verified payload
3. Find or create user in database
4. Return a JWT access token
"""

import os
import re
import secrets
import requests
from typing import cast

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from google.oauth2 import id_token as google_id_token_lib
from google.auth.transport import requests as google_requests
from flask_jwt_extended import create_access_token
import jwt as pyjwt
from jwt.algorithms import RSAAlgorithm

from ..models import User
from ..extensions import db
from .exceptions import AuthError, ValidationError
from .transaction import atomic

# =============================================================================
# Provider Configuration (loaded from environment)
# =============================================================================

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")  # Bundle ID for apps, Service ID for web
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")  # 10-character Apple Developer Team ID
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")  # Azure AD Application ID

# =============================================================================
# Public Interface
# =============================================================================

def authenticate_oauth_user(provider: str, token: str) -> str:
    """
    Authenticate a user via OAuth provider.
    
    Args:
        provider: One of 'google', 'apple', 'microsoft'
        token: The OAuth token from the provider (ID token for Google/Apple, access token for MS)
    
    Returns:
        JWT access token for the authenticated user
    
    Raises:
        ValidationError: If provider is unsupported
        AuthError: If token is invalid or verification fails
    """

    handlers = {
        "google": _authenticate_google,
        "apple": _authenticate_apple,
        "microsoft": _authenticate_microsoft,
    }

    handler = handlers.get(provider.lower())
    if not handler:
        raise ValidationError(f"Unsupported OAuth provider: {provider}")

    return handler(token)


# =============================================================================
# Google OAuth
# =============================================================================

def _authenticate_google(token: str) -> str:
    """
    Verify Google ID token and authenticate user.
    
    Google's ID token is a JWT signed by Google. We verify it using Google's
    auth library which handles signature validation and expiration checks.
    """

    if not GOOGLE_CLIENT_ID:
        raise AuthError("Google OAuth is not configured.")

    try:
        # Verify the token with Google's servers
        request = google_requests.Request()
        payload = google_id_token_lib.verify_oauth2_token(
            token,
            request,
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )

        # Extract user info
        email = payload.get("email", "").strip().lower()
        if not email:
            raise AuthError("Google token did not contain an email address.")

        # Google accounts are email-verified by default
        if not payload.get("email_verified", False):
            raise AuthError("Google email is not verified.")

        name = payload.get("name", "")

    except ValueError as e:
        raise AuthError(f"Invalid Google token: {e}") from e
    except Exception as e:
        raise AuthError(f"Google authentication failed: {e}") from e

    return _find_or_create_oauth_user(email, name, "google")


# =============================================================================
# Apple OAuth
# =============================================================================

def _authenticate_apple(token: str) -> str:
    """
    Verify Apple ID token and authenticate user.
    
    Apple uses Sign in with Apple (SIWA) which returns an identity token.
    We verify it by fetching Apple's public keys and validating the JWT signature.
    
    Note: Apple tokens don't include the user's name on subsequent sign-ins,
    only on the first authentication. Apps should cache this on first login.
    """

    if not APPLE_CLIENT_ID or not APPLE_TEAM_ID:
        raise AuthError("Apple OAuth is not configured.")

    try:
        # Fetch Apple's public keys
        jwks_response = requests.get("https://appleid.apple.com/auth/keys", timeout=10)
        jwks_response.raise_for_status()
        jwks = jwks_response.json()

        # Decode without verification first to get the key ID
        unverified_header = pyjwt.get_unverified_header(token)
        key_id = unverified_header.get("kid")

        if not key_id:
            raise AuthError("Apple token missing key ID.")

        # Find the matching public key
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == key_id:
                public_key = RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            raise AuthError("Unable to find matching Apple public key.")

        # Verify the token
        payload = pyjwt.decode(
            token,
            cast(RSAPublicKey, public_key),
            algorithms=["RS256"],
            audience=APPLE_CLIENT_ID,
            issuer="https://appleid.apple.com"
        )

        email = payload.get("email", "").strip().lower()
        if not email:
            raise AuthError("Apple token did not contain an email address.")

        # Apple tokens are always email-verified
        # Extract name if present (only on first login)
        name = ""

    except pyjwt.ExpiredSignatureError as e:
        raise AuthError("Apple token has expired.") from e
    except pyjwt.InvalidTokenError as e:
        raise AuthError(f"Invalid Apple token: {e}") from e
    except requests.RequestException as e:
        raise AuthError(f"Failed to contact Apple servers: {e}") from e
    except Exception as e:
        raise AuthError(f"Apple authentication failed: {e}") from e

    return _find_or_create_oauth_user(email, name, "apple")


# =============================================================================
# Microsoft OAuth
# =============================================================================

def _authenticate_microsoft(access_token: str) -> str:
    """
    Verify Microsoft access token and authenticate user.
    
    Microsoft uses Azure AD / Microsoft Identity Platform.
    Unlike Google/Apple, we validate the access token by calling Microsoft's
    userinfo endpoint, which both validates the token and returns user data.
    """

    if not MICROSOFT_CLIENT_ID:
        raise AuthError("Microsoft OAuth is not configured.")

    try:
        # Call Microsoft Graph API to get user info and validate token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers,
            timeout=10
        )

        if response.status_code == 401:
            raise AuthError("Invalid Microsoft access token.")

        response.raise_for_status()
        user_data = response.json()

        email = user_data.get("mail", "").strip().lower()
        if not email:
            # Fallback to userPrincipalName which often contains email
            email = user_data.get("userPrincipalName", "").strip().lower()

        if not email:
            raise AuthError("Microsoft token did not contain an email address.")

        name = user_data.get("displayName", "")

    except requests.RequestException as e:
        raise AuthError(f"Failed to verify Microsoft token: {e}") from e
    except Exception as e:
        raise AuthError(f"Microsoft authentication failed: {e}") from e

    return _find_or_create_oauth_user(email, name, "microsoft")


# =============================================================================
# Shared Helper Functions
# =============================================================================

def _find_or_create_oauth_user(email: str, name: str, provider: str) -> str:
    """
    Find existing user by email or create a new OAuth user.
    
    OAuth users get:
    - Email from the OAuth provider (verified)
    - Auto-generated username from email or name
    - Random secure password (they'll never use it, OAuth only)
    
    Returns:
        JWT access token for the user
    """

    # Try to find existing user by email
    user = User.query.filter_by(email=email).first()

    if user:
        # User exists - return token
        return create_access_token(identity=user.id)

    # Create new OAuth user
    username = _generate_username(email, name)
    random_password = secrets.token_urlsafe(32)

    with atomic(f"Failed to create OAuth user from {provider}."):
        user = User(
            username=username,
            email=email,
            password_hash=random_password  # Will be hashed by model or manually
        )
        # Hash the password properly
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash(random_password)

        db.session.add(user)

    return create_access_token(identity=user.id)


def _generate_username(email: str, name: str) -> str:
    """
    Generate a unique username from email or name.
    
    Strategy:
    1. Try email local part (before @)
    2. Try lowercase name with underscores
    3. Append random suffix until unique
    """

    base_candidates = []

    # Try email local part
    if email and "@" in email:
        local_part = email.split("@")[0]
        # Clean: remove non-alphanumeric, ensure starts with letter
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', local_part)
        if cleaned and len(cleaned) >= 3:
            base_candidates.append(cleaned[:20])

    # Try name
    if name:
        # Convert "John Doe" -> "john_doe"
        name_cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip().lower()
        name_underscored = name_cleaned.replace(" ", "_")
        if len(name_underscored) >= 3:
            base_candidates.append(name_underscored[:20])

    # Fallback
    if not base_candidates:
        base_candidates = ["user"]

    # Try each candidate with increasing suffixes
    for base in base_candidates:
        # Try without suffix first
        if not User.query.filter_by(username=base).first():
            return base

        # Try with random suffix
        for _ in range(10):
            suffix = secrets.token_hex(4)
            candidate = f"{base}_{suffix}"
            if len(candidate) > 50:
                candidate = f"{base[:40]}_{suffix}"
            if not User.query.filter_by(username=candidate).first():
                return candidate

    # Ultimate fallback: random username
    while True:
        random_name = f"user_{secrets.token_hex(8)}"
        if not User.query.filter_by(username=random_name).first():
            return random_name


# Backward compatibility
def authenticate_google_user(token: str) -> str:
    """Legacy function - use authenticate_oauth_user('google', token) instead."""
    return _authenticate_google(token)
