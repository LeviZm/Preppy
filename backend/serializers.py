"""
Simple serializers for SQLAlchemy models.

This file provides lightweight, dependency-free functions to convert model
instances into JSON-serializable dicts. A commented Marshmallow example is
included for later migration to a schema library if you prefer.
"""

from decimal import Decimal
from typing import Any, Dict, List

from .models import Recipe, Ingredient, RecipeIngredient, User, Household, PantryItem, MealPlan, ShoppingList


def _decimal_to_str(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def ingredient_to_dict(ingredient: Ingredient) -> Dict[str, Any]:
    """
    Convert an Ingredient instance to a dictionary.

    Args:
        ingredient (Ingredient): The Ingredient instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the Ingredient.
    """
    return {"id": ingredient.id, "name": ingredient.name}


def recipeingredient_to_dict(ri: RecipeIngredient) -> Dict[str, Any]:
    """
    Convert a RecipeIngredient instance to a dictionary.

    Args:
        ri (RecipeIngredient): The RecipeIngredient instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the RecipeIngredient.
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
    Convert a Recipe instance to a dictionary.

    Args:
        recipe (Recipe): The Recipe instance to convert.
        include_ingredients (bool, optional): Whether to include associated ingredients. Defaults to True.

    Returns:
        Dict[str, Any]: A dictionary representing the Recipe.
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
    Convert a User instance to a dictionary.

    Args:
        user (User): The User instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the User.
    """
    
    return {"id": user.id, "username": user.username, "email": user.email}


def household_to_dict(h: Household) -> Dict[str, Any]:
    """
    Convert a Household instance to a dictionary.

    Args:
        h (Household): The Household instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the Household.
    """
    return {"id": h.id, "name": h.name}


def pantryitem_to_dict(p: PantryItem) -> Dict[str, Any]:
    """
    Serialize a PantryItem for API responses.

    Args:
        p (PantryItem): The PantryItem instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the PantryItem.
    """
    return {
        "id": p.id,
        "user_id": p.user_id,
        "ingredient": ingredient_to_dict(p.ingredient) if p.ingredient is not None else None,
        "quantity": _decimal_to_str(p.quantity),
        "unit": p.unit,
        "updated_at": p.updated_at.isoformat() if getattr(p, "updated_at", None) is not None else None,
    }


def mealplan_to_dict(m: MealPlan) -> Dict[str, Any]:
    """
    Placeholder serializer for future MealPlan model.
    Args:
        m (MealPlan): The MealPlan instance to convert.
    """
    return {"id": getattr(m, "id", None)}


def shoppinglist_to_dict(s: ShoppingList) -> Dict[str, Any]:
    """
    Placeholder serializer for future ShoppingList model.
    Args:
        s (ShoppingList): The ShoppingList instance to convert.
    """

    return {"id": getattr(s, "id", None)}
