"""
Routes for recipe CRUD operations.
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..serializers import recipe_to_dict
from ..services import recipe_services as recipe_service, ai_services as ai_service
from ..services.exceptions import AppError, NotFoundError, ValidationError, ConflictError, ForbiddenError

recipes_bp = Blueprint("recipes", __name__, url_prefix="/api/recipes")

# Error Handler
@recipes_bp.errorhandler(Exception)
def handle_unexpected_error(_: Exception) -> Any:
    """Handle unexpected exceiptions and return a generic error message."""
    return jsonify({"error": "An unexpected error occurred."}), 500

# ----------------------------------------------------------------
# Route Handlers
# ----------------------------------------------------------------

# Getters
@recipes_bp.route("/<int:recipe_id>", methods=["GET"])
@jwt_required()
def handle_get_recipe(recipe_id: int) -> Any:
    """Get a recipe by ID."""
    recipe = recipe_service.get_recipe(recipe_id)

    if not recipe:
        return jsonify({"error": "not found"}), 404

    return jsonify(recipe_to_dict(recipe)), 200

@recipes_bp.route("/", methods=["GET"])
@jwt_required()
def handle_get_all_recipes() -> Any:
    """Get all recipes."""
    items = recipe_service.get_all_recipes()

    results = [recipe_to_dict(recipe, include_ingredients=False) for recipe in items]
    return jsonify({"recipes": results}), 200


@recipes_bp.route("/user", methods=["GET"])
@jwt_required()
def handle_get_recipes_by_user() -> Any:
    """Get all recipes for the current user."""
    user_id = int(get_jwt_identity())
    items = recipe_service.get_recipes_by_user(user_id)

    results = [recipe_to_dict(recipe, include_ingredients=False) for recipe in items]
    return jsonify({"recipes": results}), 200

# POSTers
@recipes_bp.route("/", methods=["POST"])
@jwt_required()
def handle_create_recipe() -> Any:
    """Create a new recipe."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    new_recipe = recipe_service.create_recipe(
        owner_user_id=user_id,
        name=str(data.get("name") or ""),
        instructions=str(data.get("instructions") or ""),
        ingredients=data.get("ingredients", []),
    )

    return jsonify(recipe_to_dict(new_recipe)), 201

@recipes_bp.route("/<int:recipe_id>/ingredients", methods=["POST"])
@jwt_required()
def handle_add_ingredient_to_recipe(recipe_id: int) -> Any:
    """Add an ingredient to a recipe."""
    data = request.get_json(silent=True) or {}

    recipe_ingredient = recipe_service.add_ingredient_to_recipe(recipe_id, data)
    if not recipe_ingredient:
        return jsonify({"error": "Invalid input or recipe not found."}), 400

    return jsonify({"msg": "Ingredient added to recipe.",
                    "recipe_ingredient_id": recipe_ingredient.id}), 201

# PATCHers
@recipes_bp.route("/<int:recipe_id>", methods=["PATCH"])
@jwt_required()
def handle_update_recipe(recipe_id: int) -> Any:
    """Update a recipe's name, instructions, and/or ingredients."""
    data = request.get_json(silent=True) or {}

    updated_recipe = recipe_service.update_recipe(
        recipe_id=recipe_id,
        name=data.get("name"),
        instructions=data.get("instructions"),
        ingredients=data.get("ingredients"),
    )

    if not updated_recipe:
        return jsonify({"error": "Recipe not found."}), 404

    return jsonify({"msg": "Recipe updated.", "recipe": recipe_to_dict(updated_recipe)}), 200

# DELETErs
@recipes_bp.route("/<int:recipe_id>/ingredients/<int:ingredient_id>", methods=["DELETE"])
@jwt_required()
def handle_remove_ingredient_from_recipe(recipe_id: int, ingredient_id: int) -> Any:
    """Remove an ingredient from a recipe."""
    removed = recipe_service.remove_ingredient_from_recipe(recipe_id, ingredient_id)

    if not removed:
        return jsonify({"error": "Recipe or ingredient not found."}), 404

    return jsonify({"msg": "Ingredient removed from recipe."}), 200


@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
@jwt_required()
def handle_delete_recipe(recipe_id: int) -> Any:
    """Delete a recipe by ID."""
    deleted = recipe_service.delete_recipe(recipe_id)

    if not deleted:
        return jsonify({"error": "Recipe not found."}), 404

    return jsonify({"msg": "Recipe deleted."}), 200


# ----------------------------------------------------------------
# AI Endpoints
# ----------------------------------------------------------------

@recipes_bp.route("/generate", methods=["POST"])
@jwt_required()
def handle_generate_recipe():
    """Generate a recipe based on user input. Placeholder implementation."""
    user_id = get_jwt_identity()
    prompt = request.get_json(silent=True).get("prompt", "")

    # AI service generates a payload in the same shape as manual creation
    payload = ai_service.generate_recipe_payload(prompt)

    try:
        # Reuse the same creation logic to create a recipe from the AI-generated payload
        recipe = recipe_service.create_recipe(
            owner_user_id=user_id,
            name=payload.get("name", "AI Generated Recipe"),
            instructions=payload.get("instructions", ""),
            ingredients=payload.get("ingredients", []),
        )
        return jsonify(recipe_to_dict(recipe)), 201
    except (ValidationError, ConflictError) as e:
        return jsonify({"error": str(e)}), 400
