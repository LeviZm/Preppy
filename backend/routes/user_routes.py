"""
This module contains the user profile routes for the backend.
"""

import logging

from flask import Blueprint, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import user_service
from ..services.exceptions import NotFoundError
from ..serializers import user_to_dict

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

logger = logging.getLogger(__name__)


@users_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user() -> tuple[Response, int]:
    """Return the authenticated user's profile."""

    user_id = get_jwt_identity()

    try:
        user = user_service.get_user_by_id(user_id)
        return jsonify(user_to_dict(user)), 200

    except NotFoundError as e:
        logger.warning("User not found for id: %r", user_id)
        return jsonify({"error": str(e)}), 404
