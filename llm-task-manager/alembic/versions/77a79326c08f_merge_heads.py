"""merge_heads

Revision ID: 77a79326c08f
Revises: 485a8ea4b3ce, de0411ac2671
Create Date: 2026-02-12 18:02:02.902569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77a79326c08f'
down_revision: Union[str, None] = ('485a8ea4b3ce', 'de0411ac2671')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
