"""add_created_at_to_volunteer_need_matches

Revision ID: 3c1e4e2b4f90
Revises: 11c9bb1d4386
Create Date: 2025-09-19 11:09:05.827170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c1e4e2b4f90'
down_revision: Union[str, None] = '11c9bb1d4386'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('volunteer_need_matches', sa.Column('created_at', sa.DateTime(), nullable=True))
    

def downgrade() -> None:
    op.drop_column('volunteer_need_matches', 'created_at')
    