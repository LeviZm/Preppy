"""
Recipe service for Preppy.

Handles recipe creation, management, and AI recipe generation.
Follows the pipeline architecture from Module 3.3.
"""

from typing import Dict, Any

from . import ai_services as ai_service
from .exceptions import (
    ValidationError,
    ConflictError,
    AIServiceError,
    AIResponseParseError,
    AIResponseValidationError,
)
from ..models.recipe_models import Recipe, Ingredient, RecipeIngredient
from ..extensions import db


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
    if not name:
        raise ValidationError("Recipe name is required.")
    
    if len(name) > 128:
        raise ValidationError("Recipe name must be 128 characters or less.")

    instructions = payload.get("instructions", "").strip()
    if not instructions:
        raise ValidationError("Recipe instructions are required.")

    ingredients_data = payload.get("ingredients", [])
    if not isinstance(ingredients_data, list):
        raise ValidationError("Ingredients must be a list.")

    # Check for duplicate recipe name
    existing = Recipe.query.filter_by(owner_user_id=user_id, name=name).first()
    if existing:
        raise ConflictError(f"You already have a recipe named '{name}'.")

    # Create recipe
    recipe = Recipe(
        name=name,
        instructions=instructions,
        owner_user_id=user_id
    )
    
    db.session.add(recipe)
    db.session.flush()  # Get the recipe ID

    # Add ingredients
    for sort_order, ingredient_data in enumerate(ingredients_data):
        ingredient_name = ingredient_data.get("name", "").strip()
        if not ingredient_name:
            raise ValidationError("All ingredients must have a name.")

        # Find or create ingredient
        ingredient = Ingredient.query.filter_by(name=ingredient_name).first()
        if not ingredient:
            ingredient = Ingredient(name=ingredient_name)
            db.session.add(ingredient)
            db.session.flush()

        # Create recipe ingredient association
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=float(ingredient_data.get("quantity", 1)),
            unit=ingredient_data.get("unit", "").strip() or "unit",
            prep_note=ingredient_data.get("prep_note", "").strip() or None,
            sort_order=sort_order
        )
        db.session.add(recipe_ingredient)

    db.session.commit()
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
    if not prompt or not prompt.strip():
        raise ValidationError("Prompt must not be empty.")

    # --- Steps 3–5: Generate and validate the payload ---
    payload = ai_service.generate_recipe_payload(prompt)

    # --- Steps 6–7: Save and return ---
    return create_recipe(user_id=user_id, payload=payload)
