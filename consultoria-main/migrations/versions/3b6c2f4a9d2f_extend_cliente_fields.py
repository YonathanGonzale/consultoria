"""extend cliente fields and documents

Revision ID: 3b6c2f4a9d2f
Revises: aaa4a27f5e8e
Create Date: 2025-09-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b6c2f4a9d2f'
down_revision = 'aaa4a27f5e8e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cliente', sa.Column('cedula_identidad', sa.String(length=100), nullable=True))
    op.add_column('cliente', sa.Column('telefono', sa.String(length=100), nullable=True))
    op.add_column('cliente', sa.Column('correo_electronico', sa.String(length=255), nullable=True))
    op.add_column('cliente', sa.Column('departamento', sa.String(length=150), nullable=True))
    op.add_column('cliente', sa.Column('distrito', sa.String(length=150), nullable=True))
    op.add_column('cliente', sa.Column('lugar', sa.String(length=255), nullable=True))
    op.add_column('cliente', sa.Column('ubicacion_gps', sa.Text(), nullable=True))

    op.create_table(
        'documento_cliente',
        sa.Column('id_documento', sa.Integer(), nullable=False),
        sa.Column('id_cliente', sa.Integer(), nullable=False),
        sa.Column('nombre_original', sa.String(length=255), nullable=True),
        sa.Column('archivo_url', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('uploaded_at', sa.Date(), server_default=sa.func.current_date(), nullable=True),
        sa.ForeignKeyConstraint(['id_cliente'], ['cliente.id_cliente'], ),
        sa.PrimaryKeyConstraint('id_documento')
    )


def downgrade():
    op.drop_table('documento_cliente')
    op.drop_column('cliente', 'ubicacion_gps')
    op.drop_column('cliente', 'lugar')
    op.drop_column('cliente', 'distrito')
    op.drop_column('cliente', 'departamento')
    op.drop_column('cliente', 'correo_electronico')
    op.drop_column('cliente', 'telefono')
    op.drop_column('cliente', 'cedula_identidad')
