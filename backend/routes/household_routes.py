"""
Household routes — membership management.

JWT still carries individual user_id. These routes let users create
households and invite other registered users by email address.
"""

import logging

from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import household_service
from ..services.exceptions import NotFoundError, ValidationError, ConflictError, ForbiddenError
from ..serializers import household_to_dict, household_member_to_dict

households_bp = Blueprint("households", __name__, url_prefix="/api/households")
logger = logging.getLogger(__name__)


@households_bp.route("", methods=["POST"])
@jwt_required()
def create_household() -> tuple[Response, int]:
    """Create a new household. The caller becomes its admin."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    name = data.get("name", "")

    household = household_service.create_household(user_id, name)
    return jsonify(household_to_dict(household)), 201


@households_bp.route("/me", methods=["GET"])
@jwt_required()
def my_households() -> tuple[Response, int]:
    """Return all households the authenticated user belongs to."""
    user_id = int(get_jwt_identity())
    households = household_service.get_my_households(user_id)
    return jsonify([household_to_dict(h) for h in households]), 200


@households_bp.route("/<int:household_id>/members", methods=["GET"])
@jwt_required()
def get_members(household_id: int) -> tuple[Response, int]:
    """List all members of a household. Caller must be a member."""
    user_id = int(get_jwt_identity())
    members = household_service.list_members(household_id, user_id)
    return jsonify([household_member_to_dict(m) for m in members]), 200


@households_bp.route("/<int:household_id>/invite", methods=["POST"])
@jwt_required()
def invite_member(household_id: int) -> tuple[Response, int]:
    """Invite a registered user by email. Caller must be an admin."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"error": "email is required."}), 400

    member = household_service.invite_member(household_id, user_id, email)
    return jsonify(household_member_to_dict(member)), 201


@households_bp.route("/<int:household_id>/members/<int:target_user_id>", methods=["DELETE"])
@jwt_required()
def remove_member(household_id: int, target_user_id: int) -> tuple[Response, int]:
    """
    Remove a member. Admins can remove anyone; regular members can only
    remove themselves (leave the household).
    """
    user_id = int(get_jwt_identity())
    household_service.remove_member(household_id, user_id, target_user_id)
    return jsonify({"message": "Member removed."}), 200
