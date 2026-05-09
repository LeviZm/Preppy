"""
Meal routes (minimal placeholders).
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from typing import Any

meals_bp = Blueprint("meals", __name__, url_prefix="/api/meals")


@meals_bp.route("/", methods=["GET"])
def list_meals() -> Any:
    return jsonify({"meals": []}), 200


@meals_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected_meals():
    user_id = get_jwt_identity()
    return jsonify({"msg": "protected", "user_id": user_id}), 200