"""baseline existing schema

Revision ID: cbf545f55898
Revises: 
Create Date: 2026-10-02 19:54:08.013829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cbf545f55898'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Creates the two tables that existed before Alembic was
    introduced. Each table is only created when it is missing,
    so a database that already contains them is left untouched.
    """
    existing_tables = sa.inspect(op.get_bind()).get_table_names()

    if 'prediction_sessions' not in existing_tables:
        op.create_table('prediction_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('sex', sa.String(length=1), nullable=False),
        sa.Column('input_text', sa.Text(), nullable=False),
        sa.Column('confirmed_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('has_red_flag', sa.Boolean(), nullable=False),
        sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )

    if 'feedback' not in existing_tables:
        op.create_table('feedback',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('prediction_session_id', sa.UUID(), nullable=False),
        sa.Column('was_helpful', sa.Boolean(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['prediction_session_id'], ['prediction_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    """Downgrade schema.

    The baseline tables may pre-date Alembic and hold real
    records, so they are deliberately not dropped here.
    """
    pass
