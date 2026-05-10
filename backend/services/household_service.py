"""
Household service — create households, manage membership, and resolve
the household_ids a given user belongs to.

The JWT never changes. It still carries the individual user_id.
What changes is that every ownership query in recipe/meal services
will call `get_user_household_ids(user_id)` and widen the filter to
include rows belonging to any of those households.
"""

import logging
from typing import List

from ..extensions import db
from ..models import Household, HouseholdMember, User
from .exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from .transaction import atomic

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _get_membership(household_id: int, user_id: int) -> HouseholdMember:
    m = HouseholdMember.query.filter_by(
        household_id=household_id, user_id=user_id
    ).first()
    if not m:
        raise NotFoundError("Household not found.")
    return m


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def get_user_household_ids(user_id: int) -> List[int]:
    """
    Return the list of household IDs the user belongs to.
    Used by recipe/meal services to widen ownership filters.
    """
    rows = HouseholdMember.query.filter_by(user_id=user_id).all()
    return [r.household_id for r in rows]


def create_household(user_id: int, name: str) -> Household:
    """
    Create a new household and add the creator as 'admin'.
    """
    name = name.strip()
    if not name:
        raise ValidationError("Household name is required.")
    if len(name) > 120:
        raise ValidationError("Household name must be 120 characters or less.")

    with atomic():
        household = Household(name=name)
        db.session.add(household)
        db.session.flush()
        member = HouseholdMember(
            household_id=household.id,
            user_id=user_id,
            role="admin",
        )
        db.session.add(member)

    logger.info("Household %d created by user %d.", household.id, user_id)
    return household


def get_my_households(user_id: int) -> List[Household]:
    """Return all households the user belongs to, with their members."""
    memberships = HouseholdMember.query.filter_by(user_id=user_id).all()
    return [m.household for m in memberships]


def invite_member(household_id: int, inviter_id: int, email: str) -> HouseholdMember:
    """
    Add a user to a household by email. Only admins may invite.
    """
    _require_admin(household_id, inviter_id)

    invitee = User.query.filter_by(email=email.strip().lower()).first()
    if not invitee:
        raise NotFoundError("No account found with that email address.")

    existing = HouseholdMember.query.filter_by(
        household_id=household_id, user_id=invitee.id
    ).first()
    if existing:
        raise ConflictError("That user is already a member of this household.")

    with atomic():
        member = HouseholdMember(
            household_id=household_id,
            user_id=invitee.id,
            role="member",
        )
        db.session.add(member)

    logger.info(
        "User %d invited user %d to household %d.",
        inviter_id, invitee.id, household_id,
    )
    return member


def remove_member(household_id: int, actor_id: int, target_user_id: int) -> None:
    """
    Remove a member from a household.
    - Admins may remove anyone except themselves if they are the last admin.
    - Non-admins may only remove themselves (leave).
    """
    actor = _get_membership(household_id, actor_id)
    target = HouseholdMember.query.filter_by(
        household_id=household_id, user_id=target_user_id
    ).first()
    if not target:
        raise NotFoundError("Member not found in this household.")

    if actor_id != target_user_id and actor.role != "admin":
        raise ForbiddenError("Only admins can remove other members.")

    admin_count = HouseholdMember.query.filter_by(
        household_id=household_id, role="admin"
    ).count()
    if target.role == "admin" and admin_count == 1:
        raise ValidationError(
            "Cannot remove the last admin. Promote another member first."
        )

    with atomic():
        db.session.delete(target)

    logger.info(
        "User %d removed user %d from household %d.",
        actor_id, target_user_id, household_id,
    )


def list_members(household_id: int, user_id: int) -> List[HouseholdMember]:
    """Return all members of a household. Caller must be a member."""
    _get_membership(household_id, user_id)
    return HouseholdMember.query.filter_by(household_id=household_id).all()


# -----------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------

def _require_admin(household_id: int, user_id: int) -> HouseholdMember:
    m = _get_membership(household_id, user_id)
    if m.role != "admin":
        raise ForbiddenError("Only admins can perform this action.")
    return m
