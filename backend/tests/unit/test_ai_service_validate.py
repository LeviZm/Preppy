"""
Unit tests for AI service validation functions.

Tests the _validate_recipe_payload function following Module 3.7 testing strategy.
"""

import pytest
from backend.services.ai_services import _validate_recipe_payload
from backend.services.exceptions import AIResponseValidationError


class TestValidateRecipePayload:

    # --- Structural ---

    def test_accepts_valid_payload(self, valid_ai_payload):
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_rejects_non_dict(self):
        with pytest.raises(AIResponseValidationError, match="object"):
            _validate_recipe_payload(["not", "a", "dict"])

    def test_rejects_list(self):
        with pytest.raises(AIResponseValidationError, match="object"):
            _validate_recipe_payload([1, 2, 3])

    def test_rejects_string(self):
        with pytest.raises(AIResponseValidationError, match="object"):
            _validate_recipe_payload("not an object")

    def test_rejects_integer(self):
        with pytest.raises(AIResponseValidationError, match="object"):
            _validate_recipe_payload(42)

    def test_rejects_none(self):
        with pytest.raises(AIResponseValidationError, match="object"):
            _validate_recipe_payload(None)

    def test_rejects_model_error_object(self):
        with pytest.raises(AIResponseValidationError, match="could not generate"):
            _validate_recipe_payload({"error": "No recipe for that prompt."})

    def test_rejects_model_error_with_details(self):
        with pytest.raises(AIResponseValidationError, match="could not generate"):
            _validate_recipe_payload({"error": "Prompt too complex for recipe generation."})

    # --- name ---

    def test_rejects_missing_name(self, valid_ai_payload):
        del valid_ai_payload["name"]
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_null_name(self, valid_ai_payload):
        valid_ai_payload["name"] = None
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_integer_name(self, valid_ai_payload):
        valid_ai_payload["name"] = 42
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_float_name(self, valid_ai_payload):
        valid_ai_payload["name"] = 3.14
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_list_name(self, valid_ai_payload):
        valid_ai_payload["name"] = ["not", "a", "string"]
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_empty_name(self, valid_ai_payload):
        valid_ai_payload["name"] = ""
        with pytest.raises(AIResponseValidationError, match="non-empty"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_whitespace_name(self, valid_ai_payload):
        valid_ai_payload["name"] = "   "
        with pytest.raises(AIResponseValidationError, match="non-empty"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_tab_name(self, valid_ai_payload):
        valid_ai_payload["name"] = "\t\n"
        with pytest.raises(AIResponseValidationError, match="non-empty"):
            _validate_recipe_payload(valid_ai_payload)

    def test_accepts_single_character_name(self, valid_ai_payload):
        valid_ai_payload["name"] = "A"
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    # --- instructions ---

    def test_rejects_missing_instructions(self, valid_ai_payload):
        del valid_ai_payload["instructions"]
        with pytest.raises(AIResponseValidationError, match="'instructions'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_null_instructions(self, valid_ai_payload):
        valid_ai_payload["instructions"] = None
        with pytest.raises(AIResponseValidationError, match="'instructions'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_integer_instructions(self, valid_ai_payload):
        valid_ai_payload["instructions"] = 42
        with pytest.raises(AIResponseValidationError, match="'instructions'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_list_instructions(self, valid_ai_payload):
        valid_ai_payload["instructions"] = ["step 1", "step 2"]
        with pytest.raises(AIResponseValidationError, match="'instructions'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_empty_instructions(self, valid_ai_payload):
        valid_ai_payload["instructions"] = ""
        with pytest.raises(AIResponseValidationError, match="non-empty"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_whitespace_instructions(self, valid_ai_payload):
        valid_ai_payload["instructions"] = "   \n\t   "
        with pytest.raises(AIResponseValidationError, match="non-empty"):
            _validate_recipe_payload(valid_ai_payload)

    # --- ingredients ---

    def test_rejects_missing_ingredients(self, valid_ai_payload):
        del valid_ai_payload["ingredients"]
        with pytest.raises(AIResponseValidationError, match="'ingredients'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_null_ingredients(self, valid_ai_payload):
        valid_ai_payload["ingredients"] = None
        with pytest.raises(AIResponseValidationError, match="'ingredients'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_string_ingredients(self, valid_ai_payload):
        valid_ai_payload["ingredients"] = "chicken, pasta, oil"
        with pytest.raises(AIResponseValidationError, match="'ingredients'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_integer_ingredients(self, valid_ai_payload):
        valid_ai_payload["ingredients"] = 3
        with pytest.raises(AIResponseValidationError, match="'ingredients'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_empty_ingredients_list(self, valid_ai_payload):
        valid_ai_payload["ingredients"] = []
        with pytest.raises(AIResponseValidationError, match="must not be empty"):
            _validate_recipe_payload(valid_ai_payload)

    # --- ingredient entries ---

    def test_rejects_ingredient_as_string(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0] = "chicken breast"
        with pytest.raises(AIResponseValidationError, match="index 0"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_as_integer(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0] = 42
        with pytest.raises(AIResponseValidationError, match="index 0"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_as_none(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0] = None
        with pytest.raises(AIResponseValidationError, match="index 0"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_missing_name(self, valid_ai_payload):
        del valid_ai_payload["ingredients"][0]["name"]
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_empty_name(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["name"] = ""
        with pytest.raises(AIResponseValidationError, match="non-empty"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_whitespace_name(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["name"] = "   "
        with pytest.raises(AIResponseValidationError, match="non-empty"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_null_name(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["name"] = None
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_integer_name(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["name"] = 123
        with pytest.raises(AIResponseValidationError, match="'name'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_missing_unit_key(self, valid_ai_payload):
        del valid_ai_payload["ingredients"][0]["unit"]
        with pytest.raises(AIResponseValidationError, match="'unit'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_accepts_ingredient_with_null_unit(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["unit"] = None
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_rejects_ingredient_integer_unit(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["unit"] = 42
        with pytest.raises(AIResponseValidationError, match="'unit'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_ingredient_list_unit(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["unit"] = ["not", "a", "string"]
        with pytest.raises(AIResponseValidationError, match="'unit'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_accepts_absent_quantity(self, valid_ai_payload):
        del valid_ai_payload["ingredients"][0]["quantity"]
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_accepts_null_quantity(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["quantity"] = None
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_rejects_integer_quantity(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["quantity"] = 2
        with pytest.raises(AIResponseValidationError, match="'quantity'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_float_quantity(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["quantity"] = 2.5
        with pytest.raises(AIResponseValidationError, match="'quantity'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_list_quantity(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["quantity"] = ["not", "a", "string"]
        with pytest.raises(AIResponseValidationError, match="'quantity'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_accepts_absent_prep_note(self, valid_ai_payload):
        del valid_ai_payload["ingredients"][0]["prep_note"]
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_accepts_null_prep_note(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["prep_note"] = None
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_accepts_empty_string_prep_note(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["prep_note"] = ""
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_rejects_integer_prep_note(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["prep_note"] = 42
        with pytest.raises(AIResponseValidationError, match="'prep_note'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_rejects_list_prep_note(self, valid_ai_payload):
        valid_ai_payload["ingredients"][0]["prep_note"] = ["not", "a", "string"]
        with pytest.raises(AIResponseValidationError, match="'prep_note'"):
            _validate_recipe_payload(valid_ai_payload)

    def test_second_ingredient_failure_identified_by_index(self, valid_ai_payload):
        # Confirm error messages include the correct index
        valid_ai_payload["ingredients"][1]["name"] = None
        with pytest.raises(AIResponseValidationError, match="index 1"):
            _validate_recipe_payload(valid_ai_payload)

    def test_third_ingredient_failure_identified_by_index(self, valid_ai_payload):
        # Test with third ingredient to ensure indexing is correct
        valid_ai_payload["ingredients"][2]["unit"] = 42
        with pytest.raises(AIResponseValidationError, match="index 2"):
            _validate_recipe_payload(valid_ai_payload)

    def test_accepts_all_optional_fields_as_null(self, valid_ai_payload):
        # All optional fields should be acceptable as null
        valid_ai_payload["ingredients"][0]["quantity"] = None
        valid_ai_payload["ingredients"][0]["prep_note"] = None
        valid_ai_payload["ingredients"][0]["unit"] = None
        _validate_recipe_payload(valid_ai_payload)  # must not raise

    def test_accepts_all_optional_fields_missing(self, valid_ai_payload):
        # All optional fields should be acceptable when missing
        ingredient = valid_ai_payload["ingredients"][0]
        del ingredient["quantity"]
        del ingredient["prep_note"]
        # unit is required but nullable, so keep it
        _validate_recipe_payload(valid_ai_payload)  # must not raise
