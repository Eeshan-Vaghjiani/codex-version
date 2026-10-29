"""Store symptom states and follow-up evidence without rewriting patient text.

Revision ID: d42ea86c5170
Revises: a3f1c9d27b64
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd42ea86c5170'
down_revision = 'a3f1c9d27b64'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('prediction_sessions', sa.Column(
        'assessment_context', postgresql.JSONB(), nullable=False,
        server_default=sa.text("'{}'::jsonb")))


def downgrade():
    op.drop_column('prediction_sessions', 'assessment_context')
