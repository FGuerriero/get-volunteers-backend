"""Add volunteer_need_matches table and relationships

Revision ID: 8f08437c10c0
Revises: b4045e62ef80
Create Date: 2025-07-15 11:57:27.351262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f08437c10c0'
down_revision: Union[str, None] = 'b4045e62ef80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('volunteer_need_matches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('volunteer_id', sa.Integer(), nullable=False),
    sa.Column('need_id', sa.Integer(), nullable=False),
    sa.Column('match_details', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['need_id'], ['needs.id'], ),
    sa.ForeignKeyConstraint(['volunteer_id'], ['volunteers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_volunteer_need_matches_id'), 'volunteer_need_matches', ['id'], unique=False)
    

def downgrade() -> None:
    op.drop_index(op.f('ix_volunteer_need_matches_id'), table_name='volunteer_need_matches')
    op.drop_table('volunteer_need_matches')
    