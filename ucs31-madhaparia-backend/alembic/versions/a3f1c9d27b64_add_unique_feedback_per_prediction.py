"""add unique feedback per prediction

Revision ID: a3f1c9d27b64
Revises: b686b7b5730a
Create Date: 2026-10-09 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9d27b64'
down_revision: Union[str, Sequence[str], None] = 'b686b7b5730a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        'uq_feedback_prediction_session_id',
        'feedback',
        ['prediction_session_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'uq_feedback_prediction_session_id',
        'feedback',
        type_='unique',
    )
