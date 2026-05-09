"""
Shopping pantry service implementations.

These helpers scope all pantry mutations to a user and keep quantity handling
decimal-based to avoid float drift.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple

from ..extensions import db
from ..models import Ingredient, PantryItem
from .exceptions import NotFoundError, ValidationError
from .ingredients_services import create_ingredient, get_ingredient_by_id
from .transaction import atomic

logger = logging.getLogger(__name__)


def _parse_quantity(raw_quantity: Any) -> Decimal:
    try:
        quantity = Decimal(str(raw_quantity))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError("Invalid quantity format.") from exc

    if quantity < 0:
        raise ValidationError("Quantity must be non-negative.")

    return quantity


def _normalize_unit(unit: Any) -> str:
    unit_text = str(unit or "unit").strip()
    return unit_text or "unit"


def _resolve_ingredient(payload: dict[str, Any]) -> Optional[Ingredient]:
    raw_ingredient_id = payload.get("ingredient_id")
    if raw_ingredient_id is not None:
        try:
            ingredient_id = int(raw_ingredient_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid ingredient_id format.") from exc

        return get_ingredient_by_id(ingredient_id)

    name = str(payload.get("ingredient_name") or payload.get("name") or "").strip()
    if not name:
        raise ValidationError("Ingredient name is required.")

    ingredient, _ = create_ingredient(name)
    return ingredient


def get_user_pantry(user_id: int) -> list[PantryItem]:
    """Get all pantry items for a user, ordered by most recently updated."""

    logger.debug("Fetching pantry for user %d.", user_id)
    return PantryItem.query.filter_by(user_id=user_id)\
        .order_by(PantryItem.updated_at.desc(), PantryItem.id.asc()).all()

def add_or_merge_to_pantry(user_id: int, payload: dict[str, Any]) -> Tuple[PantryItem, bool]:
    """Add a new pantry item or merge with an existing one if the ingredient matches.
    Returns the pantry item and a boolean indicating if it was created (True) or merged (False)."""

    ingredient = _resolve_ingredient(payload)
    if ingredient is None:
        logger.warning("Ingredient not found for pantry add, user %d, payload=%r.", user_id, payload)
        raise NotFoundError("Ingredient not found.")

    quantity = _parse_quantity(payload.get("quantity"))
    unit = _normalize_unit(payload.get("unit"))

    pantry_item = PantryItem.query.filter_by(user_id=user_id, ingredient_id=ingredient.id).first()
    created = pantry_item is None

    with atomic("A pantry item for this ingredient already exists."):
        if pantry_item is None:
            pantry_item = PantryItem(
                user_id=user_id,
                ingredient_id=ingredient.id,
                quantity=quantity,
                unit=unit,
            )
            db.session.add(pantry_item)
        else:
            pantry_item.quantity = (pantry_item.quantity or Decimal("0")) + quantity
            pantry_item.unit = unit

    action = "created" if created else "merged"
    logger.info("Pantry item %s for ingredient %d, user %d.", action, ingredient.id, user_id)
    return pantry_item, created


def update_pantry_quantity(
    user_id: int,
    pantry_item_id: int,
    quantity_value: Any,
    unit: Any = None,
) -> Optional[PantryItem]:
    """
    Update the quantity and optionally the unit of a pantry item.
    Returns the updated item or None if not found.
    """
    pantry_item = PantryItem.query.filter_by(id=pantry_item_id, user_id=user_id).first()
    if pantry_item is None:
        logger.warning("Pantry item %d not found for user %d.", pantry_item_id, user_id)
        return None

    with atomic():
        pantry_item.quantity = _parse_quantity(quantity_value)
        if unit is not None:
            pantry_item.unit = _normalize_unit(unit)

    logger.info("Pantry item %d updated for user %d.", pantry_item_id, user_id)
    return pantry_item


def remove_from_pantry(user_id: int, pantry_item_id: int) -> bool:
    """Remove a pantry item by ID. Returns True if removed, False if not found."""
    pantry_item = PantryItem.query.filter_by(id=pantry_item_id, user_id=user_id).first()
    if pantry_item is None:
        logger.warning("Pantry item %d not found for user %d on delete.", pantry_item_id, user_id)
        return False

    with atomic():
        db.session.delete(pantry_item)
    logger.info("Pantry item %d removed for user %d.", pantry_item_id, user_id)
    return True
