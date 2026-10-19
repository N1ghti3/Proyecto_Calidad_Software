"""esquema inicial: once tablas, extensiones, semilla de tallas y rol de aplicación

Revisión: f8ae0dea87a7
Revisión anterior: ninguna. Esta es la primera.
Fecha: 2026-09-27

Crea el esquema completo descrito en `docs/arquitectura/modelo-relacional.md`.

El cuerpo de las tablas se autogeneró a partir de los modelos de SQLAlchemy y se
revisó a mano, conforme a ADR-009. A esa base se le añadieron cuatro cosas que
la autogeneración no puede conocer, en este orden, porque el orden importa:

1. **Extensiones y la función `f_unaccent()`**, antes de las tablas: el índice
   GIN de `product` la usa, y un índice no puede crearse sobre una función que
   no existe.
2. **La semilla de `size_catalog`**, después de las tablas. Es parte del
   esquema, no de los datos de prueba (ADR-008): sin catálogo sembrado no pueden
   crearse variantes, y una base recién migrada debe quedar utilizable.
3. **El rol `tiendalocal_app`** con sus privilegios, y el `REVOKE` que hace de
   la auditoría una tabla de solo anexado en el motor y no solo en el código
   (ADR-010, RN-25).
4. **La revocación de escritura sobre `alembic_version`**: la aplicación no
   tiene por qué poder mentir sobre en qué versión de esquema está la base.

Requiere la variable de entorno `APP_DB_PASSWORD`, que es la contraseña con la
que se crea el rol de la aplicación. Sin ella la migración se detiene antes de
tocar nada: crear un rol de acceso sin contraseña sería peor que no crearlo.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f8ae0dea87a7"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROL_APP = "tiendalocal_app"

# Semilla del catálogo de tallas (ADR-008).
#
# Las posiciones van de diez en diez a propósito: insertar una talla intermedia
# en el futuro es una fila nueva con una posición libre, no renumerar las siete
# que ya existen. `UNIQUE(position)` no perdona un renumerado a medias.
#
# `ÚNICA` es la talla de los productos de pieza única previstos en ADR-002, y va
# al final porque no pertenece a la escala.
TALLAS_INICIALES: tuple[tuple[str, str, int], ...] = (
    ("XS", "XS", 10),
    ("S", "S", 20),
    ("M", "M", 30),
    ("L", "L", 40),
    ("XL", "XL", 50),
    ("XXL", "XXL", 60),
    ("ÚNICA", "Única", 90),
)


def _contrasena_del_rol_de_aplicacion() -> str:
    """Contraseña del rol de la aplicación, del entorno o del archivo .env.

    Se busca en las dos partes y en este orden, igual que hace `env.py` con la
    URL de conexión: la variable de entorno gana, porque es lo que usa el canal
    de integración continua, y el `.env` de la raíz es el caso normal de trabajo
    en una máquina. Leer solo la variable de entorno obligaría a exportarla a
    mano en cada sesión de terminal, teniendo el valor ya escrito en el `.env`.
    """
    contrasena = os.getenv("APP_DB_PASSWORD")

    if not contrasena:
        try:
            from app.core.config import obtener_settings

            contrasena = obtener_settings().app_db_password
        except Exception:  # pragma: no cover - solo mejora el mensaje de error
            contrasena = None

    if not contrasena:
        raise RuntimeError(
            "Falta APP_DB_PASSWORD. Es la contraseña del rol "
            f"'{ROL_APP}', con el que se conecta la aplicación. Está declarada "
            "en .env.example: copia ese archivo como .env en la raíz del "
            "repositorio y rellénala antes de migrar."
        )
    return contrasena


def _crear_extensiones_y_funcion_de_busqueda() -> None:
    """Instala unaccent y pg_trgm, y declara la envoltura inmutable.

    `unaccent()` no está declarada IMMUTABLE porque depende de un diccionario
    que podría cambiar, y PostgreSQL no indexa funciones que no lo sean. La
    envoltura fija el diccionario en la propia definición y ahí sí la
    inmutabilidad es cierta. Es normalización de texto, no lógica de negocio:
    ADR-001 prohíbe lo segundo, no lo primero.
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
          LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
          AS $$ SELECT public.unaccent('public.unaccent', $1) $$
        """
    )


def _sembrar_catalogo_de_tallas() -> None:
    """Inserta las siete tallas iniciales."""
    tabla = sa.table(
        "size_catalog",
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("position", sa.SmallInteger),
    )
    op.bulk_insert(
        tabla,
        [
            {"code": code, "label": etiqueta, "position": posicion}
            for code, etiqueta, posicion in TALLAS_INICIALES
        ],
    )


def _crear_rol_de_aplicacion() -> None:
    """Crea el rol con el que corre la aplicación y ajusta sus privilegios.

    El rol se crea aquí y no en el `docker-compose.yml` porque sus privilegios
    dependen de que las tablas existan, y las tablas las crea esta migración.

    La contraseña se escapa con `quote_literal()` del propio motor: una sentencia
    DDL no admite parámetros, de modo que el valor tiene que ir incrustado, y
    quien sabe citar una cadena de PostgreSQL es PostgreSQL.
    """
    conexion = op.get_bind()
    contrasena_citada = conexion.execute(
        sa.text("SELECT quote_literal(:valor)"),
        {"valor": _contrasena_del_rol_de_aplicacion()},
    ).scalar_one()

    ya_existe = conexion.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = :rol"), {"rol": ROL_APP}
    ).scalar()

    if ya_existe:
        # El rol vive en el clúster, no en la base: puede sobrevivir a un
        # downgrade de otra base del mismo motor. Se reutiliza en lugar de
        # fallar.
        op.execute(f"ALTER ROLE {ROL_APP} WITH LOGIN PASSWORD {contrasena_citada}")
    else:
        op.execute(f"CREATE ROLE {ROL_APP} WITH LOGIN PASSWORD {contrasena_citada}")

    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROL_APP}")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
        f"TO {ROL_APP}"
    )

    # RN-25: la auditoría es de solo anexado. Esta es la única garantía real;
    # que la aplicación no exponga la operación es una costumbre, no una
    # restricción. CP-82 lo comprueba intentando un UPDATE y esperando el
    # rechazo.
    op.execute(f"REVOKE UPDATE, DELETE ON audit_log FROM {ROL_APP}")

    # La aplicación lee en qué versión de esquema está la base, pero no la
    # escribe. Eso es tarea de Alembic, que se conecta con el propietario.
    op.execute(f"REVOKE ALL ON alembic_version FROM {ROL_APP}")
    op.execute(f"GRANT SELECT ON alembic_version TO {ROL_APP}")

    # Las tablas que creen las migraciones futuras nacen con los mismos
    # privilegios, para que nadie tenga que acordarse de concederlos.
    #
    # ATENCIÓN: esto incluye UPDATE y DELETE. Una migración futura que recree
    # `audit_log` —o que añada otra tabla de solo anexado— debe repetir su
    # REVOKE. La prueba CP-82 es lo que lo detectaría.
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROL_APP}"
    )


def _revocar_privilegios_del_rol_de_aplicacion() -> None:
    """Deja el rol sin privilegios sobre este esquema.

    El rol **no se elimina**: es un objeto del clúster y puede estar en uso por
    otra base del mismo motor. Borrarlo aquí convertiría un downgrade de esta
    base en una caída de otra.
    """
    conexion = op.get_bind()
    existe = conexion.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = :rol"), {"rol": ROL_APP}
    ).scalar()
    if not existe:
        return

    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {ROL_APP}"
    )
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROL_APP}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {ROL_APP}")


def upgrade() -> None:
    # Se valida antes de tocar la base: una migración que crea diez tablas y
    # falla en la undécima deja un esquema a medias.
    _contrasena_del_rol_de_aplicacion()

    _crear_extensiones_y_funcion_de_busqueda()


    # --- Tablas, restricciones e índices (autogenerado y revisado) ---
    op.create_table('admin_user',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('email', sa.String(length=160), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("email ~ '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$'", name=op.f('ck_admin_user_correo_formato')),
    sa.CheckConstraint('email = lower(email)', name=op.f('ck_admin_user_correo_minusculas')),
    sa.CheckConstraint('length(trim(password_hash)) > 0', name=op.f('ck_admin_user_hash_no_vacio')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admin_user')),
    sa.UniqueConstraint('email', name=op.f('uq_admin_user_email'))
    )
    op.create_table('category',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('slug', sa.String(length=90), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("slug ~ '^[a-z0-9-]+$'", name=op.f('ck_category_slug_formato')),
    sa.CheckConstraint('length(name) >= 2', name=op.f('ck_category_nombre_minimo')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_category')),
    sa.UniqueConstraint('name', name=op.f('uq_category_name')),
    sa.UniqueConstraint('slug', name=op.f('uq_category_slug'))
    )
    op.create_table('order_header',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('order_number', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'CONFIRMADA'"), nullable=False),
    sa.Column('total_cop', sa.BigInteger(), nullable=False),
    sa.Column('customer_name', sa.String(length=120), nullable=False),
    sa.Column('customer_email', sa.String(length=160), nullable=False),
    sa.Column('customer_phone', sa.String(length=20), nullable=False),
    sa.Column('shipping_address', sa.String(length=200), nullable=False),
    sa.Column('shipping_city', sa.String(length=80), nullable=False),
    sa.Column('data_processing_consent', sa.Boolean(), nullable=False),
    sa.Column('privacy_notice_version', sa.String(length=20), nullable=False),
    sa.Column('consent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("customer_email ~* '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$'", name=op.f('ck_order_header_correo_formato')),
    sa.CheckConstraint("customer_phone ~ '^[0-9]{7,15}$'", name=op.f('ck_order_header_telefono_formato')),
    sa.CheckConstraint("order_number ~ '^TL-[0-9]{8}-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{5}$'", name=op.f('ck_order_header_numero_formato')),
    sa.CheckConstraint("status IN ('CONFIRMADA', 'PREPARADA', 'ENTREGADA', 'CANCELADA')", name=op.f('ck_order_header_estado_valido')),
    sa.CheckConstraint('data_processing_consent = true', name=op.f('ck_order_header_consentimiento_obligatorio')),
    sa.CheckConstraint('length(trim(customer_name)) > 0', name=op.f('ck_order_header_nombre_no_vacio')),
    sa.CheckConstraint('length(trim(shipping_address)) > 0', name=op.f('ck_order_header_direccion_no_vacia')),
    sa.CheckConstraint('length(trim(shipping_city)) > 0', name=op.f('ck_order_header_ciudad_no_vacia')),
    sa.CheckConstraint('total_cop > 0', name=op.f('ck_order_header_total_positivo')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_header')),
    sa.UniqueConstraint('order_number', name=op.f('uq_order_header_order_number'))
    )
    op.create_index('ix_order_header_customer_email', 'order_header', [sa.literal_column('lower(customer_email)')], unique=False)
    op.create_index('ix_order_header_status_created_at', 'order_header', ['status', sa.literal_column('created_at DESC')], unique=False)
    op.create_table('size_catalog',
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('label', sa.String(length=40), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('code = upper(code)', name=op.f('ck_size_catalog_codigo_mayusculas')),
    sa.CheckConstraint('length(trim(label)) > 0', name=op.f('ck_size_catalog_etiqueta_no_vacia')),
    sa.CheckConstraint('position >= 0', name=op.f('ck_size_catalog_posicion_no_negativa')),
    sa.PrimaryKeyConstraint('code', name=op.f('pk_size_catalog')),
    sa.UniqueConstraint('position', name=op.f('uq_size_catalog_position'))
    )
    op.create_table('audit_log',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('admin_user_id', sa.UUID(), nullable=True),
    sa.Column('entity_type', sa.String(length=30), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=False),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('old_value', sa.String(length=120), nullable=True),
    sa.Column('new_value', sa.String(length=120), nullable=False),
    sa.Column('reason', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("action IN ('STOCK_CHANGE', 'STATUS_CHANGE', 'PUBLISH_CHANGE')", name=op.f('ck_audit_log_accion_valida')),
    sa.CheckConstraint("entity_type IN ('INVENTORY', 'ORDER', 'PRODUCT')", name=op.f('ck_audit_log_entidad_valida')),
    sa.CheckConstraint("source = 'ORDEN' OR reason IS NOT NULL", name=op.f('ck_audit_log_motivo_obligatorio')),
    sa.CheckConstraint("source IN ('AJUSTE_MANUAL', 'ORDEN', 'CANCELACION')", name=op.f('ck_audit_log_origen_valido')),
    sa.CheckConstraint('length(trim(new_value)) > 0', name=op.f('ck_audit_log_valor_nuevo_no_vacio')),
    sa.ForeignKeyConstraint(['admin_user_id'], ['admin_user.id'], name=op.f('fk_audit_log_admin_user_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index('ix_audit_log_created_at', 'audit_log', [sa.literal_column('created_at DESC')], unique=False)
    op.create_index('ix_audit_log_entity_type_entity_id_created_at', 'audit_log', ['entity_type', 'entity_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_table('notification',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('recipient_type', sa.String(length=20), nullable=False),
    sa.Column('recipient', sa.String(length=160), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'PENDIENTE'"), nullable=False),
    sa.Column('attempts', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('last_error', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("recipient ~* '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$'", name=op.f('ck_notification_correo_formato')),
    sa.CheckConstraint("recipient_type IN ('COMPRADOR', 'ADMINISTRADOR')", name=op.f('ck_notification_destinatario_valido')),
    sa.CheckConstraint("status IN ('PENDIENTE', 'ENVIADA', 'FALLIDA')", name=op.f('ck_notification_estado_valido')),
    sa.CheckConstraint('attempts >= 0', name=op.f('ck_notification_intentos_no_negativos')),
    sa.ForeignKeyConstraint(['order_id'], ['order_header.id'], name=op.f('fk_notification_order_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification'))
    )
    op.create_index('ix_notification_order_id', 'notification', ['order_id'], unique=False)
    op.create_index('ix_notification_status', 'notification', ['status'], unique=False)
    op.create_table('product',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('category_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('slug', sa.String(length=140), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price_cop', sa.BigInteger(), nullable=False),
    sa.Column('published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("slug ~ '^[a-z0-9-]+$'", name=op.f('ck_product_slug_formato')),
    sa.CheckConstraint('description IS NULL OR length(description) <= 2000', name=op.f('ck_product_descripcion_maxima')),
    sa.CheckConstraint('length(name) >= 3', name=op.f('ck_product_nombre_minimo')),
    sa.CheckConstraint('price_cop > 0', name=op.f('ck_product_precio_positivo')),
    sa.ForeignKeyConstraint(['category_id'], ['category.id'], name=op.f('fk_product_category_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product')),
    sa.UniqueConstraint('slug', name=op.f('uq_product_slug'))
    )
    op.create_index('idx_product_name_search', 'product',
    [sa.literal_column('lower(f_unaccent(name))')], unique=False,
    postgresql_using='gin',
    postgresql_ops={'lower(f_unaccent(name))': 'gin_trgm_ops'})
    op.create_index('ix_product_category_id', 'product', ['category_id'], unique=False)
    op.create_index('ix_product_published', 'product', ['published'], unique=False)
    op.create_table('product_image',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('alt_text', sa.String(length=160), nullable=False),
    sa.Column('position', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('width', sa.SmallInteger(), nullable=False),
    sa.Column('height', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('height > 0', name=op.f('ck_product_image_alto_positivo')),
    sa.CheckConstraint('length(trim(alt_text)) > 0', name=op.f('ck_product_image_alt_text_no_vacio')),
    sa.CheckConstraint('length(trim(url)) > 0', name=op.f('ck_product_image_url_no_vacia')),
    sa.CheckConstraint('position >= 0', name=op.f('ck_product_image_posicion_no_negativa')),
    sa.CheckConstraint('width > 0', name=op.f('ck_product_image_ancho_positivo')),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk_product_image_product_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_image')),
    sa.UniqueConstraint('product_id', 'position', name='uq_product_image_product_id_position')
    )
    op.create_index('ix_product_image_product_id', 'product_image', ['product_id'], unique=False)
    op.create_table('product_variant',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('sku', sa.String(length=40), nullable=False),
    sa.Column('size', sa.String(length=20), nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("sku ~ '^[A-Z0-9-]+$'", name=op.f('ck_product_variant_sku_formato')),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk_product_variant_product_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['size'], ['size_catalog.code'], name=op.f('fk_product_variant_size'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_variant')),
    sa.UniqueConstraint('product_id', 'size', name='uq_product_variant_product_id_size'),
    sa.UniqueConstraint('sku', name=op.f('uq_product_variant_sku'))
    )
    op.create_index('ix_product_variant_product_id', 'product_variant', ['product_id'], unique=False)
    op.create_index('ix_product_variant_size', 'product_variant', ['size'], unique=False)
    op.create_table('inventory',
    sa.Column('variant_id', sa.UUID(), nullable=False),
    sa.Column('stock_quantity', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('stock_quantity >= 0', name=op.f('ck_inventory_stock_no_negativo')),
    sa.ForeignKeyConstraint(['variant_id'], ['product_variant.id'], name=op.f('fk_inventory_variant_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('variant_id', name=op.f('pk_inventory'))
    )
    op.create_table('order_item',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('variant_id', sa.UUID(), nullable=False),
    sa.Column('product_name', sa.String(length=120), nullable=False),
    sa.Column('size', sa.String(length=20), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price_cop', sa.BigInteger(), nullable=False),
    sa.Column('line_total_cop', sa.BigInteger(), nullable=False),
    sa.CheckConstraint('line_total_cop = quantity * unit_price_cop', name=op.f('ck_order_item_total_linea_coherente')),
    sa.CheckConstraint('quantity > 0', name=op.f('ck_order_item_cantidad_positiva')),
    sa.CheckConstraint('unit_price_cop > 0', name=op.f('ck_order_item_precio_positivo')),
    sa.ForeignKeyConstraint(['order_id'], ['order_header.id'], name=op.f('fk_order_item_order_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['variant_id'], ['product_variant.id'], name=op.f('fk_order_item_variant_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_item')),
    sa.UniqueConstraint('order_id', 'variant_id', name='uq_order_item_order_id_variant_id')
    )
    op.create_index('ix_order_item_order_id', 'order_item', ['order_id'], unique=False)

    # --- Semilla del catálogo de tallas (ADR-008) ---
    _sembrar_catalogo_de_tallas()

    # --- Rol de la aplicación y protección de la auditoría (ADR-010) ---
    _crear_rol_de_aplicacion()


def downgrade() -> None:
    # Primero los privilegios: revocarlos después de borrar las tablas sería
    # revocar sobre lo que ya no está.
    _revocar_privilegios_del_rol_de_aplicacion()

    # --- Tablas e índices, en orden inverso de dependencias ---
    op.drop_index('ix_order_item_order_id', table_name='order_item')
    op.drop_table('order_item')
    op.drop_table('inventory')
    op.drop_index('ix_product_variant_size', table_name='product_variant')
    op.drop_index('ix_product_variant_product_id', table_name='product_variant')
    op.drop_table('product_variant')
    op.drop_index('ix_product_image_product_id', table_name='product_image')
    op.drop_table('product_image')
    op.drop_index('ix_product_published', table_name='product')
    op.drop_index('ix_product_category_id', table_name='product')
    op.drop_index('idx_product_name_search', table_name='product', postgresql_using='gin')
    op.drop_table('product')
    op.drop_index('ix_notification_status', table_name='notification')
    op.drop_index('ix_notification_order_id', table_name='notification')
    op.drop_table('notification')
    op.drop_index('ix_audit_log_entity_type_entity_id_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_table('size_catalog')
    op.drop_index('ix_order_header_status_created_at', table_name='order_header')
    op.drop_index('ix_order_header_customer_email', table_name='order_header')
    op.drop_table('order_header')
    op.drop_table('category')
    op.drop_table('admin_user')

    # --- Función y extensiones ---
    #
    # La función se va porque la creó esta migración. Las extensiones también:
    # este esquema es el único que las usa, y dejarlas puestas haría que el
    # downgrade no fuera reversible de verdad. Si otro esquema del mismo motor
    # las necesitara, DROP EXTENSION fallaría por dependencia, que es el aviso
    # correcto y no un borrado silencioso.
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS unaccent")
