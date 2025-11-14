"""remove contacto column from cliente

Revision ID: 2b5ef8c77a86
Revises: 7fa9c61d3b4e
Create Date: 2025-11-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b5ef8c77a86'
down_revision = '7fa9c61d3b4e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('cliente', schema=None) as batch_op:
        batch_op.drop_column('contacto')


def downgrade():
    with op.batch_alter_table('cliente', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contacto', sa.String(length=255), nullable=True))
