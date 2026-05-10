"""
Meal planning and shopping list routes.
"""

import logging
from datetime import date
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..serializers import mealplan_to_dict, shoppinglist_to_dict, shoppinglistitem_to_dict
from ..services import meals_services as svc
from ..services.exceptions import ConflictError, NotFoundError, ValidationError

meals_bp = Blueprint("meals", __name__, url_prefix="/api/meals")

logger = logging.getLogger(__name__)


def _uid() -> int:
    return int(get_jwt_identity())


# -----------------------------------------------------------------------
# MealPlan endpoints   /api/meals/plans
# -----------------------------------------------------------------------

@meals_bp.route("/plans", methods=["GET"])
@jwt_required()
def list_plans() -> Any:
    start = request.args.get("start")
    end = request.args.get("end")

    start_date = None
    end_date = None
    try:
        if start:
            start_date = date.fromisoformat(start)
        if end:
            end_date = date.fromisoformat(end)
    except ValueError:
        return jsonify({"error": "start/end must be ISO dates (YYYY-MM-DD)."}), 400

    plans = svc.list_meal_plans(_uid(), start_date=start_date, end_date=end_date)
    return jsonify({"meal_plans": [mealplan_to_dict(p) for p in plans]}), 200


@meals_bp.route("/plans", methods=["POST"])
@jwt_required()
def create_plan() -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        plan = svc.create_meal_plan(_uid(), payload)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ConflictError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"meal_plan": mealplan_to_dict(plan)}), 201


@meals_bp.route("/plans/<int:plan_id>", methods=["GET"])
@jwt_required()
def get_plan(plan_id: int) -> Any:
    try:
        plan = svc.get_meal_plan(plan_id, _uid())
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"meal_plan": mealplan_to_dict(plan)}), 200


@meals_bp.route("/plans/<int:plan_id>", methods=["PATCH"])
@jwt_required()
def update_plan(plan_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        plan = svc.update_meal_plan(_uid(), plan_id, payload)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ConflictError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"meal_plan": mealplan_to_dict(plan)}), 200


@meals_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
@jwt_required()
def delete_plan(plan_id: int) -> Any:
    try:
        svc.delete_meal_plan(plan_id, _uid())
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"msg": "Meal plan deleted."}), 200


# -----------------------------------------------------------------------
# ShoppingList endpoints   /api/meals/shopping
# -----------------------------------------------------------------------

@meals_bp.route("/shopping", methods=["GET"])
@jwt_required()
def list_lists() -> Any:
    lists = svc.list_shopping_lists(_uid())
    return jsonify({"shopping_lists": [shoppinglist_to_dict(sl) for sl in lists]}), 200


@meals_bp.route("/shopping", methods=["POST"])
@jwt_required()
def create_list() -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        sl = svc.create_shopping_list(_uid(), payload)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"shopping_list": shoppinglist_to_dict(sl)}), 201


@meals_bp.route("/shopping/<int:list_id>", methods=["GET"])
@jwt_required()
def get_list(list_id: int) -> Any:
    try:
        sl = svc.get_shopping_list(list_id, _uid())
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"shopping_list": shoppinglist_to_dict(sl)}), 200


@meals_bp.route("/shopping/<int:list_id>", methods=["PATCH"])
@jwt_required()
def update_list(list_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        sl = svc.update_shopping_list(_uid(), list_id, payload)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"shopping_list": shoppinglist_to_dict(sl)}), 200


@meals_bp.route("/shopping/<int:list_id>", methods=["DELETE"])
@jwt_required()
def delete_list(list_id: int) -> Any:
    try:
        svc.delete_shopping_list(list_id, _uid())
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"msg": "Shopping list deleted."}), 200


@meals_bp.route("/shopping/<int:list_id>/items/<int:item_id>/check", methods=["PATCH"])
@jwt_required()
def check_item(list_id: int, item_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    is_checked = bool(payload.get("is_checked", True))
    try:
        item = svc.check_item(list_id, item_id, _uid(), is_checked)
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"item": shoppinglistitem_to_dict(item)}), 200


@meals_bp.route("/shopping/generate/<int:plan_id>", methods=["POST"])
@jwt_required()
def generate_from_plan(plan_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    try:
        sl = svc.generate_list_from_meal_plan(_uid(), plan_id, payload.get("name"))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"shopping_list": shoppinglist_to_dict(sl)}), 201