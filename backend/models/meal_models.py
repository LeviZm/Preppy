"""SQLAlchemy data models for meals, meal plans, shopping lists, and pantry management."""

from datetime import datetime, timezone

from ..extensions import db

# -----------------------------------------------------------------------
#       Models for Meal Planning and Shopping List Management
# -----------------------------------------------------------------------

# TODO: Add MealPlan and ShoppingList models with appropriate relationships to User, Recipe, and PantryItem.
# class MealPlan(db.Model):
    """
    User-specific meal plan with scheduled recipes for
    calendar integration and shopping list generation.
    """

# class ShoppingList(db.Model):
    """
    User-specific shopping list for generating grocery lists
    based on meal plans and pantry inventory.
    """

class PantryItem(db.Model):
    """
    User-specific pantry inventory for meal planning and shopping list generation.
    """

    __tablename__ = "pantry_items"
    __table_args__ = (
        db.UniqueConstraint("user_id", "ingredient_id", name="uq_pantry_user_ingredient"),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id = db.Column(
        db.Integer,
        db.ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="pantry_items")
    ingredient = db.relationship("Ingredient", back_populates="pantry_items")
