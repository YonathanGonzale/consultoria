"""update project state enum to en_proceso/licencia_emitida

Revision ID: c4b9215bd3a2
Revises: 2b5ef8c77a86
Create Date: 2025-11-12 00:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'c4b9215bd3a2'
down_revision = '2b5ef8c77a86'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    enum_info = bind.execute(
        text(
            """
            SELECT udt_name, udt_schema
            FROM information_schema.columns
            WHERE table_name = 'proyecto' AND column_name = 'estado'
            LIMIT 1
            """
        )
    ).fetchone()

    if not enum_info:
        raise RuntimeError("No se pudo determinar el tipo ENUM actual de proyecto.estado")

    enum_name = enum_info.udt_name
    enum_schema = enum_info.udt_schema
    new_enum_name = f"{enum_name}_new"

    def quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def qualify(name: str) -> str:
        if enum_schema and enum_schema != 'public':
            return f"{quote(enum_schema)}.{quote(name)}"
        return quote(name)

    qualified_enum = qualify(enum_name)
    qualified_new_enum = qualify(new_enum_name)

    # Ensure the new label exists on the current enum before updating data.
    with op.get_context().autocommit_block():
        op.execute(
            text(f"ALTER TYPE {qualified_enum} ADD VALUE IF NOT EXISTS 'licencia_emitida'")
        )

    # Normalize data to the new set of labels.
    op.execute(
        text(
            "UPDATE proyecto SET estado = 'licencia_emitida' WHERE estado = 'finalizado'"
        )
    )
    op.execute(
        text("UPDATE proyecto SET estado = 'en_proceso' WHERE estado = 'pendiente'")
    )

    # Drop default temporarily.
    op.execute(text("ALTER TABLE proyecto ALTER COLUMN estado DROP DEFAULT"))

    new_enum = sa.Enum(
        'en_proceso',
        'licencia_emitida',
        name=new_enum_name,
        schema=None if enum_schema == 'public' else enum_schema,
    )
    new_enum.create(bind, checkfirst=True)

    op.execute(
        text(
            f"ALTER TABLE proyecto ALTER COLUMN estado TYPE {qualified_new_enum} "
            f"USING estado::text::{qualified_new_enum}"
        )
    )

    op.execute(text(f"DROP TYPE {qualified_enum}"))

    if enum_schema and enum_schema != 'public':
        op.execute(
            text(
                f"ALTER TYPE {qualified_new_enum} RENAME TO {quote(enum_name)}"
            )
        )
    else:
        op.execute(
            text(
                f"ALTER TYPE {quote(new_enum_name)} RENAME TO {quote(enum_name)}"
            )
        )

    op.execute(
        text("ALTER TABLE proyecto ALTER COLUMN estado SET DEFAULT 'en_proceso'")
    )


def downgrade():
    bind = op.get_bind()

    enum_info = bind.execute(
        text(
            """
            SELECT udt_name, udt_schema
            FROM information_schema.columns
            WHERE table_name = 'proyecto' AND column_name = 'estado'
            LIMIT 1
            """
        )
    ).fetchone()

    if not enum_info:
        raise RuntimeError("No se pudo determinar el tipo ENUM actual de proyecto.estado")

    enum_name = enum_info.udt_name
    enum_schema = enum_info.udt_schema
    old_enum_name = f"{enum_name}_old"

    def quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def qualify(name: str) -> str:
        if enum_schema and enum_schema != 'public':
            return f"{quote(enum_schema)}.{quote(name)}"
        return quote(name)

    qualified_enum = qualify(enum_name)
    qualified_old_enum = qualify(old_enum_name)

    with op.get_context().autocommit_block():
        op.execute(
            text(f"ALTER TYPE {qualified_enum} ADD VALUE IF NOT EXISTS 'finalizado'")
        )

    op.execute(
        text(
            "UPDATE proyecto SET estado = 'finalizado' WHERE estado = 'licencia_emitida'"
        )
    )

    old_enum = sa.Enum(
        'pendiente',
        'en_proceso',
        'finalizado',
        name=old_enum_name,
        schema=None if enum_schema == 'public' else enum_schema,
    )
    old_enum.create(bind, checkfirst=True)

    op.execute(
        text(
            f"ALTER TABLE proyecto ALTER COLUMN estado TYPE {qualified_old_enum} "
            f"USING estado::text::{qualified_old_enum}"
        )
    )

    op.execute(text(f"DROP TYPE {qualified_enum}"))

    if enum_schema and enum_schema != 'public':
        op.execute(
            text(
                f"ALTER TYPE {qualified_old_enum} RENAME TO {quote(enum_name)}"
            )
        )
    else:
        op.execute(
            text(
                f"ALTER TYPE {quote(old_enum_name)} RENAME TO {quote(enum_name)}"
            )
        )

    op.execute(
        text("ALTER TABLE proyecto ALTER COLUMN estado SET DEFAULT 'pendiente'")
    )
