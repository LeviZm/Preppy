"""
Meal planning and shopping list service implementations.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from ..extensions import db
from ..models import MealPlan, Recipe, ShoppingList, ShoppingListItem
from .exceptions import NotFoundError, ValidationError
from .ingredients_services import get_or_create_ingredient
from .transaction import atomic
from . import household_service

logger = logging.getLogger(__name__)

_VALID_MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}


# -----------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------

def _parse_date(raw: Any) -> date:
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except (ValueError, TypeError) as exc:
        raise ValidationError("planned_date must be a valid ISO date (YYYY-MM-DD).") from exc


def _parse_servings(raw: Any) -> int:
    try:
        value = int(raw)
    except (ValueError, TypeError) as exc:
        raise ValidationError("servings must be a positive integer.") from exc
    if value < 1:
        raise ValidationError("servings must be at least 1.")
    return value


def _parse_quantity(raw: Any) -> Decimal:
    try:
        qty = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError("Invalid quantity format.") from exc
    if qty <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    return qty


def _fetch_owned_plan(meal_plan_id: int, user_id: int) -> MealPlan:
    plan = MealPlan.query.filter_by(id=meal_plan_id, user_id=user_id).first()
    if not plan:
        raise NotFoundError("Meal plan not found.")
    return plan


def _fetch_owned_list(shopping_list_id: int, user_id: int) -> ShoppingList:
    sl = ShoppingList.query.filter_by(id=shopping_list_id, user_id=user_id).first()
    if not sl:
        raise NotFoundError("Shopping list not found.")
    return sl


# -----------------------------------------------------------------------
# MealPlan CRUD
# -----------------------------------------------------------------------

def create_meal_plan(user_id: int, payload: Dict[str, Any]) -> MealPlan:
    """
    Create a meal plan entry for a user.

    Required payload keys: recipe_id, planned_date
    Optional: meal_type (breakfast|lunch|dinner|snack), servings, notes
    """
    recipe_id = payload.get("recipe_id")
    if not recipe_id:
        raise ValidationError("recipe_id is required.")

    household_ids = household_service.get_user_household_ids(user_id)
    recipe = Recipe.query.filter(
        Recipe.id == int(recipe_id),
        db.or_(
            Recipe.owner_user_id == user_id,
            db.and_(Recipe.household_id.isnot(None), Recipe.household_id.in_(household_ids))
        )
    ).first()
    if not recipe:
        raise NotFoundError("Recipe not found.")

    planned_date = _parse_date(payload.get("planned_date"))

    meal_type = str(payload.get("meal_type") or "dinner").lower()
    if meal_type not in _VALID_MEAL_TYPES:
        raise ValidationError(f"meal_type must be one of: {', '.join(sorted(_VALID_MEAL_TYPES))}.")

    servings = _parse_servings(payload.get("servings", 1))
    notes = str(payload.get("notes") or "").strip() or None

    plan = MealPlan(
        user_id=user_id,
        recipe_id=recipe.id,
        planned_date=planned_date,
        meal_type=meal_type,
        servings=servings,
        notes=notes,
    )
    with atomic("A meal plan for this recipe on this date already exists."):
        db.session.add(plan)

    logger.info("MealPlan %d created for user %d.", plan.id, user_id)
    return plan


def list_meal_plans(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[MealPlan]:
    """List meal plans accessible to a user (their own + household members')."""
    household_ids = household_service.get_user_household_ids(user_id)
    household_member_ids: List[int] = []
    if household_ids:
        from ..models import HouseholdMember
        rows = HouseholdMember.query.filter(
            HouseholdMember.household_id.in_(household_ids)
        ).all()
        household_member_ids = list({r.user_id for r in rows})
    visible_user_ids = list({user_id, *household_member_ids})
    query = MealPlan.query.filter(MealPlan.user_id.in_(visible_user_ids))
    if start_date:
        query = query.filter(MealPlan.planned_date >= start_date)
    if end_date:
        query = query.filter(MealPlan.planned_date <= end_date)
    return query.order_by(MealPlan.planned_date.asc(), MealPlan.meal_type.asc()).all()


def get_meal_plan(meal_plan_id: int, user_id: int) -> MealPlan:
    return _fetch_owned_plan(meal_plan_id, user_id)


def update_meal_plan(user_id: int, meal_plan_id: int, payload: Dict[str, Any]) -> MealPlan:
    """
    Partial-update a meal plan. Any provided key overwrites the current value.
    """
    plan = _fetch_owned_plan(meal_plan_id, user_id)

    if "planned_date" in payload:
        plan.planned_date = _parse_date(payload["planned_date"])
    if "meal_type" in payload:
        mt = str(payload["meal_type"]).lower()
        if mt not in _VALID_MEAL_TYPES:
            raise ValidationError(f"meal_type must be one of: {', '.join(sorted(_VALID_MEAL_TYPES))}.")
        plan.meal_type = mt
    if "servings" in payload:
        plan.servings = _parse_servings(payload["servings"])
    if "notes" in payload:
        plan.notes = str(payload["notes"]).strip() or None

    with atomic("A meal plan for this recipe on this date already exists."):
        pass

    logger.info("MealPlan %d updated for user %d.", meal_plan_id, user_id)
    return plan


def delete_meal_plan(meal_plan_id: int, user_id: int) -> None:
    plan = _fetch_owned_plan(meal_plan_id, user_id)
    with atomic():
        db.session.delete(plan)
    logger.info("MealPlan %d deleted by user %d.", meal_plan_id, user_id)


# -----------------------------------------------------------------------
# ShoppingList CRUD
# -----------------------------------------------------------------------

def create_shopping_list(user_id: int, payload: Dict[str, Any]) -> ShoppingList:
    """
    Create an empty shopping list for a user.

    Required: name
    Optional: meal_plan_id, items ([{ingredient_name|ingredient_id, quantity, unit}])
    """
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValidationError("Shopping list name is required.")

    meal_plan_id = payload.get("meal_plan_id")
    if meal_plan_id is not None:
        _fetch_owned_plan(int(meal_plan_id), user_id)

    sl = ShoppingList(
        user_id=user_id,
        meal_plan_id=int(meal_plan_id) if meal_plan_id is not None else None,
        name=name,
    )
    with atomic():
        db.session.add(sl)
        db.session.flush()
        _sync_items(sl, payload.get("items") or [])

    logger.info("ShoppingList %d created for user %d.", sl.id, user_id)
    return sl


def list_shopping_lists(user_id: int) -> List[ShoppingList]:
    return (
        ShoppingList.query
        .filter_by(user_id=user_id)
        .order_by(ShoppingList.created_at.desc())
        .all()
    )


def get_shopping_list(shopping_list_id: int, user_id: int) -> ShoppingList:
    return _fetch_owned_list(shopping_list_id, user_id)


def update_shopping_list(user_id: int, shopping_list_id: int, payload: Dict[str, Any]) -> ShoppingList:
    """
    Partial-update a shopping list header and optionally sync its items.
    If 'items' is provided, the list is fully replaced (same sync logic as recipes).
    """
    sl = _fetch_owned_list(shopping_list_id, user_id)

    if "name" in payload:
        name = str(payload["name"]).strip()
        if not name:
            raise ValidationError("Shopping list name cannot be empty.")
        sl.name = name
    if "is_complete" in payload:
        sl.is_complete = bool(payload["is_complete"])

    with atomic():
        if "items" in payload:
            _sync_items(sl, payload["items"])

    logger.info("ShoppingList %d updated for user %d.", shopping_list_id, user_id)
    return sl


def delete_shopping_list(shopping_list_id: int, user_id: int) -> None:
    sl = _fetch_owned_list(shopping_list_id, user_id)
    with atomic():
        db.session.delete(sl)
    logger.info("ShoppingList %d deleted by user %d.", shopping_list_id, user_id)


# -----------------------------------------------------------------------
# ShoppingListItem helpers
# -----------------------------------------------------------------------

def _sync_items(sl: ShoppingList, raw_items: List[Dict[str, Any]]) -> None:
    """
    Replace all items on a shopping list with the provided list.
    Merges by ingredient: creates missing, updates existing, deletes removed.
    """
    existing_map: Dict[int, ShoppingListItem] = {item.ingredient_id: item for item in sl.items}
    incoming_ids: List[int] = []

    for idx, raw in enumerate(raw_items):
        ing = get_or_create_ingredient(
            str(raw.get("ingredient_name") or raw.get("name") or "").strip()
        ) if not raw.get("ingredient_id") else None

        if ing is None and raw.get("ingredient_id"):
            from ..models import Ingredient
            ing = Ingredient.query.get(int(raw["ingredient_id"]))
            if not ing:
                raise NotFoundError(f"Ingredient id={raw['ingredient_id']} not found.")

        if ing is None:
            raise ValidationError("Each item must supply ingredient_name or ingredient_id.")

        qty = _parse_quantity(raw.get("quantity", 1))
        unit = str(raw.get("unit") or "unit").strip() or "unit"

        incoming_ids.append(ing.id)
        existing = existing_map.get(ing.id)
        if existing:
            existing.quantity = qty
            existing.unit = unit
            existing.sort_order = idx
        else:
            db.session.add(ShoppingListItem(
                shopping_list_id=sl.id,
                ingredient_id=ing.id,
                quantity=qty,
                unit=unit,
                sort_order=idx,
            ))

    for ing_id, item in existing_map.items():
        if ing_id not in incoming_ids:
            db.session.delete(item)


def check_item(shopping_list_id: int, item_id: int, user_id: int, is_checked: bool) -> ShoppingListItem:
    """Toggle the checked state of a single shopping list item."""
    sl = _fetch_owned_list(shopping_list_id, user_id)
    item = ShoppingListItem.query.filter_by(id=item_id, shopping_list_id=sl.id).first()
    if not item:
        raise NotFoundError("Shopping list item not found.")
    with atomic():
        item.is_checked = is_checked
    return item


def generate_list_from_meal_plan(user_id: int, meal_plan_id: int, list_name: Optional[str] = None) -> ShoppingList:
    """
    Auto-generate a shopping list from all recipes in a meal plan,
    aggregating ingredient quantities across recipes (scaled by servings).
    Ingredients already in the pantry are included but not subtracted
    (pantry deduction is a UX concern for the frontend).
    """
    plan = _fetch_owned_plan(meal_plan_id, user_id)
    name = list_name or f"Shopping list for {plan.planned_date.isoformat()}"

    from ..models import RecipeIngredient
    ri_rows: List[RecipeIngredient] = (
        db.session.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == plan.recipe_id)
        .all()
    )

    aggregated: Dict[int, Tuple[Decimal, str]] = {}
    for ri in ri_rows:
        scaled_qty = Decimal(str(ri.quantity)) * plan.servings
        if ri.ingredient_id in aggregated:
            prev_qty, prev_unit = aggregated[ri.ingredient_id]
            aggregated[ri.ingredient_id] = (prev_qty + scaled_qty, prev_unit)
        else:
            aggregated[ri.ingredient_id] = (scaled_qty, ri.unit)

    items_payload = [
        {"ingredient_id": ing_id, "quantity": str(qty), "unit": unit}
        for ing_id, (qty, unit) in aggregated.items()
    ]

    return create_shopping_list(user_id, {
        "name": name,
        "meal_plan_id": meal_plan_id,
        "items": items_payload,
    })
