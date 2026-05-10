"""SQLAlchemy data models for meals, meal plans, shopping lists, and pantry management."""

from datetime import datetime, timezone

from ..extensions import db

# -----------------------------------------------------------------------
#       Models for Meal Planning and Shopping List Management
# -----------------------------------------------------------------------

class MealPlan(db.Model):  # type: ignore[name-defined]
    """
    User-specific meal plan with scheduled recipes for
    calendar integration and shopping list generation.
    """

    __tablename__ = "meal_plans"
    __table_args__ = (
        db.UniqueConstraint("user_id", "recipe_id", "planned_date", name="uq_mealplan_user_recipe_date"),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )

    planned_date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(30), nullable=False, default="dinner")
    servings = db.Column(db.Integer, nullable=False, default=1)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="meal_plans")
    recipe = db.relationship("Recipe", back_populates="meal_plans")

    shopping_lists = db.relationship(
        "ShoppingList",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MealPlan id={self.id} user={self.user_id} date={self.planned_date}>"


class ShoppingList(db.Model):  # type: ignore[name-defined]
    """
    User-specific shopping list for generating grocery lists
    based on meal plans and pantry inventory.
    """

    __tablename__ = "shopping_lists"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meal_plan_id = db.Column(
        db.Integer,
        db.ForeignKey("meal_plans.id", ondelete="SET NULL"),
        nullable=True,
    )

    name = db.Column(db.String(150), nullable=False)
    is_complete = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="shopping_lists")
    meal_plan = db.relationship("MealPlan", back_populates="shopping_lists")

    items = db.relationship(
        "ShoppingListItem",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="ShoppingListItem.sort_order",
    )

    def __repr__(self) -> str:
        return f"<ShoppingList id={self.id} user={self.user_id} name={self.name!r}>"


class ShoppingListItem(db.Model):  # type: ignore[name-defined]
    """
    A single line item on a shopping list, linked to a canonical ingredient.
    """

    __tablename__ = "shopping_list_items"
    __table_args__ = (
        db.UniqueConstraint("shopping_list_id", "ingredient_id", name="uq_shoppingitem_list_ingredient"),
    )

    id = db.Column(db.Integer, primary_key=True)

    shopping_list_id = db.Column(
        db.Integer,
        db.ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id = db.Column(
        db.Integer,
        db.ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    is_checked = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    shopping_list = db.relationship("ShoppingList", back_populates="items")
    ingredient = db.relationship("Ingredient", back_populates="shopping_list_items")

    def __repr__(self) -> str:
        return (
            f"<ShoppingListItem list={self.shopping_list_id} "
            f"ingredient={self.ingredient_id} qty={self.quantity} {self.unit}>"
        )

class PantryItem(db.Model):  # type: ignore[name-defined]
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
