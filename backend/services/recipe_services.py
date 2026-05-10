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
from .exceptions import NotFoundError, ValidationError, ConflictError, AIServiceError, AIResponseParseError, AIResponseValidationError
from .ingredients_services import get_or_create_ingredient
from .transaction import atomic
from . import ai_services as ai_service
from . import household_service

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
    Fetch a recipe by ID that the user can access: either they own it,
    or it belongs to one of their households.
    Raises NotFoundError if not found or not accessible.
    """
    household_ids = household_service.get_user_household_ids(user_id)
    recipe = Recipe.query.filter(
        Recipe.id == recipe_id,
        db.or_(
            Recipe.owner_user_id == user_id,
            db.and_(Recipe.household_id.isnot(None), Recipe.household_id.in_(household_ids))
        )
    ).first()
    if not recipe:
        logger.warning("Recipe %d not found or not accessible by user %d.", recipe_id, user_id)
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


def create_recipe(user_id: int, payload: Dict[str, Any]) -> Recipe:
    """
    Create a new recipe from validated payload.

    Args:
        user_id: ID of the user creating the recipe
        payload: Validated recipe data with name, instructions, ingredients

    Returns:
        Created Recipe object

    Raises:
        ValidationError: if payload is invalid
        ConflictError: if user already has a recipe with this name
    """
    name = payload.get("name", "").strip()
    logger.debug("Creating recipe '%s' for user %d", name, user_id, extra={"user_id": user_id})
    
    if not name:
        raise ValidationError("Recipe name is required.")
    
    # Check for existing recipe with same name for this user
    existing = Recipe.query.filter_by(owner_user_id=user_id, name=name).first()
    if existing:
        raise ConflictError("You already have a recipe with this name.")
    
    # Create recipe
    recipe = Recipe(
        name=name,
        instructions=payload.get("instructions", "").strip(),
        owner_user_id=user_id
    )
    db.session.add(recipe)
    db.session.flush()  # Get the recipe ID
    
    # Create recipe ingredients
    for sort_order, ingredient_data in enumerate(payload.get("ingredients", [])):
        ingredient = get_or_create_ingredient(ingredient_data["name"])
        
        # Handle optional fields with defaults
        quantity = ingredient_data.get("quantity")
        if quantity is not None:
            try:
                quantity = float(quantity)
            except (ValueError, TypeError):
                quantity = 1.0
        else:
            quantity = 1.0
            
        unit = ingredient_data.get("unit", "").strip() or "unit"
        prep_note = ingredient_data.get("prep_note")
        
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=float(quantity),
            unit=unit,
            prep_note=prep_note.strip() if prep_note else None,
            sort_order=sort_order
        )
        db.session.add(recipe_ingredient)

    db.session.commit()
    logger.info("Recipe created and saved.", extra={"user_id": user_id, "recipe_id": recipe.id})
    return recipe


def generate_and_save_recipe(user_id: int, prompt: str) -> Recipe:
    """
    Generate a recipe from a user prompt and save it to the database.

    Validates the prompt, calls the AI service, and delegates persistence
    to create_recipe() — the same function used by the manual creation flow.

    Raises:
        ValidationError: if the prompt is empty.
        AIServiceError: if the AI API fails or times out.
        AIResponseParseError: if the AI response is not valid JSON.
        AIResponseValidationError: if the AI response fails schema validation.
        ConflictError: if the user already has a recipe with the generated name.
    """
    # --- Step 2: Validate the prompt ---
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        logger.debug("AI recipe generation failed: empty prompt for user %d", user_id, extra={"user_id": user_id})
        raise ValidationError("Prompt must not be empty.")

    # --- Steps 3–5: Generate and validate the payload ---
    try:
        payload = ai_service.generate_recipe_payload(prompt)
    except AIServiceError as e:
        # Upstream error - already logged in ai_service
        raise
    except AIResponseParseError as e:
        logger.error(
            "AI response failed JSON parsing.",
            extra={"user_id": user_id},
            exc_info=True,
        )
        raise
    except AIResponseValidationError as e:
        logger.error(
            "AI response failed schema validation.",
            extra={"user_id": user_id, "validation_error": str(e)},
            exc_info=True,
        )
        raise

    # --- Steps 6–7: Save and return ---
    recipe = create_recipe(user_id=user_id, payload=payload)
    return recipe


# ---------------------------------------------------------
# Get Recipes
# ---------------------------------------------------------

def get_recipe(recipe_id: int, user_id: int) -> Recipe:
    """
    Get a recipe by ID that the user can access (owned or household-shared).
    """
    logger.debug("Fetching recipe %d for user %d.", recipe_id, user_id)
    household_ids = household_service.get_user_household_ids(user_id)
    recipe = (
        Recipe.query
        .filter(
            Recipe.id == recipe_id,
            db.or_(
                Recipe.owner_user_id == user_id,
                db.and_(Recipe.household_id.isnot(None), Recipe.household_id.in_(household_ids))
            )
        )
        .options(
            joinedload(_qa(Recipe.recipe_ingredients))
            .joinedload(_qa(RecipeIngredient.ingredient))
        )
        .first()
    )
    if not recipe:
        logger.warning("Recipe %d not found for user %d.", recipe_id, user_id)
        raise NotFoundError("Recipe not found.")
    return recipe

def list_recipes(user_id: int) -> List[Recipe]:
    """
    Get all recipes accessible to a user: owned by them, or shared via
    a household they belong to. Ordered newest first.
    """
    logger.debug("Listing recipes for user %d.", user_id)
    household_ids = household_service.get_user_household_ids(user_id)
    return (
        Recipe.query
        .options(
            joinedload(_qa(Recipe.recipe_ingredients))
            .joinedload(_qa(RecipeIngredient.ingredient))
        )
        .filter(
            db.or_(
                Recipe.owner_user_id == user_id,
                db.and_(Recipe.household_id.isnot(None), Recipe.household_id.in_(household_ids))
            )
        )
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
