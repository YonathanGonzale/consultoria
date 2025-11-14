"""add dashboard alert columns to proyecto

Revision ID: e1b2c3d4e5f6
Revises: c4b9215bd3a2
Create Date: 2025-11-13 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1b2c3d4e5f6'
down_revision = 'c4b9215bd3a2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('proyecto', sa.Column('alert_finalized', sa.Boolean(), nullable=True, server_default=sa.false()))
    op.add_column('proyecto', sa.Column('alert_finalized_at', sa.Date(), nullable=True))
    op.add_column('proyecto', sa.Column('alert_finalized_reason', sa.String(length=255), nullable=True))
    op.add_column('proyecto', sa.Column('alert_snoozed_until', sa.Date(), nullable=True))
    op.add_column('proyecto', sa.Column('alert_snooze_reason', sa.String(length=255), nullable=True))

    # opcional: eliminar server_default dejando solo el valor por defecto para nuevas inserciones de la app
    op.alter_column('proyecto', 'alert_finalized', server_default=None)


def downgrade():
    op.drop_column('proyecto', 'alert_snooze_reason')
    op.drop_column('proyecto', 'alert_snoozed_until')
    op.drop_column('proyecto', 'alert_finalized_reason')
    op.drop_column('proyecto', 'alert_finalized_at')
    op.drop_column('proyecto', 'alert_finalized')
