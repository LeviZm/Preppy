"""add meal_plans, shopping_lists, shopping_list_items

Revision ID: a1b2c3d4e5f6
Revises: 8ace4122a35c
Create Date: 2026-05-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '8ace4122a35c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'meal_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('planned_date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.String(length=30), nullable=False),
        sa.Column('servings', sa.Integer(), nullable=False),
        sa.Column('notes', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'recipe_id', 'planned_date', name='uq_mealplan_user_recipe_date'),
    )
    op.create_index('ix_meal_plans_user_id', 'meal_plans', ['user_id'])

    op.create_table(
        'shopping_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('meal_plan_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('is_complete', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shopping_lists_user_id', 'shopping_lists', ['user_id'])

    op.create_table(
        'shopping_list_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shopping_list_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=30), nullable=False),
        sa.Column('is_checked', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['shopping_list_id'], ['shopping_lists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shopping_list_id', 'ingredient_id', name='uq_shoppingitem_list_ingredient'),
    )


def downgrade():
    op.drop_table('shopping_list_items')
    op.drop_index('ix_shopping_lists_user_id', table_name='shopping_lists')
    op.drop_table('shopping_lists')
    op.drop_index('ix_meal_plans_user_id', table_name='meal_plans')
    op.drop_table('meal_plans')
