"""
Ingredient service implementations.

This module owns canonical ingredient lookup and creation so callers can rely
on one case-insensitive source of truth.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy import func

from ..extensions import db
from ..models import Ingredient
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def list_ingredients() -> List[Ingredient]:
    """List all ingredients, sorted by name and ID."""
    return Ingredient.query.order_by(func.lower(Ingredient.name), Ingredient.id).all()


def get_ingredient_by_id(ingredient_id: int) -> Optional[Ingredient]:
    """Get an ingredient by ID."""

    return db.session.get(Ingredient, ingredient_id)


def get_ingredient_by_name(name: str) -> Optional[Ingredient]:
    """Get an ingredient by name (case-insensitive)."""

    cleaned_name = _normalize_name(name)
    if not cleaned_name:
        return None

    return Ingredient.query.filter(func.lower(Ingredient.name) == cleaned_name.lower()).first()


def create_ingredient(name: str) -> Tuple[Ingredient, bool]:
    """Create a new ingredient if it doesn't already exist."""

    cleaned_name = _normalize_name(name)
    if not cleaned_name:
        raise ValidationError("Ingredient name is required.")

    existing = get_ingredient_by_name(cleaned_name)
    if existing is not None:
        logger.debug("Ingredient '%s' already exists (id=%d).", cleaned_name, existing.id)
        return existing, False

    ingredient = Ingredient(name=cleaned_name)
    db.session.add(ingredient)
    db.session.flush()
    logger.info("Ingredient '%s' created (id=%d).", cleaned_name, ingredient.id)
    return ingredient, True


def get_or_create_ingredient(name: str) -> Ingredient:
    """Get an ingredient by name, or create it if it doesn't exist."""

    ingredient, _ = create_ingredient(name)
    return ingredient
