"""
This module contains the OAuth authentication routes for the backend.
"""

import logging

from flask import Blueprint, jsonify, Response, request
from flask_jwt_extended import create_refresh_token

from ..services import oauth_services as oauth_service
from ..services.exceptions import ValidationError, AuthError

oauth_bp = Blueprint("oauth", __name__, url_prefix="/api/oauth")

logger = logging.getLogger(__name__)


@oauth_bp.route("/login", methods=["POST"])
def oauth_login() -> tuple[Response, int]:
    """Authenticate a user via an OAuth provider and return access + refresh tokens."""

    payload = request.get_json(silent=True) or {}
    provider = payload.get("provider", "").strip().lower()
    token = payload.get("token", "").strip()

    if not provider or not token:
        return jsonify({"error": "provider and token are required."}), 400

    try:
        access_token = oauth_service.authenticate_oauth_user(provider, token)
        refresh_token = create_refresh_token(identity=provider)
        logger.info("Successful OAuth login via provider: %r", provider)
        return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 200

    except ValidationError as e:
        logger.warning("Unsupported OAuth provider: %r", provider)
        return jsonify({"error": str(e)}), 400

    except AuthError as e:
        logger.warning("OAuth authentication failed for provider %r: %s", provider, e)
        return jsonify({"error": str(e)}), 401
