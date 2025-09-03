"""Add is_manager field to volunteers table

Revision ID: 11c9bb1d4386
Revises: 8f08437c10c0
Create Date: 2025-09-03 14:03:50.983817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11c9bb1d4386'
down_revision: Union[str, None] = '8f08437c10c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('volunteers', sa.Column('is_manager', sa.Integer(), nullable=False, server_default='0'))
    

def downgrade() -> None:
    op.drop_column('volunteers', 'is_manager')
