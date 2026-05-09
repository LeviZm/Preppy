"""
Recipe service implementations
This module provides small helper functions used by route handlers.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, List, Dict, Optional, cast

from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import QueryableAttribute

from ..extensions import db
from ..models import Recipe, RecipeIngredient
from .exceptions import NotFoundError, ValidationError
from .ingredients_services import get_or_create_ingredient
from .transaction import atomic

logger = logging.getLogger(__name__)


def _qa(attr: Any) -> QueryableAttribute[Any]:
    """Cast relationship descriptors for SQLAlchemy loader options type checkers."""

    return cast(QueryableAttribute[Any], attr)

# ---------------------------------------------------------
# Private helpers
# ---------------------------------------------------------

def _validate_name(name: str) -> str:
    name = name.strip()

    if not name:
        raise ValueError("Recipe name is required")

    if len(name) > 128:
        raise ValueError("Recipe name must be less than 128 characters")

    return name

def _parse_quantity(qty: Any) -> Decimal:
    """Parse a quantity value into a Decimal, defaulting to 0 on error."""

    try:
        return Decimal(str(qty))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def _fetch_owned(recipe_id: int, user_id: int) -> Recipe:
    """
    Fetch a recipe by ID ensuring it belongs to the given user.
    Raises NotFoundError if the recipe doesn't exist or doesn't belong to the user.
    """

    recipe = Recipe.query.filter_by(id=recipe_id, owner_user_id=user_id).first()
    if not recipe:
        logger.warning("Recipe %d not found or not owned by user %d.", recipe_id, user_id)
        raise NotFoundError("Recipe not found.")
    return recipe

def _sync_recipe_ingredients(recipe: Recipe, ingredients: List[Dict]) -> None:
    """
    Sync the `RecipeIngredient` rows for `recipe` to match the incoming `ingredients` list.

    `ingredients` items have the shape:
      {"name": str, "quantity": Decimal|str|int, "unit": str, "prep_note": str (opt)}

    Behavior:
    - Create missing `Ingredient` rows.
    - Create or update `RecipeIngredient` rows for each incoming ingredient.
    - Remove `RecipeIngredient` rows that are not present in the incoming list.
    - Maintain `sort_order` according to the incoming list order.
    """

    # Load existing associations for the recipe
    existing_ris = RecipeIngredient.query.filter_by(recipe_id=recipe.id).all()
    existing_map = {ri.ingredient.name: ri for ri in existing_ris}

    incoming_names = []

    for idx, item in enumerate(ingredients):
        name = (item.get("name") or "").strip()
        if not name:
            continue
        incoming_names.append(name)

        # Ensure Ingredient exists
        ing = get_or_create_ingredient(name)

        # Prepare fields
        qty_dec = _parse_quantity(item.get("quantity", 0))
        unit = item.get("unit") or "unit"
        prep = item.get("prep_note")

        # Update existing association or create a new one
        ri = existing_map.get(name)
        if ri:
            ri.ingredient_id = ing.id
            ri.quantity = qty_dec
            ri.unit = unit
            ri.prep_note = prep
            ri.sort_order = idx
        else:
            ri = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing.id,
                quantity=qty_dec,
                unit=unit,
                prep_note=prep,
                sort_order=idx,
            )
            db.session.add(ri)

    # Delete associations that were removed in the new payload
    for ri in existing_ris:
        if ri.ingredient.name not in incoming_names:
            db.session.delete(ri)

def create_recipe(
    owner_user_id: int,
    name: str,
    instructions: str,
    ingredients: List[Dict]
) -> Recipe:
    """
    Create a recipe and its recipe-ingredient rows.

    Ingredients is a list of dicts:
    {"name": str, "quantity": Decimal|str, "unit": str, "prep_note": str (opt)}
    """

    resolved = [
        (item, get_or_create_ingredient(item["name"]))
        for item in ingredients
        if item.get("name")
    ]

    with atomic("A recipe with this name already exists."):
        recipe = Recipe(owner_user_id=owner_user_id, name=name, instructions=instructions)
        db.session.add(recipe)
        db.session.flush()  # ensure recipe.id is available

        for idx, (item, ing) in enumerate(resolved):
            ri = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing.id,
                quantity=_parse_quantity(item.get("quantity", 0)),
                unit=item.get("unit", "unit"),
                prep_note=item.get("prep_note"),
                sort_order=idx,
            )
            db.session.add(ri)
            
    logger.info(
        "Recipe %d '%s' created for user %d with %d ingredients.",
        recipe.id, recipe.name, recipe.owner_user_id, len(resolved)
    )

    return recipe

# ---------------------------------------------------------
# Get Recipes
# ---------------------------------------------------------

def get_recipe(recipe_id: int, user_id: int) -> Recipe:
    """
    Get a recipe by ID, or None if not found.
    """

    logger.debug("Fetching recipe %d for user %d.", recipe_id, user_id)

    recipe = (
        Recipe.query
        .filter_by(id=recipe_id, owner_user_id=user_id)
        .options(joinedload(_qa(Recipe.recipe_ingredients))
        .joinedload(_qa(RecipeIngredient.ingredient)))
        .first()
    )

    if not recipe:
        logger.warning("Recipe %d not found for user %d.", recipe_id, user_id)
        raise NotFoundError("Recipe not found.")

    return recipe

def list_recipes(user_id: int) -> List[Recipe]:
    """
    Get all recipes for a user, ordered by newest first.
    Eagerly loads ingredients to prevent N+1 query issues.
    """

    logger.debug("Listing recipes for user %d.", user_id)
    return (
        Recipe.query
        .options(
            joinedload(_qa(Recipe.recipe_ingredients))
            .joinedload(_qa(RecipeIngredient.ingredient))
        )
        .filter_by(owner_user_id=user_id)
        .order_by(Recipe.created_at.desc())
        .all()
    )

# -----------------------------------------------------------------
# Update Recipes
# -----------------------------------------------------------------

def update_recipe(
    user_id: int,
    recipe_id: int,
    name: Optional[str] = None,
    instructions: Optional[str] = None,
    ingredients: Optional[List[Dict]] = None,
) -> Recipe:
    """
    Update a recipe's basic fields and optionally its ingredient list.

    If `ingredients` is provided, the recipe's ingredient associations are synchronized
    to match the provided list (create/update/delete as needed).
    """

    recipe = _fetch_owned(recipe_id, user_id)

    with atomic("A recipe with this name already exists."):
        if name is not None:
            recipe.name = name
        if instructions is not None:
            recipe.instructions = instructions
        if ingredients is not None:
            _sync_recipe_ingredients(recipe, ingredients)

    logger.info("Recipe %d updated for user %d.", recipe_id, user_id)
    return recipe

def delete_recipe(recipe_id: int, user_id: int) -> None:
    """
    Delete a recipe and its associations.
    Raises NotFoundError if the recipe doesn't exist or doesn't belong to the user.
    """

    recipe = _fetch_owned(recipe_id, user_id)
    with atomic():
        db.session.delete(recipe)
    logger.info("Recipe %d deleted by user %d.", recipe_id, user_id)

def add_ingredient_to_recipe(
    recipe_id: int,
    ingredient_data: Dict,
    user_id: int
) -> RecipeIngredient:
    """
    Add a single ingredient to a recipe. Returns the created `RecipeIngredient`.
    Raises NotFoundError if the recipe doesn't exist or doesn't belong to the user.
    """

    recipe = _fetch_owned(recipe_id, user_id)

    name = (ingredient_data.get("name") or "").strip()
    if not name:
        raise ValidationError("Ingredient name is required.")

    ing = get_or_create_ingredient(name)

    with atomic("This ingredient already exists in the recipe."):
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ing.id,
            quantity=_parse_quantity(ingredient_data.get("quantity", 0)),
            unit=ingredient_data.get("unit") or "unit",
            prep_note=ingredient_data.get("prep_note"),
            sort_order=ingredient_data.get("sort_order", 0),
        )
        db.session.add(ri)

    logger.info("Ingredient '%s' added to recipe %d by user %d.", name, recipe_id, user_id)
    return ri


def remove_ingredient_from_recipe(recipe_id: int, ingredient_id: int, user_id: int) -> None:
    """
    Remove a specific ingredient association from a recipe by ingredient id.
    Raises NotFoundError if the recipe or ingredient association doesn't exist.
    """

    recipe = _fetch_owned(recipe_id, user_id)

    ri = RecipeIngredient.query.filter_by(recipe_id=recipe.id, ingredient_id=ingredient_id).first()
    if not ri:
        logger.warning("Ingredient %d not found in recipe %d for user %d.", ingredient_id, recipe_id, user_id)
        raise NotFoundError("Ingredient not found in recipe.")
    with atomic():
        db.session.delete(ri)
    logger.info("Ingredient %d removed from recipe %d by user %d.", ingredient_id, recipe_id, user_id)
