"""SQLAlchemy data models for the Preppy backend."""

from datetime import datetime, timezone

from ..extensions import db

# ----------------------------------------------------------------------
#                Recipe and Ingredient Models
# ----------------------------------------------------------------------

class Recipe(db.Model):  # type: ignore[name-defined]
    """
    A recipe owned by a user and optionally shared in a household.
    """

    __tablename__ = "recipes"
    __table_args__ = (
        db.UniqueConstraint("owner_user_id", "name", name="uq_recipe_owner_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    household_id = db.Column(
        db.Integer,
        db.ForeignKey("households.id", ondelete="SET NULL"),
        nullable=True,
    )

    owner = db.relationship("User", back_populates="recipes")
    household = db.relationship("Household", back_populates="recipes")

    recipe_ingredients = db.relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )

    meal_plans = db.relationship(
        "MealPlan",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Recipe {self.id} {self.name}>"


class Ingredient(db.Model):  # type: ignore[name-defined]
    """
    Canonical ingredient entity reused across many recipes.
    """

    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    recipe_ingredients = db.relationship(
        "RecipeIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )

    pantry_items = db.relationship(
        "PantryItem",
        back_populates="ingredient",
    )

    shopping_list_items = db.relationship(
        "ShoppingListItem",
        back_populates="ingredient",
    )

    def __repr__(self) -> str:
        return f"<Ingredient {self.id} {self.name}>"


class RecipeIngredient(db.Model):  # type: ignore[name-defined]
    """
    Association object with recipe-specific amount/unit metadata.
    """

    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        db.UniqueConstraint("recipe_id", "ingredient_id", name="uq_recipe_ingredient"),
    )

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
    )

    ingredient_id = db.Column(
        db.Integer,
        db.ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    prep_note = db.Column(db.String(150), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    recipe = db.relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = db.relationship("Ingredient", back_populates="recipe_ingredients")

    def __repr__(self) -> str:
        return (
            f"<RecipeIngredient recipe={self.recipe_id} ingredient={self.ingredient_id} "
            f"qty={self.quantity} {self.unit}>"
        )
