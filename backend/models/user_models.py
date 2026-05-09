"""SQLAlchemy data models for user and household management."""

import datetime
from datetime import timezone

from ..extensions import db

# ----------------------------------------------------------------------
#                User and Household Models
# ----------------------------------------------------------------------

class User(db.Model):
    """
    An application user who can own recipes and join households.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc), nullable=False)

    recipes = db.relationship("Recipe", back_populates="owner")
    household_memberships = db.relationship(
        "HouseholdMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    pantry_items = db.relationship(
        "PantryItem",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"

class Household(db.Model):
    """
    A collaboration group where users can share meal planning.
    """

    __tablename__ = "households"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc), nullable=False)

    members = db.relationship(
        "HouseholdMember",
        back_populates="household",
        cascade="all, delete-orphan",
    )
    recipes = db.relationship("Recipe", back_populates="household")

    def __repr__(self) -> str:
        return f"<Household id={self.id} name={self.name}>"


class HouseholdMember(db.Model):
    """
    Join table for many-to-many relation between users and households.
    """
    __tablename__ = "household_members"
    __table_args__ = (
        db.UniqueConstraint("household_id", "user_id", name="uq_household_user"),
    )

    id = db.Column(db.Integer, primary_key=True)

    household_id = db.Column(
        db.Integer,
        db.ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = db.Column(db.String(30), nullable=False, default="member")
    joined_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc), nullable=False)

    household = db.relationship("Household", back_populates="members")
    user = db.relationship("User", back_populates="household_memberships")

    def __repr__(self) -> str:
        return f"<HouseholdMember h={self.household_id} u={self.user_id}>"
