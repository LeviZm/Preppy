"""
Simple serializers for SQLAlchemy models.

This file provides lightweight, dependency-free functions to convert model
instances into JSON-serializable dicts. A commented Marshmallow example is
included for later migration to a schema library if you prefer.
"""

from decimal import Decimal
from typing import Any, Dict, List

from .models import Recipe, Ingredient, RecipeIngredient, User, Household


def _decimal_to_str(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def ingredient_to_dict(ingredient: Ingredient) -> Dict[str, Any]:
    return {"id": ingredient.id, "name": ingredient.name}


def recipeingredient_to_dict(ri: RecipeIngredient) -> Dict[str, Any]:
    """
    :param ri:
    :return:
    """
    return {
        "id": ri.id,
        "ingredient": ingredient_to_dict(ri.ingredient) if ri.ingredient is not None else None,
        "quantity": _decimal_to_str(ri.quantity),
        "unit": ri.unit,
        "prep_note": ri.prep_note,
        "sort_order": ri.sort_order,
    }


def recipe_to_dict(recipe: Recipe, include_ingredients: bool = True) -> Dict[str, Any]:
    """
    :param recipe:
    :param include_ingredients:
    :return:
    """
    base = {
        "id": recipe.id,
        "name": recipe.name,
        "instructions": recipe.instructions,
        "owner_user_id": recipe.owner_user_id,
        "household_id": recipe.household_id,
        "created_at": recipe.created_at.isoformat() if recipe.created_at is not None else None,
        "updated_at": recipe.updated_at.isoformat() if recipe.updated_at is not None else None,
    }

    if include_ingredients:
        ris = sorted(getattr(recipe, "recipe_ingredients", []), key=lambda x: x.sort_order or 0)
        base["ingredients"] = [recipeingredient_to_dict(ri) for ri in ris]

    return base


def user_to_dict(user: User) -> Dict[str, Any]:
    """
    :param user:
    :return:
    """
    return {"id": user.id, "username": user.username, "email": user.email}


def household_to_dict(h: Household) -> Dict[str, Any]:
    """
    :param h:
    :return:
    """
    return {"id": h.id, "name": h.name}
