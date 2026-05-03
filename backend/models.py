"""
SQLAlchemy data models for the Preppy backend.

Recipe names can repeat globally, but must be unique per owner user.
Many-to-many relation between Recipe and Ingredient with quantity/unit.
Household collaboration support so multiple users can share planning context.
"""

from datetime import datetime

from .extensions import db

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    household = db.relationship("Household", back_populates="members")
    user = db.relationship("User", back_populates="household_memberships")

    def __repr__(self) -> str:
        return f"<HouseholdMember h={self.household_id} u={self.user_id}>"

# ----------------------------------------------------------------------
#                Recipe and Ingredient Models
# ----------------------------------------------------------------------

class Recipe(db.Model):
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    owner_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
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

    def __repr__(self) -> str:
        return f"<Recipe {self.id} {self.name}>"


class Ingredient(db.Model):
    """
    Canonical ingredient entity reused across many recipes.
    """

    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    recipe_ingredients = db.relationship(
        "RecipeIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )

    pantry_items = db.relationship(
        "PantryItem",
        back_populates="ingredient",
    )

    def __repr__(self) -> str:
        return f"<Ingredient {self.id} {self.name}>"


class RecipeIngredient(db.Model):
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

# -----------------------------------------------------------------------
#        Future Models (e.g. MealPlan, ShoppingList) would go here
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
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship("User", back_populates="pantry_items")
    ingredient = db.relationship("Ingredient", back_populates="pantry_items")
