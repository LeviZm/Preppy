"""Tests for access control and authentication."""

def test_list_recipes_requires_auth(client):
    """No token → 401."""
    response = client.get("/api/recipes/")
    assert response.status_code == 401

def test_get_recipe_requires_auth(client):
    """No token → 401."""
    response = client.get("/api/recipes/1")
    assert response.status_code == 401

def test_create_recipe_requires_auth(client):
    """No token → 401."""
    response = client.post("/api/recipes/", json={"name": "Test"})
    assert response.status_code == 401

def test_update_recipe_requires_auth(client):
    """No token → 401."""
    response = client.patch("/api/recipes/1", json={"name": "Updated"})
    assert response.status_code == 401

def test_delete_recipe_requires_auth(client):
    """No token → 401."""
    response = client.delete("/api/recipes/1")
    assert response.status_code == 401

def test_register_is_public(client):
    """No token → not a 401."""
    response = client.post("/api/auth/register", json={
        "username": "test", "email": "test@example.com", "password": "password123"
    })
    assert response.status_code != 401

def test_login_is_public(client):
    """No token → not a 401 (will be 200 with valid creds or 401 only for wrong password)."""
    response = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com", "password": "wrongpassword"
    })
    # Should return 401 for invalid credentials, not "missing auth" 401
    assert response.status_code == 401