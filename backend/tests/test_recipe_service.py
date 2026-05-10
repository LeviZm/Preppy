"""Tests for recipe service operations."""

import pytest
from ..services import recipe_services as recipe_service
from ..services.exceptions import NotFoundError


def test_get_recipe_wrong_owner_raises_not_found(app_context, user_a, user_b, recipe_owned_by_a):
    """User B cannot retrieve User A's recipe."""
    with pytest.raises(NotFoundError):
        recipe_service.get_recipe(
            user_id=user_b.id, recipe_id=recipe_owned_by_a.id
        )

def test_update_recipe_wrong_owner_raises_not_found(app_context, user_a, user_b, recipe_owned_by_a):
    """User B cannot update User A's recipe."""
    with pytest.raises(NotFoundError):
        recipe_service.update_recipe(
            user_id=user_b.id,
            recipe_id=recipe_owned_by_a.id,
            name="Hijacked Recipe"
        )

def test_delete_recipe_wrong_owner_raises_not_found(app_context, user_a, user_b, recipe_owned_by_a):
    """User B cannot delete User A's recipe."""
    with pytest.raises(NotFoundError):
        recipe_service.delete_recipe(
            user_id=user_b.id,
            recipe_id=recipe_owned_by_a.id
        )

def test_delete_recipe_wrong_owner_leaves_record_intact(app_context, user_a, user_b, recipe_owned_by_a):
    """After a failed delete attempt by the wrong user, the record still exists."""
    with pytest.raises(NotFoundError):
        recipe_service.delete_recipe(
            user_id=user_b.id,
            recipe_id=recipe_owned_by_a.id
        )
    # The recipe must still be retrievable by its real owner
    recipe = recipe_service.get_recipe(
        user_id=user_a.id, recipe_id=recipe_owned_by_a.id
    )
    assert recipe.id == recipe_owned_by_a.id

def test_update_recipe_wrong_owner_does_not_modify_record(app_context, user_a, user_b, recipe_owned_by_a):
    """After a failed update attempt by the wrong user, the record is unchanged."""
    original_name = recipe_owned_by_a.name
    with pytest.raises(NotFoundError):
        recipe_service.update_recipe(
            user_id=user_b.id,
            recipe_id=recipe_owned_by_a.id,
            name="Hijacked Recipe"
        )
    recipe = recipe_service.get_recipe(
        user_id=user_a.id, recipe_id=recipe_owned_by_a.id
    )
    assert recipe.name == original_name