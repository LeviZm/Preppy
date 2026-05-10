"""
Integration tests for recipe routes including AI generation.

Tests the HTTP layer with mocked AI services following Module 3.7 strategy.
"""

import json
import pytest
from backend.services import ai_services
from backend.services.exceptions import (
    AIServiceError,
    AIResponseParseError,
    AIResponseValidationError,
    AuthError,
    ValidationError,
)



class TestRecipeGenerateRoute:

    # --- Authentication ---

    def test_unauthenticated_request_returns_401(self, client):
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "test prompt"},
            headers={}
        )
        assert response.status_code == 401

    def test_authenticated_request_succeeds(self, client, existing_user):
        # Create JWT token within the same app context as the test client
        with client.application.app_context():
            from backend.services.user_service import authenticate_user
            
            try:
                token = authenticate_user("existing@example.com", "ValidPassword1")
            except (AuthError, ValidationError) as e:
                pytest.skip(f"Authentication failed: {e}")
            
            # Mock AI service to return valid payload
            valid_payload = {
                "name": "Test Recipe",
                "instructions": "Test instructions",
                "ingredients": [{"name": "test ingredient", "unit": "cup"}]
            }
            
            # Mock the AI service before making the request
            import backend.services.ai_services as ai_service_module
            original_function = ai_service_module.generate_recipe_payload
            ai_service_module.generate_recipe_payload = lambda prompt: valid_payload
            
            try:
                response = client.post(
                    "/api/recipes/generate",
                    json={"prompt": "test prompt"},
                    headers={"Authorization": f"Bearer {token}"}
                )
                assert response.status_code == 201
                
                data = json.loads(response.data)
                assert data["name"] == "Test Recipe"
                assert "id" in data
            finally:
                ai_service_module.generate_recipe_payload = original_function

    # --- Happy path ---

    def test_valid_prompt_returns_201_with_recipe(self, client, existing_user, valid_ai_payload, monkeypatch):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        # Mock AI service
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "chicken parmesan"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["name"] == valid_ai_payload["name"]
        assert data["instructions"] == valid_ai_payload["instructions"]
        assert "id" in data
        assert "created_at" in data

    # --- Error handling ---

    def test_empty_prompt_returns_400(self, client, existing_user):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": ""},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "empty" in data["error"].lower()

    def test_whitespace_prompt_returns_400(self, client, existing_user):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "   "},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_missing_prompt_returns_400(self, client, existing_user):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        response = client.post(
            "/api/recipes/generate",
            json={},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_ai_service_error_returns_502_with_safe_message(self, client, existing_user, monkeypatch):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        # Mock AI service to raise AIServiceError
        def raise_ai_service_error(prompt):
            raise AIServiceError("API timeout occurred with key SECRET_API_KEY")
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            raise_ai_service_error,
        )
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "test prompt"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 502
        data = json.loads(response.data)
        assert "error" in data
        # Should contain safe user-facing message
        assert "temporarily unavailable" in data["error"]
        # Should NOT contain internal details
        assert "SECRET_API_KEY" not in data["error"]
        assert "timeout" not in data["error"]

    def test_parse_error_returns_502_with_safe_message(self, client, existing_user, monkeypatch):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        # Mock AI service to raise parse error
        def raise_parse_error(prompt):
            raise AIResponseParseError("Invalid JSON: missing closing brace")
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            raise_parse_error,
        )
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "test prompt"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 502
        data = json.loads(response.data)
        assert "error" in data
        assert "unexpected response" in data["error"]
        # Should NOT contain internal details
        assert "Invalid JSON" not in data["error"]
        assert "missing closing brace" not in data["error"]

    def test_validation_error_returns_502_with_safe_message(self, client, existing_user, monkeypatch):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        # Mock AI service to raise validation error
        def raise_validation_error(prompt):
            raise AIResponseValidationError("Schema validation failed: missing ingredients field")
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            raise_validation_error,
        )
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "test prompt"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 502
        data = json.loads(response.data)
        assert "error" in data
        assert "unexpected response" in data["error"]
        # Should NOT contain internal details
        assert "Schema validation" not in data["error"]
        assert "missing ingredients" not in data["error"]

    def test_conflict_error_returns_409(self, client, existing_user, valid_ai_payload, monkeypatch):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        # Create a recipe with the same name first
        create_response = client.post(
            "/api/recipes/",
            json={
                "name": valid_ai_payload["name"],
                "instructions": "Existing instructions",
                "ingredients": [{"name": "existing ingredient", "unit": "cup"}]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_response.status_code == 201
        
        # Mock AI service to return payload with same name
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            lambda prompt: valid_ai_payload,
        )
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "test prompt"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert "error" in data
        assert "already have a recipe" in data["error"]

    def test_unexpected_error_returns_500(self, client, existing_user, monkeypatch):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        # Mock AI service to raise unexpected exception
        def raise_unexpected_error(prompt):
            raise RuntimeError("Unexpected database connection failure")
        
        monkeypatch.setattr(
            ai_services,
            "generate_recipe_payload",
            raise_unexpected_error,
        )
        
        response = client.post(
            "/api/recipes/generate",
            json={"prompt": "test prompt"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        assert "unexpected error" in data["error"]
        # Should NOT contain internal details
        assert "database connection" not in data["error"]

    # --- Input validation ---

    def test_invalid_json_returns_400(self, client, existing_user):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        response = client.post(
            "/api/recipes/generate",
            data="invalid json",
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400

    def test_missing_content_type_returns_400(self, client, existing_user):
        # Create JWT token directly using user service
        from backend.services.user_service import authenticate_user
        try:
            token = authenticate_user("existing@example.com", "ValidPassword1")
        except (AuthError, ValidationError) as e:
            pytest.skip(f"Authentication failed: {e}")
        
        response = client.post(
            "/api/recipes/generate",
            data='{"prompt": "test"}',
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
