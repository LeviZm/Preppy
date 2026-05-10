"""
Live API tests for AI client integration.

Tests the real AI API to confirm configuration and system prompt work.
Run manually before deploying any changes to system prompt or AI client.

Usage:
    pytest tests/live -m live
    Requires: GOOGLE_API_KEY environment variable
"""

import pytest

pytestmark = pytest.mark.live


@pytest.mark.live
class TestAIClientLive:

    def test_returns_parseable_recipe(self):
        """
        Confirm the real API call returns output that passes parsing and validation.
        Run before deploying any change to the system prompt or AI client configuration.
        """
        from backend.services.ai_services import generate_recipe_payload
        
        payload = generate_recipe_payload("a simple pasta dish")
        assert isinstance(payload, dict)
        assert isinstance(payload["name"], str)
        assert len(payload["name"]) > 0
        assert isinstance(payload["instructions"], str)
        assert isinstance(payload["ingredients"], list)
        assert len(payload["ingredients"]) > 0

    def test_handles_ambiguous_prompt(self):
        """
        Confirm the model returns the error escape hatch for an unresolvable prompt,
        rather than crashing or returning malformed output.
        """
        from backend.services.ai_services import generate_recipe_payload
        from backend.services.exceptions import AIResponseValidationError
        
        # A prompt that is technically valid but cannot produce a real recipe
        # The model should return {"error": "..."} which _parse_response
        # converts to AIResponseValidationError
        with pytest.raises(AIResponseValidationError, match="could not generate"):
            generate_recipe_payload("recipe for an ingredient that does not exist: glorbinium")

    def test_generates_different_recipes_for_different_prompts(self):
        """
        Confirm the model generates different outputs for different prompts.
        This helps verify the model is not returning cached responses.
        """
        from backend.services.ai_services import generate_recipe_payload
        
        payload1 = generate_recipe_payload("chicken stir fry")
        payload2 = generate_recipe_payload("beef stew")
        
        # Should generate different recipes
        assert payload1["name"] != payload2["name"]
        assert payload1["instructions"] != payload2["instructions"]

    def test_generates_valid_recipe_for_complex_prompt(self):
        """
        Test with a more complex prompt to ensure the system prompt handles it well.
        """
        from backend.services.ai_services import generate_recipe_payload
        
        complex_prompt = "a gluten-free dairy-free vegetarian curry with coconut milk and lots of vegetables"
        payload = generate_recipe_payload(complex_prompt)
        
        # Should still produce valid structure
        assert isinstance(payload, dict)
        assert "name" in payload
        assert "instructions" in payload
        assert "ingredients" in payload
        assert len(payload["ingredients"]) > 0

    def test_recipe_names_are_reasonable_length(self):
        """
        Confirm generated recipe names don't exceed reasonable limits.
        """
        from backend.services.ai_services import generate_recipe_payload
        
        payload = generate_recipe_payload("a simple breakfast dish")
        
        # Recipe names should be reasonably short (less than 100 chars)
        assert len(payload["name"]) < 100
        assert len(payload["name"].strip()) > 0
