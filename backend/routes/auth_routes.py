"""
This module contains the authentication routes for the backend.
"""

import logging
from typing import Any

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity

from ..services import auth_services
from ..services.exceptions import ValidationError, ConflictError, AuthError
from ..serializers import user_to_dict

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

logger = logging.getLogger(__name__)


@auth_bp.route("/register", methods=["POST"])
def register() -> Any:
    """Register a new user account."""

    payload = request.get_json(silent=True) or {}
    
    try:
        user = auth_services.register_user(payload)
        logger.info("New user registered: id=%d", user.id)
        return jsonify(user_to_dict(user)), 201

    except ValidationError as e:
        logger.warning("Registration validation failed: %s", e.message)
        return jsonify({"error": str(e)}), 400

    except ConflictError as e:
        logger.warning("Registration conflict: %s", e.message)
        return jsonify({"error": str(e)}), 409


@auth_bp.route("/login", methods=["POST"])
def login() -> Any:
    """Authenticate a user and return access + refresh tokens."""

    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "")
    password = payload.get("password", "")

    try:
        access_token = auth_services.authenticate_user(email, password)
        refresh_token = create_refresh_token(identity=email)
        logger.info("Successful login for email: %r", email)
        return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 200

    except AuthError as e:
        logger.warning("Failed login attempt for email: %r", email)
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh() -> Any:
    """Exchange a refresh token for a new access token."""

    current_user = get_jwt_identity()
    access = create_access_token(identity=current_user)
    return jsonify({"access_token": access}), 200


@auth_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected() -> Any:
    """Example protected endpoint."""

    return jsonify({"msg": "authenticated"}), 200
