"""Tests for recipe ownership and access control."""

import pytest
from ..services import recipe_services as recipe_service
from ..services.exceptions import NotFoundError
from ..tests.conftest import create_test_user, create_test_recipe

def test_user_cannot_read_another_users_recipe(app_context, db_session):
    """
    Core ownership test: the MVP success criterion made executable.
    A valid, authenticated user must not be able to read, update,
    or delete a recipe that belongs to someone else.
    """
    # Arrange — two real users, one recipe
    alice = create_test_user(username="alice", email="alice@test.com")
    bob = create_test_user(username="bob", email="bob@test.com")
    alices_recipe = create_test_recipe(owner=alice, name="Alice's Soup")
    _ = db_session  # use fixture to ensure cleanup

    # Act & Assert — Bob cannot read Alice's recipe
    with pytest.raises(NotFoundError):
        recipe_service.get_recipe(
            user_id=bob.id,
            recipe_id=alices_recipe.id
        )


def test_user_cannot_update_another_users_recipe(app_context, db_session):
    """
    Verify that a user cannot update a recipe they do not own.
    """
    alice = create_test_user(username="alice", email="alice@test.com")
    bob = create_test_user(username="bob", email="bob@test.com")
    alices_recipe = create_test_recipe(owner=alice, name="Alice's Soup")
    _ = db_session

    with pytest.raises(NotFoundError):
        recipe_service.update_recipe(
            user_id=bob.id,
            recipe_id=alices_recipe.id,
            name="Bob's Soup"
        )

    # Confirm the recipe is unchanged
    unchanged = recipe_service.get_recipe(
        user_id=alice.id,
        recipe_id=alices_recipe.id
    )
    assert unchanged.name == "Alice's Soup"


def test_user_cannot_delete_another_users_recipe(app_context, db_session):
    alice = create_test_user(username="alice", email="alice@test.com")
    bob = create_test_user(username="bob", email="bob@test.com")
    alices_recipe = create_test_recipe(owner=alice, name="Alice's Soup")
    _ = db_session

    with pytest.raises(NotFoundError):
        recipe_service.delete_recipe(
            user_id=bob.id,
            recipe_id=alices_recipe.id
        )

    # Confirm the recipe still exists
    still_there = recipe_service.get_recipe(
        user_id=alice.id,
        recipe_id=alices_recipe.id
    )
    assert still_there.id == alices_recipe.id


def test_users_can_share_recipe_names(app_context, db_session):
    """
    Both users can create a recipe called 'Pasta' without conflict.
    Uniqueness is per-user, not global.
    """
    alice = create_test_user(username="alice", email="alice@test.com")
    bob = create_test_user(username="bob", email="bob@test.com")
    _ = db_session

    recipe_service.create_recipe(
        user_id=alice.id, payload={"name": "Pasta", "instructions": "", "ingredients": []}
    )
    # This must not raise ConflictError
    recipe_service.create_recipe(
        user_id=bob.id, payload={"name": "Pasta", "instructions": "", "ingredients": []}
    )