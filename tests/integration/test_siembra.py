"""La siembra de desarrollo deja el catálogo que necesitan las auditorías.

Se ejecuta el guion tal como lo usa el equipo, en un proceso aparte y contra una
base propia: la siembra se niega a correr sobre un catálogo con datos.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from apoyo import RAIZ, conectar
from app.core.seguridad import verificar_contrasena

GUION = RAIZ / "database" / "seeds" / "sembrar_desarrollo.py"
CONTRASENA_ADMIN = "contrasena-de-siembra-de-prueba"


def _sembrar(url_app: str, *argumentos: str) -> subprocess.CompletedProcess:
    entorno = {
        **os.environ,
        "DATABASE_URL": url_app,
        "ADMIN_SEED_PASSWORD": CONTRASENA_ADMIN,
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, str(GUION), *argumentos],
        cwd=RAIZ, env=entorno, capture_output=True, text=True,
        encoding="utf-8", timeout=120,
    )


def _conteos(conn) -> dict[str, int]:
    consultas = {
        "categorias": "SELECT count(*) FROM category",
        "productos": "SELECT count(*) FROM product",
        "publicados": "SELECT count(*) FROM product WHERE published",
        "publicados_con_imagen": (
            "SELECT count(*) FROM product p WHERE p.published "
            "AND EXISTS (SELECT 1 FROM product_image i WHERE i.product_id = p.id)"
        ),
        "variantes_sin_inventario": (
            "SELECT count(*) FROM product_variant v "
            "LEFT JOIN inventory i ON i.variant_id = v.id WHERE i.variant_id IS NULL"
        ),
        "administradores": "SELECT count(*) FROM admin_user",
    }
    return {clave: conn.execute(sql).fetchone()[0] for clave, sql in consultas.items()}


@pytest.fixture(scope="module")
def base_sembrada(url_cluster, contrasena_app):
    from apoyo import base_efimera

    with base_efimera(url_cluster, contrasena_app) as base:
        resultado = _sembrar(base.url_app)
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr
        yield base


def test_deja_el_catalogo_de_demostracion(base_sembrada):
    with conectar(base_sembrada.url_owner) as conn:
        conteos = _conteos(conn)

    assert conteos["categorias"] == 4
    assert conteos["productos"] == 14
    assert conteos["publicados"] == 12
    # Precondición de CP-80 (RNF-01).
    assert conteos["publicados_con_imagen"] == 12
    # ADR-002: toda variante tiene su registro de existencias.
    assert conteos["variantes_sin_inventario"] == 0
    assert conteos["administradores"] == 1


def test_el_administrador_queda_con_hash_argon2id_verificable(base_sembrada):
    with conectar(base_sembrada.url_owner) as conn:
        hash_almacenado = conn.execute("SELECT password_hash FROM admin_user").fetchone()[0]

    assert hash_almacenado.startswith("$argon2id$")
    assert CONTRASENA_ADMIN not in hash_almacenado
    assert verificar_contrasena(CONTRASENA_ADMIN, hash_almacenado)


def test_no_siembra_encima_de_un_catalogo_existente(base_sembrada):
    with conectar(base_sembrada.url_owner) as conn:
        antes = _conteos(conn)

    resultado = _sembrar(base_sembrada.url_app)

    assert resultado.returncode == 1
    with conectar(base_sembrada.url_owner) as conn:
        assert _conteos(conn) == antes


def test_reiniciar_reemplaza_el_catalogo_y_conserva_el_administrador(base_sembrada):
    for _ in range(2):
        resultado = _sembrar(base_sembrada.url_app, "--reiniciar")
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr

    with conectar(base_sembrada.url_owner) as conn:
        conteos = _conteos(conn)
    assert conteos["productos"] == 14
    assert conteos["administradores"] == 1
