"""Adding Password and active flag to Volunteer and update Need ownership

Revision ID: b4045e62ef80
Revises: c99360b2d9e7
Create Date: 2025-07-08 16:34:16.258346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4045e62ef80'
down_revision: Union[str, None] = 'c99360b2d9e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('needs', sa.Column('owner_id', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'needs', 'volunteers', ['owner_id'], ['id'])
    op.add_column('volunteers', sa.Column('password', sa.String(length=255), nullable=False))
    op.add_column('volunteers', sa.Column('is_active', sa.Integer(), nullable=True))
    

def downgrade() -> None:
    op.drop_column('volunteers', 'is_active')
    op.drop_column('volunteers', 'password')
    op.drop_constraint(None, 'needs', type_='foreignkey')
    op.drop_column('needs', 'owner_id')
    