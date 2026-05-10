"""
Routes for recipe CRUD operations.
"""

import logging

from flask import Blueprint, jsonify, Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import limiter
from ..serializers import recipe_to_dict
from ..services import (
    recipe_services as recipe_service
)

from ..services.exceptions import (
    NotFoundError, 
    ValidationError, 
    ConflictError,
    AIServiceError,
    AIResponseParseError,
    AIResponseValidationError,
)

recipes_bp = Blueprint("recipes", __name__, url_prefix="/api/recipes")

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Route Handlers
# ----------------------------------------------------------------

# Getters
@recipes_bp.route("/<int:recipe_id>", methods=["GET"])
@jwt_required()
def handle_get_recipe(recipe_id: int) -> tuple[Response, int]:
    """Get a recipe by ID."""

    user_id = int(get_jwt_identity())

    try:
        recipe = recipe_service.get_recipe(recipe_id, user_id)
    except NotFoundError:
        logger.warning("GET recipe %d failed: not found for user %d.", recipe_id, user_id)
        return jsonify({"error": "Recipe not found."}), 404

    return jsonify(recipe_to_dict(recipe)), 200

@recipes_bp.route("/", methods=["GET"])
@jwt_required()
def handle_list_recipes() -> tuple[Response, int]:
    """Get (and list) all recipes for the current user."""

    user_id = int(get_jwt_identity())
    items = recipe_service.list_recipes(user_id)

    results = [recipe_to_dict(recipe, include_ingredients=False) for recipe in items]
    return jsonify({"recipes": results}), 200

# POSTers
@recipes_bp.route("/", methods=["POST"])
@jwt_required()
def handle_create_recipe() -> tuple[Response, int]:
    """Create a new recipe."""

    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    try:
        new_recipe = recipe_service.create_recipe(
            user_id=user_id,
            payload={
                "name": str(data.get("name") or ""),
                "instructions": str(data.get("instructions") or ""),
                "ingredients": data.get("ingredients", [])
            }
        )
    except (ValidationError, ConflictError) as e:
        logger.warning("POST create recipe failed for user %d: %s", user_id, e)
        return jsonify({"error": str(e)}), 400

    return jsonify(recipe_to_dict(new_recipe)), 201

@recipes_bp.route("/<int:recipe_id>/ingredients", methods=["POST"])
@jwt_required()
def handle_add_ingredient_to_recipe(recipe_id: int) -> tuple[Response, int]:
    """Add an ingredient to a recipe."""

    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    try:
        recipe_ingredient = recipe_service.add_ingredient_to_recipe(recipe_id, data, user_id)
    except NotFoundError as e:
        logger.warning("POST add ingredient to recipe %d failed for user %d: %s", recipe_id, user_id, e)
        return jsonify({"error": str(e)}), 404
    except (ValidationError, ConflictError) as e:
        logger.warning("POST add ingredient to recipe %d invalid for user %d: %s", recipe_id, user_id, e)
        return jsonify({"error": str(e)}), 400

    return jsonify({"msg": "Ingredient added to recipe.",
                    "recipe_ingredient_id": recipe_ingredient.id}), 201

# PATCHers
@recipes_bp.route("/<int:recipe_id>", methods=["PATCH"])
@jwt_required()
def handle_update_recipe(recipe_id: int) -> tuple[Response, int]:
    """Update a recipe's name, instructions, and/or ingredients."""

    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    try:
        updated_recipe = recipe_service.update_recipe(
            user_id=user_id,
            recipe_id=recipe_id,
            name=data.get("name"),
            instructions=data.get("instructions"),
            ingredients=data.get("ingredients"),
        )
    except NotFoundError as e:
        logger.warning("PATCH recipe %d failed for user %d: %s", recipe_id, user_id, e)
        return jsonify({"error": str(e)}), 404
    except ConflictError as e:
        logger.warning("PATCH recipe %d conflict for user %d: %s", recipe_id, user_id, e)
        return jsonify({"error": str(e)}), 409

    return jsonify({"msg": "Recipe updated.", "recipe": recipe_to_dict(updated_recipe)}), 200

# DELETErs
@recipes_bp.route("/<int:recipe_id>/ingredients/<int:ingredient_id>", methods=["DELETE"])
@jwt_required()
def handle_remove_ingredient_from_recipe(recipe_id: int, ingredient_id: int) -> tuple[Response, int]:
    """Remove an ingredient from a recipe."""

    user_id = int(get_jwt_identity())
    try:
        recipe_service.remove_ingredient_from_recipe(recipe_id, ingredient_id, user_id)
    except NotFoundError as e:
        logger.warning("DELETE ingredient %d from recipe %d failed for user %d: %s", ingredient_id, recipe_id, user_id, e)
        return jsonify({"error": str(e)}), 404

    return jsonify({"msg": "Ingredient removed from recipe."}), 200


@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
@jwt_required()
def handle_delete_recipe(recipe_id: int) -> tuple[Response, int]:
    """Delete a recipe by ID."""

    user_id = int(get_jwt_identity())
    try:
        recipe_service.delete_recipe(recipe_id, user_id)
    except NotFoundError as e:
        logger.warning("DELETE recipe %d failed for user %d: %s", recipe_id, user_id, e)
        return jsonify({"error": str(e)}), 404

    return jsonify({"msg": "Recipe deleted."}), 200


# ----------------------------------------------------------------
# AI Endpoints
# ----------------------------------------------------------------

@recipes_bp.route("/generate", methods=["POST"])
@jwt_required()
@limiter.limit("20 per day", key_func=lambda: str(get_jwt_identity()))
def handle_generate_recipe() -> tuple[Response, int]:
    """Generate a recipe based on user input using the AI pipeline."""

    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    
    logger.info("POST /api/recipes/generate request from user %d", user_id, extra={"user_id": user_id})

    try:
        recipe = recipe_service.generate_and_save_recipe(
            user_id=user_id, prompt=prompt
        )
        return jsonify(recipe_to_dict(recipe)), 201

    except ValidationError as e:
        # User error - return their own message back to them
        return jsonify({"error": str(e)}), 400

    except ConflictError as e:
        # User error - tell them the name is taken
        return jsonify({"error": str(e)}), 409

    except AIServiceError:
        # Upstream error - generic message, do not expose API details
        return jsonify({
            "error": "The recipe generator is temporarily unavailable. Please try again."
        }), 502

    except (AIResponseParseError, AIResponseValidationError):
        # Application error - already logged in service, generic message
        return jsonify({
            "error": "The recipe generator returned an unexpected response. Please try again."
        }), 502

    except Exception:
        # Uncaught application error - log here as last resort
        logger.error(
            "Unhandled exception in generate_recipe route.",
            extra={"user_id": user_id},
            exc_info=True,
        )
        return jsonify({
            "error": "An unexpected error occurred. Please try again."
        }), 500
