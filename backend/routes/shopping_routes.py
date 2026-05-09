"""
Pantry routes.
"""

import logging
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..serializers import pantryitem_to_dict
from ..services import pantry_services as shopping_service
from ..services.exceptions import ValidationError, NotFoundError

shopping_bp = Blueprint("shopping", __name__, url_prefix="/api/shopping")

logger = logging.getLogger(__name__)


def _current_user_id() -> int:
    return int(get_jwt_identity())


@shopping_bp.route("/", methods=["GET"], strict_slashes=False)
@shopping_bp.route("/pantry", methods=["GET"])
@jwt_required()
def get_pantry() -> Any:
    user_id = _current_user_id()
    pantry_items = shopping_service.get_user_pantry(user_id)
    return jsonify({"items": [pantryitem_to_dict(item) for item in pantry_items]}), 200


@shopping_bp.route("/", methods=["POST"], strict_slashes=False)
@shopping_bp.route("/pantry", methods=["POST"])
@jwt_required()
def add_or_merge_to_pantry() -> Any:
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}

    try:
        pantry_item, created = shopping_service.add_or_merge_to_pantry(user_id, payload)
    except ValidationError as exc:
        logger.warning("POST pantry add failed for user %d: %s", user_id, exc)
        return jsonify({"error": str(exc)}), 400
    except NotFoundError as exc:
        logger.warning("POST pantry add ingredient not found for user %d: %s", user_id, exc)
        return jsonify({"error": str(exc)}), 404

    status_code = 201 if created else 200
    return jsonify({"item": pantryitem_to_dict(pantry_item), "created": created}), status_code


@shopping_bp.route("/pantry/<int:pantry_item_id>", methods=["PATCH"])
@jwt_required()
def update_pantry_quantity(pantry_item_id: int) -> Any:
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}

    try:
        pantry_item = shopping_service.update_pantry_quantity(
            user_id=user_id,
            pantry_item_id=pantry_item_id,
            quantity_value=payload.get("quantity"),
            unit=payload.get("unit"),
        )
    except ValidationError as exc:
        logger.warning("PATCH pantry item %d invalid for user %d: %s", pantry_item_id, user_id, exc)
        return jsonify({"error": str(exc)}), 400

    if pantry_item is None:
        logger.warning("PATCH pantry item %d not found for user %d.", pantry_item_id, user_id)
        return jsonify({"error": "Pantry item not found."}), 404

    return jsonify({"item": pantryitem_to_dict(pantry_item)}), 200


@shopping_bp.route("/pantry/<int:pantry_item_id>", methods=["DELETE"])
@jwt_required()
def remove_from_pantry(pantry_item_id: int) -> Any:
    user_id = _current_user_id()
    removed = shopping_service.remove_from_pantry(user_id, pantry_item_id)

    if not removed:
        logger.warning("DELETE pantry item %d not found for user %d.", pantry_item_id, user_id)
        return jsonify({"error": "Pantry item not found."}), 404

    return jsonify({"msg": "Pantry item removed."}), 200