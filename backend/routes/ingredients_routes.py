"""
Ingredient catalog routes.
"""

import logging
from typing import Any

from flask import Blueprint, jsonify, request

from ..serializers import ingredient_to_dict
from ..services import ingredients_services as ingredient_service
from ..services.exceptions import ValidationError

ingredients_bp = Blueprint("ingredients", __name__, url_prefix="/api/ingredients")

logger = logging.getLogger(__name__)


@ingredients_bp.route("/", methods=["GET"], strict_slashes=False)
def list_ingredients() -> Any:
    """Route to list all ingredients"""

    ingredients = ingredient_service.list_ingredients()
    return jsonify({"ingredients": [ingredient_to_dict(ingredient) for ingredient in ingredients]}),200


@ingredients_bp.route("/<int:ingredient_id>", methods=["GET"])
def get_ingredient(ingredient_id: int) -> Any:
    """Route to get a single ingredient by ID"""

    ingredient = ingredient_service.get_ingredient_by_id(ingredient_id)
    if ingredient is None:
        logger.warning("GET ingredient %d not found.", ingredient_id)
        return jsonify({"error": "Ingredient not found."}), 404

    return jsonify({"ingredient": ingredient_to_dict(ingredient)}), 200


@ingredients_bp.route("/", methods=["POST"], strict_slashes=False)
def create_ingredient() -> Any:
    """Route to create a new ingredient."""

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Ingredient name is required."}), 400

    try:
        ingredient, created = ingredient_service.create_ingredient(name)
    except ValidationError as exc:
        logger.warning("POST create ingredient failed: %s", exc)
        return jsonify({"error": str(exc)}), 400

    status_code = 201 if created else 200
    if created:
        logger.info("Ingredient '%s' created (id=%d).", ingredient.name, ingredient.id)
    return jsonify({"ingredient": ingredient_to_dict(ingredient), "created": created}), status_code
