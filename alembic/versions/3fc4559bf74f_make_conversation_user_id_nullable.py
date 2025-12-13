"""make conversation user_id nullable

Revision ID: 3fc4559bf74f
Revises: eb4eedf542c5
Create Date: 2025-12-13 20:28:54.851452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import fastapi_users_db_sqlalchemy

# revision identifiers, used by Alembic.
revision: str = '3fc4559bf74f'
down_revision: Union[str, Sequence[str], None] = 'eb4eedf542c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=fastapi_users_db_sqlalchemy.generics.GUID(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=fastapi_users_db_sqlalchemy.generics.GUID(),
               nullable=False)