"""
Simple serializers for SQLAlchemy models.

This file provides lightweight, dependency-free functions to convert model
instances into JSON-serializable dicts. A commented Marshmallow example is
included for later migration to a schema library if you prefer.
"""

from decimal import Decimal
from typing import Any, Dict, Iterable, cast

from .models import (
    Recipe,
    Ingredient,
    RecipeIngredient,
    User,
    Household,
    HouseholdMember,
    PantryItem,
    MealPlan,
    ShoppingList,
    ShoppingListItem,
)


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

    ingredient = getattr(ri, "ingredient", None)

    return {
        "id": ri.id,
        "ingredient": ingredient_to_dict(ingredient) if ingredient is not None else None,
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
        include_ingredients (bool, optional):
            Whether to include associated ingredients. Defaults to True.

    Returns:
        Dict[str, Any]: A dictionary representing the Recipe.
    """

    data = {
        "id": recipe.id,
        "name": recipe.name,
        "instructions": recipe.instructions,
        "owner_user_id": recipe.owner_user_id,
        "household_id": recipe.household_id,
        "created_at": recipe.created_at.isoformat() if recipe.created_at is not None else None,
        "updated_at": recipe.updated_at.isoformat() if recipe.updated_at is not None else None,
    }

    if include_ingredients:
        recipe_ingredients = cast(Iterable[RecipeIngredient], recipe.recipe_ingredients)
        data["ingredients"] = [
            {
                "id": ri.id,
                "name": ri.ingredient.name,
                "quantity": _decimal_to_str(ri.quantity),
                "unit": ri.unit,
                "prep_note": ri.prep_note,
                "sort_order": ri.sort_order,
            }
            for ri in recipe_ingredients
        ]

    return data


def user_to_dict(user: User) -> Dict[str, Any]:
    """
    Convert a User instance to a dictionary.

    Args:
        user (User): The User instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the User.
    """

    return {"id": user.id, "username": user.username, "email": user.email}


def household_member_to_dict(m: HouseholdMember) -> Dict[str, Any]:
    return {
        "id": m.id,
        "user": user_to_dict(m.user),
        "role": m.role,
        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
    }


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

    ingredient = getattr(p, "ingredient", None)

    return {
        "id": p.id,
        "user_id": p.user_id,
        "ingredient": ingredient_to_dict(ingredient) if ingredient is not None else None,
        "quantity": _decimal_to_str(p.quantity),
        "unit": p.unit,
        "updated_at": p.updated_at.isoformat() if getattr(p, "updated_at", None) is not None else None,
    }


def mealplan_to_dict(m: MealPlan) -> Dict[str, Any]:
    """
    Convert a MealPlan instance to a dictionary.

    Args:
        m (MealPlan): The MealPlan instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the MealPlan.
    """

    return {
        "id": m.id,
        "user_id": m.user_id,
        "recipe_id": m.recipe_id,
        "planned_date": m.planned_date.isoformat() if m.planned_date is not None else None,
        "meal_type": m.meal_type,
        "servings": m.servings,
        "notes": m.notes,
        "created_at": m.created_at.isoformat() if m.created_at is not None else None,
    }


def shoppinglistitem_to_dict(item: ShoppingListItem) -> Dict[str, Any]:
    """
    Convert a ShoppingListItem instance to a dictionary.

    Args:
        item (ShoppingListItem): The ShoppingListItem instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the ShoppingListItem.
    """

    ingredient = getattr(item, "ingredient", None)

    return {
        "id": item.id,
        "shopping_list_id": item.shopping_list_id,
        "ingredient_id": item.ingredient_id,
        "ingredient_name": ingredient.name if ingredient is not None else None,
        "quantity": _decimal_to_str(item.quantity),
        "unit": item.unit,
        "is_checked": item.is_checked,
        "sort_order": item.sort_order,
    }


def shoppinglist_to_dict(s: ShoppingList) -> Dict[str, Any]:
    """
    Convert a ShoppingList instance to a dictionary.

    Args:
        s (ShoppingList): The ShoppingList instance to convert.

    Returns:
        Dict[str, Any]: A dictionary representing the ShoppingList.
    """

    return {
        "id": s.id,
        "user_id": s.user_id,
        "meal_plan_id": s.meal_plan_id,
        "name": s.name,
        "is_complete": s.is_complete,
        "created_at": s.created_at.isoformat() if s.created_at is not None else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at is not None else None,
        "items": [shoppinglistitem_to_dict(i) for i in (s.items or [])],
    }
