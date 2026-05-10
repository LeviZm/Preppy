"""
Integration tests for AI recipe generation.

Tests the full generate_and_save_recipe flow with mocked AI client
following Module 3.7 testing strategy.
"""

import pytest
from backend.services import recipe_services, ai_services
from backend.services.exceptions import (
    ValidationError,
    ConflictError,
    AIServiceError,
    AIResponseParseError,
    AIResponseValidationError,
)


class TestGenerateAndSaveRecipe:

    # --- Prompt validation ---

    def test_rejects_empty_prompt(self, app_context):
        with pytest.raises(ValidationError, match="empty"):
            recipe_services.generate_and_save_recipe(user_id=1, prompt="")

    def test_rejects_whitespace_prompt(self, app_context):
        with pytest.raises(ValidationError, match="empty"):
            recipe_services.generate_and_save_recipe(user_id=1, prompt="   ")

    def test_rejects_tab_only_prompt(self, app_context):
        with pytest.raises(ValidationError, match="empty"):
            recipe_services.generate_and_save_recipe(user_id=1, prompt="\t\n")

    def test_accepts_non_empty_prompt(self, app_context, valid_ai_payload, monkeypatch):
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        # Should not raise
        recipe_services.generate_and_save_recipe(user_id=1, prompt="valid prompt")

    # --- AI error propagation ---

    def test_propagates_ai_service_error(self, app_context, monkeypatch):
        def raise_ai_service_error(prompt):
            raise AIServiceError("Timed out.")
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            raise_ai_service_error,
        )
        with pytest.raises(AIServiceError):
            recipe_services.generate_and_save_recipe(user_id=1, prompt="pasta")

    def test_propagates_parse_error(self, app_context, monkeypatch):
        def raise_parse_error(prompt):
            raise AIResponseParseError("Bad JSON.")
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            raise_parse_error,
        )
        with pytest.raises(AIResponseParseError):
            recipe_services.generate_and_save_recipe(user_id=1, prompt="pasta")

    def test_propagates_validation_error(self, app_context, monkeypatch):
        def raise_validation_error(prompt):
            raise AIResponseValidationError("Schema validation failed.")
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            raise_validation_error,
        )
        with pytest.raises(AIResponseValidationError):
            recipe_services.generate_and_save_recipe(user_id=1, prompt="pasta")

    # --- Happy path ---

    def test_saves_recipe_from_valid_payload(
        self, app_context, user_a, valid_ai_payload, monkeypatch
    ):
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        recipe = recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="chicken parmesan"
        )
        assert recipe.id is not None
        assert recipe.name == valid_ai_payload["name"]
        assert recipe.owner_user_id == user_a.id
        assert recipe.instructions == valid_ai_payload["instructions"]

    def test_saved_recipe_has_correct_ingredient_count(
        self, app_context, user_a, valid_ai_payload, monkeypatch
    ):
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        recipe = recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="chicken parmesan"
        )
        assert len(recipe.recipe_ingredients) == len(valid_ai_payload["ingredients"])

    def test_saved_recipe_has_correct_ingredient_details(
        self, app_context, user_a, valid_ai_payload, monkeypatch
    ):
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        recipe = recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="chicken parmesan"
        )
        
        # Check first ingredient details
        first_ingredient = recipe.recipe_ingredients[0]
        expected = valid_ai_payload["ingredients"][0]
        assert first_ingredient.ingredient.name == expected["name"]
        assert first_ingredient.quantity == float(expected["quantity"])
        assert first_ingredient.unit == expected["unit"]
        assert first_ingredient.prep_note == expected["prep_note"]

    def test_raises_conflict_if_name_already_exists(
        self, app_context, user_a, valid_ai_payload, recipe_owned_by_a, monkeypatch
    ):
        # recipe_owned_by_a has the same name as valid_ai_payload
        valid_ai_payload["name"] = recipe_owned_by_a.name
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        with pytest.raises(ConflictError):
            recipe_services.generate_and_save_recipe(
                user_id=user_a.id, prompt="any prompt"
            )

    def test_second_user_can_save_same_name(
        self, app_context, user_a, user_b, valid_ai_payload, monkeypatch
    ):
        # User 1 already has a recipe with this name
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="chicken parmesan"
        )
        # User 2 generating the same name should succeed
        recipe = recipe_services.generate_and_save_recipe(
            user_id=user_b.id, prompt="chicken parmesan"
        )
        assert recipe.owner_user_id == user_b.id

    def test_creates_new_ingredients_when_needed(
        self, app_context, user_a, valid_ai_payload, monkeypatch
    ):
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="new recipe"
        )
        
        # Check that ingredients were created in the database
        from backend.models.recipe_models import Ingredient
        
        created_ingredients = Ingredient.query.all()
        ingredient_names = [ing.name for ing in created_ingredients]
        
        expected_names = [ing["name"] for ing in valid_ai_payload["ingredients"]]
        for name in expected_names:
            assert name in ingredient_names

    def test_reuses_existing_ingredients(
        self, app_context, user_a, valid_ai_payload, monkeypatch
    ):
        # Create an ingredient first
        from backend.extensions import db
        from backend.models.recipe_models import Ingredient
        
        existing_ingredient = Ingredient(name="chicken breast")
        db.session.add(existing_ingredient)
        db.session.commit()
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="recipe with existing ingredient"
        )
        
        # Should reuse the existing ingredient, not create a duplicate
        ingredients = Ingredient.query.filter_by(name="chicken breast").all()
        assert len(ingredients) == 1
        assert ingredients[0].id == existing_ingredient.id

    def test_handles_ingredients_without_optional_fields(
        self, app_context, user_a, valid_ai_payload, monkeypatch
    ):
        # Remove optional fields from ingredients
        for ingredient in valid_ai_payload["ingredients"]:
            ingredient.pop("quantity", None)
            ingredient.pop("prep_note", None)
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        recipe = recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="minimal ingredients"
        )
        
        # Should save successfully with default values for optional fields
        assert len(recipe.recipe_ingredients) == len(valid_ai_payload["ingredients"])
        for recipe_ingredient in recipe.recipe_ingredients:
            assert recipe_ingredient.quantity == 1.0  # Default value when not provided
            assert recipe_ingredient.prep_note is None

    def test_prompt_is_passed_to_ai_service(
        self, app_context, user_a, valid_ai_payload, monkeypatch
    ):
        captured_prompts = []
        
        def capture_prompt(prompt):
            captured_prompts.append(prompt)
            return valid_ai_payload
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            capture_prompt,
        )
        
        test_prompt = "spicy thai curry"
        recipe_services.generate_and_save_recipe(user_id=user_a.id, prompt=test_prompt)
        
        assert len(captured_prompts) == 1
        assert captured_prompts[0] == test_prompt

    def test_user_id_is_passed_correctly_to_create_recipe(
        self, app_context, user_a, user_b, valid_ai_payload, monkeypatch
    ):
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        
        # Create recipe for user_a
        recipe_a = recipe_services.generate_and_save_recipe(
            user_id=user_a.id, prompt="recipe for user a"
        )
        
        # Create recipe for user_b  
        recipe_b = recipe_services.generate_and_save_recipe(
            user_id=user_b.id, prompt="recipe for user b"
        )
        
        assert recipe_a.owner_user_id == user_a.id
        assert recipe_b.owner_user_id == user_b.id
        assert recipe_a.id != recipe_b.id
