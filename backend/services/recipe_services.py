"""
Recipe service implementations
This module provides small helper functions used by route handlers.
"""

from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional

from ..extensions import db
from ..models import Recipe, Ingredient, RecipeIngredient

# Create Recipe
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

    recipe = Recipe(owner_user_id=owner_user_id, name=name, instructions=instructions)
    db.session.add(recipe)
    db.session.flush()  # ensure recipe.id is available

    for idx, item in enumerate(ingredients):
        iname = item.get("name")
        if not iname:
            continue
        ing = Ingredient.query.filter_by(name=iname).first()
        if not ing:
            ing = Ingredient(name=iname)
            db.session.add(ing)
            db.session.flush()

        qty = item.get("quantity", 0)
        unit = item.get("unit", "unit")
        prep = item.get("prep_note")

        try:
            qty_dec = Decimal(str(qty))
        except (InvalidOperation, ValueError):
            qty_dec = Decimal(0)

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ing.id,
            quantity=qty_dec,
            unit=unit,
            prep_note=prep,
            sort_order=idx,
        )
        db.session.add(ri)

    db.session.commit()
    return recipe

# ---------------------------------------------------------
# Get Recipes
# ---------------------------------------------------------

def get_recipe(recipe_id: int, user_id: int) -> Recipe:
    """
    Get a recipe by ID, or None if not found.
    """

    recipe = (
        Recipe.query
        .filter_by(id=recipe_id, owner_user_id=user_id)
        .options(db.joinedload(Recipe.ingredients)
        .joinedload(RecipeIngredient.ingredient))
        .first()
    )

    if not recipe:
        raise NotFoundError("Recipe not found.")

    return recipe


def get_all_recipes(user_id: int) -> List[Recipe]:
    """
    Get all recipes, ordered by creation date descending.
    """

    recipes = (
        Recipe.query
        .filter_by(owner_user_id=user_id)
        .order_by(Recipe.created_at.desc())
        .all()
    )

    if not recipes:
        raise NotFoundError("No recipes found.")

    return recipes

def get_recipes_by_user(owner_user_id: int) -> List[Recipe]:
    """Return recipes owned by a given user, newest first."""

    return (
        Recipe.query.filter_by(owner_user_id=owner_user_id)
        .order_by(Recipe.created_at.desc())
        .all()
    )

# -----------------------------------------------------------------
# Update Recipes
# -----------------------------------------------------------------

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
        ing = Ingredient.query.filter_by(name=name).first()
        if not ing:
            ing = Ingredient(name=name)
            db.session.add(ing)
            db.session.flush()

        # Prepare fields
        qty = item.get("quantity", 0)
        try:
            qty_dec = Decimal(str(qty))
        except (InvalidOperation, ValueError):
            qty_dec = Decimal(0)
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


def update_recipe(
    user_id: int,
    recipe_id: int,
    name: Optional[str] = None,
    instructions: Optional[str] = None,
    ingredients: Optional[List[Dict]] = None,
) -> Optional[Recipe]:
    """
    Update a recipe's basic fields and optionally its ingredient list.

    If `ingredients` is provided, the recipe's ingredient associations are synchronized
    to match the provided list (create/update/delete as needed).
    """

    recipe = Recipe.query.filter_by(id=recipe_id, owner_user_id=user_id).first()
    
    if not recipe:
        return None

    if name is not None:
        recipe.name = name
    if instructions is not None:
        recipe.instructions = instructions

    if ingredients is not None:
        _sync_recipe_ingredients(recipe, ingredients)

    db.session.commit()
    return recipe

def delete_recipe(recipe_id: int, user_id: int) -> bool:
    """
    Delete a recipe and its associations. Returns True if deleted, False if not found.
    """

    recipe = Recipe.query.filter_by(id=recipe_id, owner_user_id=user_id).first()
    if not recipe:
        return False
    db.session.delete(recipe)
    db.session.commit()
    return True


def add_ingredient_to_recipe(
    recipe_id: int,
    ingredient_data: Dict,
    user_id: int
    ) -> Optional[RecipeIngredient]:
    """
    Add a single ingredient to a recipe. Returns the created `RecipeIngredient`.
    """

    recipe = Recipe.query.filter_by(id=recipe_id, owner_user_id=user_id).first()
    if not recipe:
        return None

    name = (ingredient_data.get("name") or "").strip()
    if not name:
        return None

    ing = Ingredient.query.filter_by(name=name).first()
    if not ing:
        ing = Ingredient(name=name)
        db.session.add(ing)
        db.session.flush()

    qty = ingredient_data.get("quantity", 0)
    try:
        qty_dec = Decimal(str(qty))
    except (InvalidOperation, ValueError):
        qty_dec = Decimal(0)

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ing.id,
        quantity=qty_dec,
        unit=ingredient_data.get("unit") or "unit",
        prep_note=ingredient_data.get("prep_note"),
        sort_order=ingredient_data.get("sort_order", 0),
    )
    db.session.add(ri)
    db.session.commit()
    return ri


def remove_ingredient_from_recipe(recipe_id: int, ingredient_id: int, user_id: int) -> bool:
    """
    Remove a specific ingredient association from a recipe by ingredient id.
    Returns True if removed, False otherwise.
    """

    recipe = Recipe.query.filter_by(id=recipe_id, owner_user_id=user_id).first()
    if not recipe:
        return False

    ri = RecipeIngredient.query.filter_by(recipe_id=recipe.id, ingredient_id=ingredient_id).first()
    if not ri:
        return False
    db.session.delete(ri)
    db.session.commit()
    return True
