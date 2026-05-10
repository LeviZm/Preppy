"""add index on recipes.owner_user_id

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-10 00:00:00.000000

"""
from alembic import op

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_recipes_owner_user_id",
        "recipes",
        ["owner_user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_recipes_owner_user_id", table_name="recipes")
