# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

"""create initial tables

Revision ID: c99360b2d9e7
Revises: 
Create Date: 2025-07-04 11:22:11.555271

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c99360b2d9e7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "needs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_tasks", sa.Text(), nullable=True),
        sa.Column("required_skills", sa.Text(), nullable=True),
        sa.Column("num_volunteers_needed", sa.Integer(), nullable=False),
        sa.Column(
            "format",
            sa.Enum("in-person", "virtual", name="need_format"),
            nullable=False,
        ),
        sa.Column("location_details", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_needs_id"), "needs", ["id"], unique=False)
    op.create_table(
        "volunteers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("about_me", sa.Text(), nullable=True),
        sa.Column("skills", sa.Text(), nullable=True),
        sa.Column("volunteer_interests", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("availability", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_volunteers_email"), "volunteers", ["email"], unique=True)
    op.create_index(op.f("ix_volunteers_id"), "volunteers", ["id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_volunteers_id"), table_name="volunteers")
    op.drop_index(op.f("ix_volunteers_email"), table_name="volunteers")
    op.drop_table("volunteers")
    op.drop_index(op.f("ix_needs_id"), table_name="needs")
    op.drop_table("needs")
    # ### end Alembic commands ###
