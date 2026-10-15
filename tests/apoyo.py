"""Utilidades compartidas por las pruebas de base de datos.

Las pruebas hablan con PostgreSQL mediante `psycopg` y SQL explícito, no con los
modelos de SQLAlchemy. Es deliberado: lo que se verifica es **lo que el motor
garantiza por sí solo**. Si una prueba pasara por los modelos, una validación de
Python podría tapar una restricción ausente en la base, y la prueba seguiría en
verde con el esquema roto.
"""

from __future__ import annotations

import argparse
import secrets
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parents[1]
BACKEND = RAIZ / "backend"

ROL_APP = "tiendalocal_app"

# Alfabeto del número de orden (ADR-010): sin 0, 1, I ni O.
ALFABETO_ORDEN = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


# ------------------------------------------------------------------ URLs


def url_de_base(url_admin: str, base: str, usuario: str | None = None,
                contrasena: str | None = None) -> str:
    """URL en formato SQLAlchemy para otra base del mismo clúster."""
    url = make_url(url_admin).set(database=base)
    if usuario is not None:
        url = url.set(username=usuario, password=contrasena)
    return url.render_as_string(hide_password=False)


def para_psycopg(url_sqlalchemy: str) -> str:
    """psycopg no entiende el sufijo `+psycopg` del dialecto de SQLAlchemy."""
    return url_sqlalchemy.replace("postgresql+psycopg://", "postgresql://", 1)


def conectar(url_sqlalchemy: str, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(para_psycopg(url_sqlalchemy), autocommit=autocommit)


# --------------------------------------------------------------- Alembic


def configuracion_alembic(url_owner: str) -> Config:
    """Configuración de Alembic apuntando a una base concreta.

    La URL viaja como `-x url=...`, el mismo mecanismo que `env.py` ofrece al
    canal de integración continua, de modo que nunca se lee el `.env` de quien
    ejecuta las pruebas.
    """
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.cmd_opts = argparse.Namespace(x=[f"url={url_owner}"])
    return cfg


def migrar(url_owner: str, revision: str = "head") -> None:
    command.upgrade(configuracion_alembic(url_owner), revision)


def revertir(url_owner: str, revision: str = "base") -> None:
    command.downgrade(configuracion_alembic(url_owner), revision)


# ----------------------------------------------------------- bases efímeras


@dataclass(frozen=True)
class BaseDePrueba:
    nombre: str
    url_owner: str
    url_app: str


@contextmanager
def base_efimera(url_admin: str, contrasena_app: str,
                 migrada: bool = True) -> Iterator[BaseDePrueba]:
    """Crea una base vacía en el clúster de pruebas y la borra al salir.

    Cada base hereda la colación ICU `es-CO` del clúster (ADR-011), porque
    `CREATE DATABASE` copia la configuración de `template1`.
    """
    nombre = f"tl_prueba_{uuid.uuid4().hex[:10]}"
    with conectar(url_admin, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{nombre}"')
    try:
        base = BaseDePrueba(
            nombre=nombre,
            url_owner=url_de_base(url_admin, nombre),
            url_app=url_de_base(url_admin, nombre, ROL_APP, contrasena_app),
        )
        if migrada:
            migrar(base.url_owner)
        yield base
    finally:
        with conectar(url_admin, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')


# --------------------------------------------------------------- datos


def sufijo_unico() -> str:
    return uuid.uuid4().hex[:8]


def nuevo_numero_orden() -> str:
    """Número de orden válido según ADR-010: TL-AAAAMMDD-XXXXX."""
    fecha = datetime.now(timezone.utc).strftime("%Y%m%d")
    cola = "".join(secrets.choice(ALFABETO_ORDEN) for _ in range(5))
    return f"TL-{fecha}-{cola}"


@dataclass(frozen=True)
class Variante:
    id: uuid.UUID
    producto_id: uuid.UUID
    nombre_producto: str
    talla: str
    precio_cop: int


def crear_variante(conn: psycopg.Connection, stock: int, talla: str = "M",
                   precio_cop: int = 50_000) -> Variante:
    """Crea categoría, producto, variante e inventario con datos únicos.

    No confirma la transacción: decide quien llama. Las pruebas de
    restricciones la revierten; las de concurrencia la confirman para que
    otras conexiones la vean.
    """
    sufijo = sufijo_unico()
    categoria_id = conn.execute(
        "INSERT INTO category (name, slug) VALUES (%s, %s) RETURNING id",
        (f"Categoría {sufijo}", f"categoria-{sufijo}"),
    ).fetchone()[0]
    nombre = f"Producto de prueba {sufijo}"
    producto_id = conn.execute(
        "INSERT INTO product (category_id, name, slug, price_cop, published) "
        "VALUES (%s, %s, %s, %s, true) RETURNING id",
        (categoria_id, nombre, f"producto-{sufijo}", precio_cop),
    ).fetchone()[0]
    variante_id = conn.execute(
        "INSERT INTO product_variant (product_id, sku, size) VALUES (%s, %s, %s) "
        "RETURNING id",
        (producto_id, f"SKU-{sufijo.upper()}-{talla.replace('Ú', 'U')}", talla),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO inventory (variant_id, stock_quantity) VALUES (%s, %s)",
        (variante_id, stock),
    )
    return Variante(variante_id, producto_id, nombre, talla, precio_cop)


DATOS_COMPRADOR = {
    "customer_name": "Compradora de Prueba",
    "customer_email": "compradora@example.com",
    "customer_phone": "3001234567",
    "shipping_address": "Calle 1 # 2-3",
    "shipping_city": "Bogotá D.C.",
}


def insertar_orden(conn: psycopg.Connection, total_cop: int, **cambios) -> uuid.UUID:
    """Inserta una cabecera de orden válida; `cambios` sobrescribe columnas."""
    fila = {
        "order_number": nuevo_numero_orden(),
        "total_cop": total_cop,
        "data_processing_consent": True,
        "privacy_notice_version": "1.0",
        **DATOS_COMPRADOR,
        **cambios,
    }
    columnas = ", ".join(fila)
    marcadores = ", ".join(f"%({c})s" for c in fila)
    return conn.execute(
        f"INSERT INTO order_header ({columnas}) VALUES ({marcadores}) RETURNING id",
        fila,
    ).fetchone()[0]
