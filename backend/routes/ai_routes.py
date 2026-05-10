"""
AI feature routes.

  POST /api/ai/meal-plan        — generate a 7-day meal plan from a prompt
  POST /api/ai/shopping-list    — generate a shopping list from recipes + pantry
  POST /api/ai/modify-recipe    — scale or adapt a recipe
  POST /api/ai/scan-pantry      — detect pantry items from an uploaded image

Note: recipe generation (POST /api/recipes/generate) lives on recipes_bp
in recipe_routes.py, co-located with the rest of the recipe CRUD.
"""

import logging
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..serializers import recipe_to_dict
from ..services import ai_services as ai_svc
from ..services import meals_services, pantry_services, recipe_services
from ..services.exceptions import (
    AIResponseParseError,
    AIResponseValidationError,
    AIServiceError,
    NotFoundError,
    ValidationError,
)

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

logger = logging.getLogger(__name__)


def _uid() -> int:
    return int(get_jwt_identity())


# -----------------------------------------------------------------------
# POST /api/ai/meal-plan
# Generate a full 7-day meal plan and persist it as MealPlan + Recipe rows.
# Body: { "prompt": str, "save": bool (default true) }
# -----------------------------------------------------------------------

@ai_bp.route("/meal-plan", methods=["POST"])
@jwt_required()
def generate_meal_plan() -> Any:
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt") or "").strip()
    save = data.get("save", True)

    try:
        plan_payload = ai_svc.generate_meal_plan_payload(prompt)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError:
        return jsonify({"error": "The AI service is temporarily unavailable. Please try again."}), 502
    except (AIResponseParseError, AIResponseValidationError):
        return jsonify({"error": "The AI returned an unexpected response. Please try again."}), 502

    if not save:
        return jsonify({"meal_plan": plan_payload}), 200

    user_id = _uid()
    saved_recipes = []
    errors = []

    for day in plan_payload.get("days", []):
        for meal in day.get("meals", []):
            recipe_payload = {
                "name": meal["name"],
                "instructions": meal.get("description", ""),
                "ingredients": meal.get("ingredients", []),
            }
            try:
                recipe = recipe_services.create_recipe(user_id, recipe_payload)
                saved_recipes.append(recipe_to_dict(recipe, include_ingredients=False))
            except Exception as exc:
                logger.warning("Failed to save meal plan recipe '%s': %s", meal.get("name"), exc)
                errors.append({"name": meal.get("name"), "error": str(exc)})

    return jsonify({
        "meal_plan": plan_payload,
        "saved_recipes": saved_recipes,
        "errors": errors,
    }), 201


# -----------------------------------------------------------------------
# POST /api/ai/shopping-list
# Generate an AI-powered shopping list from the user's planned recipes
# and their current pantry, then optionally persist it.
# Body: { "recipe_names": [str], "save": bool (default true),
#         "list_name": str (optional) }
# -----------------------------------------------------------------------

@ai_bp.route("/shopping-list", methods=["POST"])
@jwt_required()
def generate_shopping_list() -> Any:
    user_id = _uid()
    data = request.get_json(silent=True) or {}
    recipe_names = data.get("recipe_names") or []
    save = data.get("save", True)
    list_name = str(data.get("list_name") or "AI Shopping List").strip()

    if not isinstance(recipe_names, list) or not recipe_names:
        return jsonify({"error": "recipe_names must be a non-empty array of strings."}), 400

    pantry_rows = pantry_services.get_user_pantry(user_id)
    pantry_context = [
        {
            "name": row.ingredient.name if row.ingredient else "",
            "quantity": str(row.quantity),
            "unit": row.unit,
        }
        for row in pantry_rows
        if row.ingredient
    ]

    try:
        payload = ai_svc.generate_shopping_list_payload(recipe_names, pantry_context)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError:
        return jsonify({"error": "The AI service is temporarily unavailable. Please try again."}), 502
    except (AIResponseParseError, AIResponseValidationError):
        return jsonify({"error": "The AI returned an unexpected response. Please try again."}), 502

    if not save:
        return jsonify({"items": payload["items"]}), 200

    try:
        shopping_list = meals_services.create_shopping_list(user_id, {
            "name": list_name,
            "items": [
                {
                    "ingredient_name": item["name"],
                    "quantity": item.get("quantity") or "1",
                    "unit": item.get("unit") or "unit",
                }
                for item in payload["items"]
            ],
        })
    except (ValidationError, NotFoundError) as exc:
        return jsonify({"error": str(exc)}), 400

    from ..serializers import shoppinglist_to_dict
    return jsonify({"shopping_list": shoppinglist_to_dict(shopping_list)}), 201


# -----------------------------------------------------------------------
# POST /api/ai/modify-recipe/<recipe_id>
# Scale servings or apply dietary restrictions to an existing recipe.
# Saves the result as a new recipe (preserves the original).
# Body: { "servings": int (optional), "dietary_notes": str (optional),
#         "save": bool (default true) }
# -----------------------------------------------------------------------

@ai_bp.route("/modify-recipe/<int:recipe_id>", methods=["POST"])
@jwt_required()
def modify_recipe(recipe_id: int) -> Any:
    user_id = _uid()
    data = request.get_json(silent=True) or {}

    try:
        recipe = recipe_services.get_recipe(recipe_id, user_id)
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    servings = data.get("servings")
    if servings is not None:
        try:
            servings = int(servings)
            if servings < 1:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "servings must be a positive integer."}), 400

    dietary_notes = str(data.get("dietary_notes") or "").strip() or None
    save = data.get("save", True)

    recipe_dict = recipe_to_dict(recipe)

    try:
        modified = ai_svc.modify_recipe_payload(recipe_dict, servings=servings, dietary_notes=dietary_notes)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError:
        return jsonify({"error": "The AI service is temporarily unavailable. Please try again."}), 502
    except (AIResponseParseError, AIResponseValidationError):
        return jsonify({"error": "The AI returned an unexpected response. Please try again."}), 502

    if not save:
        return jsonify({"modified_recipe": modified}), 200

    try:
        new_recipe = recipe_services.create_recipe(user_id, modified)
    except Exception as exc:
        logger.warning("Failed to save modified recipe for user %d: %s", user_id, exc)
        return jsonify({
            "error": f"Recipe was generated but could not be saved: {exc}",
            "modified_recipe": modified,
        }), 422

    return jsonify({
        "recipe": recipe_to_dict(new_recipe),
        "changes": modified.get("changes", []),
    }), 201


# -----------------------------------------------------------------------
# POST /api/ai/scan-pantry
# Upload an image of a pantry/fridge and auto-populate pantry items.
# Expects multipart/form-data with field "image" (JPEG/PNG/WebP).
# Body param: "save" (default true) — if false, returns detections only.
# -----------------------------------------------------------------------

@ai_bp.route("/scan-pantry", methods=["POST"])
@jwt_required()
def scan_pantry() -> Any:
    user_id = _uid()

    if "image" not in request.files:
        return jsonify({"error": "An image file is required. Send it as multipart/form-data with field 'image'."}), 400

    image_file = request.files["image"]
    mime_type = image_file.content_type or "image/jpeg"
    image_bytes = image_file.read()

    save = request.form.get("save", "true").lower() != "false"

    try:
        payload = ai_svc.scan_pantry_from_image(image_bytes, mime_type)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError:
        return jsonify({"error": "The AI vision service is temporarily unavailable. Please try again."}), 502
    except (AIResponseParseError, AIResponseValidationError) as exc:
        return jsonify({"error": "The AI could not identify food items in this image."}), 502

    if not save:
        return jsonify({"detected_items": payload["items"]}), 200

    saved = []
    errors = []
    for item in payload["items"]:
        try:
            pantry_item, created = pantry_services.add_or_merge_to_pantry(user_id, {
                "ingredient_name": item["name"],
                "quantity": item.get("quantity") or "1",
                "unit": item.get("unit") or "unit",
            })
            saved.append({"name": item["name"], "created": created})
        except Exception as exc:
            logger.warning("Failed to save scanned pantry item '%s': %s", item.get("name"), exc)
            errors.append({"name": item.get("name"), "error": str(exc)})

    return jsonify({
        "detected_items": payload["items"],
        "saved": saved,
        "errors": errors,
    }), 201


# -----------------------------------------------------------------------
# POST /api/ai/scan-receipt
# Upload an image of a grocery receipt and auto-populate pantry items.
# Expects multipart/form-data with field "image" (JPEG/PNG/WebP).
# Body param: "save" (default true) — if false, returns detections only.
# -----------------------------------------------------------------------

@ai_bp.route("/scan-receipt", methods=["POST"])
@jwt_required()
def scan_receipt() -> Any:
    user_id = _uid()

    if "image" not in request.files:
        return jsonify({"error": "An image file is required. Send it as multipart/form-data with field 'image'."}), 400

    image_file = request.files["image"]
    mime_type = image_file.content_type or "image/jpeg"
    image_bytes = image_file.read()

    save = request.form.get("save", "true").lower() != "false"

    try:
        payload = ai_svc.scan_receipt_from_image(image_bytes, mime_type)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError:
        return jsonify({"error": "The AI vision service is temporarily unavailable. Please try again."}), 502
    except (AIResponseParseError, AIResponseValidationError):
        return jsonify({"error": "The AI could not read the receipt. Please try a clearer photo."}), 502

    if not save:
        return jsonify({"detected_items": payload["items"]}), 200

    saved = []
    errors = []
    for item in payload["items"]:
        try:
            pantry_item, created = pantry_services.add_or_merge_to_pantry(user_id, {
                "ingredient_name": item["name"],
                "quantity": item.get("quantity") or "1",
                "unit": item.get("unit") or "unit",
            })
            saved.append({"name": item["name"], "created": created})
        except Exception as exc:
            logger.warning("Failed to save receipt item '%s': %s", item.get("name"), exc)
            errors.append({"name": item.get("name"), "error": str(exc)})

    return jsonify({
        "detected_items": payload["items"],
        "saved": saved,
        "errors": errors,
    }), 201


# -----------------------------------------------------------------------
# POST /api/ai/suggest-from-pantry
# Read the user's live pantry and return ranked recipe suggestions.
# Body: { "count": int (1-5, default 3), "save": bool (default false) }
# -----------------------------------------------------------------------

@ai_bp.route("/suggest-from-pantry", methods=["POST"])
@jwt_required()
def suggest_from_pantry() -> Any:
    user_id = _uid()
    data = request.get_json(silent=True) or {}

    try:
        count = int(data.get("count", 3))
        if not (1 <= count <= 5):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "count must be an integer between 1 and 5."}), 400

    save = data.get("save", False)

    pantry_rows = pantry_services.get_user_pantry(user_id)
    if not pantry_rows:
        return jsonify({"error": "Your pantry is empty. Add some ingredients first."}), 400

    pantry_context = [
        {
            "name": row.ingredient.name if row.ingredient else "",
            "quantity": str(row.quantity),
            "unit": row.unit,
        }
        for row in pantry_rows
        if row.ingredient
    ]

    try:
        payload = ai_svc.suggest_recipes_from_pantry(pantry_context, count=count)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except AIServiceError:
        return jsonify({"error": "The AI service is temporarily unavailable. Please try again."}), 502
    except (AIResponseParseError, AIResponseValidationError):
        return jsonify({"error": "The AI returned an unexpected response. Please try again."}), 502

    if not save:
        return jsonify({"recipes": payload["recipes"]}), 200

    saved_recipes = []
    errors = []
    for suggestion in payload["recipes"]:
        recipe_payload = {
            "name": suggestion["name"],
            "instructions": suggestion["instructions"],
            "ingredients": suggestion.get("ingredients", []),
        }
        try:
            recipe = recipe_services.create_recipe(user_id, recipe_payload)
            saved_recipes.append({
                **recipe_to_dict(recipe, include_ingredients=False),
                "pantry_match": suggestion.get("pantry_match"),
                "missing": suggestion.get("missing", []),
            })
        except Exception as exc:
            logger.warning("Failed to save suggested recipe '%s': %s", suggestion.get("name"), exc)
            errors.append({"name": suggestion.get("name"), "error": str(exc)})

    return jsonify({
        "recipes": payload["recipes"],
        "saved_recipes": saved_recipes,
        "errors": errors,
    }), 201
