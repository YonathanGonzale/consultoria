"""expand mades project fields

Revision ID: 7fa9c61d3b4e
Revises: 3b6c2f4a9d2f
Create Date: 2025-09-03 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7fa9c61d3b4e'
down_revision = '3b6c2f4a9d2f'
branch_labels = None
depends_on = None


estado_enum = sa.Enum('pendiente', 'en_proceso', 'finalizado', name='estado_proyecto_enum')


def upgrade():
    # Rename tipo_tramite -> subtipo
    with op.batch_alter_table('proyecto', schema=None) as batch_op:
        batch_op.alter_column('tipo_tramite', new_column_name='subtipo')

    # Add new financial and descriptive fields
    op.add_column('proyecto', sa.Column('anio_inicio', sa.Integer(), nullable=True))
    op.add_column('proyecto', sa.Column('costo_total', sa.Numeric(12, 2), nullable=True))
    op.add_column('proyecto', sa.Column('exp_siam', sa.String(length=120), nullable=True))
    op.add_column('proyecto', sa.Column('factura_archivo_url', sa.Text(), nullable=True))
    op.add_column('proyecto', sa.Column('fecha_emision_licencia', sa.Date(), nullable=True))
    op.add_column('proyecto', sa.Column('fecha_vencimiento_licencia', sa.Date(), nullable=True))
    op.add_column('proyecto', sa.Column('finca', sa.String(length=120), nullable=True))
    op.add_column('proyecto', sa.Column('fraccion', sa.String(length=120), nullable=True))
    op.add_column('proyecto', sa.Column('lote', sa.String(length=120), nullable=True))
    op.add_column('proyecto', sa.Column('manzana', sa.String(length=120), nullable=True))
    op.add_column('proyecto', sa.Column('mapa_archivo_url', sa.Text(), nullable=True))
    op.add_column('proyecto', sa.Column('matricula', sa.String(length=120), nullable=True))
    op.add_column('proyecto', sa.Column('monto_entregado', sa.Numeric(12, 2), nullable=True))
    op.add_column('proyecto', sa.Column('nombre_proyecto', sa.String(length=255), nullable=True))
    op.add_column('proyecto', sa.Column('padron', sa.String(length=120), nullable=True))
    op.add_column('proyecto', sa.Column('porcentaje_entrega', sa.Numeric(5, 2), nullable=True))
    op.add_column('proyecto', sa.Column('saldo_restante', sa.Numeric(12, 2), nullable=True))
    op.add_column('proyecto', sa.Column('superficie', sa.Numeric(12, 2), nullable=True))
    op.add_column('proyecto', sa.Column('lugar', sa.String(length=255), nullable=True))
    op.add_column('proyecto', sa.Column('distrito', sa.String(length=150), nullable=True))
    op.add_column('proyecto', sa.Column('departamento', sa.String(length=150), nullable=True))

    # Ensure estado has valid values before converting to ENUM
    op.execute("UPDATE proyecto SET estado = 'pendiente' WHERE estado IS NULL OR estado = ''")

    bind = op.get_bind()
    estado_enum.create(bind, checkfirst=True)
    op.alter_column(
        'proyecto',
        'estado',
        existing_type=sa.String(length=50),
        type_=estado_enum,
        nullable=False,
        server_default='pendiente',
        postgresql_using="estado::text::estado_proyecto_enum"
    )

    # Update documento_proyecto metadata
    op.add_column('documento_proyecto', sa.Column('categoria', sa.String(length=100), nullable=True))
    op.add_column('documento_proyecto', sa.Column('mime_type', sa.String(length=100), nullable=True))
    op.add_column('documento_proyecto', sa.Column('nombre_original', sa.String(length=255), nullable=True))
    op.add_column('documento_proyecto', sa.Column('uploaded_at', sa.Date(), server_default=sa.func.current_date(), nullable=True))


def downgrade():
    # Revert documento_proyecto metadata
    op.drop_column('documento_proyecto', 'uploaded_at')
    op.drop_column('documento_proyecto', 'nombre_original')
    op.drop_column('documento_proyecto', 'mime_type')
    op.drop_column('documento_proyecto', 'categoria')

    # Revert estado enum
    bind = op.get_bind()
    op.alter_column(
        'proyecto',
        'estado',
        existing_type=estado_enum,
        type_=sa.String(length=50),
        nullable=True,
        server_default=None,
        postgresql_using="estado::text"
    )
    estado_enum.drop(bind, checkfirst=True)

    # Drop newly added columns
    op.drop_column('proyecto', 'lugar')
    op.drop_column('proyecto', 'superficie')
    op.drop_column('proyecto', 'saldo_restante')
    op.drop_column('proyecto', 'porcentaje_entrega')
    op.drop_column('proyecto', 'padron')
    op.drop_column('proyecto', 'nombre_proyecto')
    op.drop_column('proyecto', 'monto_entregado')
    op.drop_column('proyecto', 'matricula')
    op.drop_column('proyecto', 'mapa_archivo_url')
    op.drop_column('proyecto', 'manzana')
    op.drop_column('proyecto', 'lote')
    op.drop_column('proyecto', 'fraccion')
    op.drop_column('proyecto', 'finca')
    op.drop_column('proyecto', 'fecha_vencimiento_licencia')
    op.drop_column('proyecto', 'fecha_emision_licencia')
    op.drop_column('proyecto', 'factura_archivo_url')
    op.drop_column('proyecto', 'exp_siam')
    op.drop_column('proyecto', 'distrito')
    op.drop_column('proyecto', 'departamento')
    op.drop_column('proyecto', 'costo_total')
    op.drop_column('proyecto', 'anio_inicio')

    with op.batch_alter_table('proyecto', schema=None) as batch_op:
        batch_op.alter_column('subtipo', new_column_name='tipo_tramite')
