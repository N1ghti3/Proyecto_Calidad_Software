"""ADR-010 / RN-25 / CP-82 — el rol de la aplicación tiene solo lo que necesita.

La auditoría es de solo anexado **en el motor**, no por costumbre del código:
si la aplicación tuviera un defecto que intentara corregir un registro, la base
debe impedirlo.
"""

from __future__ import annotations

import psycopg
import pytest

from apoyo import crear_variante


def _registro_de_auditoria(conn) -> str:
    variante = crear_variante(conn, stock=1)
    return conn.execute(
        "INSERT INTO audit_log (entity_type, entity_id, action, source, new_value) "
        "VALUES ('INVENTORY', %s, 'STOCK_CHANGE', 'ORDEN', '0') RETURNING id",
        (variante.id,),
    ).fetchone()[0]


def _rechazado_por_privilegios(conn, sql, params=None):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with conn.transaction():
            conn.execute(sql, params)


def test_la_aplicacion_puede_insertar_y_leer_auditoria(bd):
    registro = _registro_de_auditoria(bd)
    leido = bd.execute("SELECT id FROM audit_log WHERE id = %s", (registro,)).fetchone()
    assert leido is not None


def test_rn25_la_aplicacion_no_puede_modificar_la_auditoria(bd):
    registro = _registro_de_auditoria(bd)
    _rechazado_por_privilegios(
        bd, "UPDATE audit_log SET new_value = 'alterado' WHERE id = %s", (registro,)
    )


def test_rn25_la_aplicacion_no_puede_borrar_la_auditoria(bd):
    registro = _registro_de_auditoria(bd)
    _rechazado_por_privilegios(bd, "DELETE FROM audit_log WHERE id = %s", (registro,))


def test_la_aplicacion_no_puede_cambiar_el_esquema(bd):
    _rechazado_por_privilegios(bd, "CREATE TABLE tabla_intrusa (id int)")


def test_la_aplicacion_no_puede_alterar_la_version_del_esquema(bd):
    version = bd.execute("SELECT version_num FROM alembic_version").fetchone()
    assert version is not None
    _rechazado_por_privilegios(bd, "UPDATE alembic_version SET version_num = 'falsa'")


def test_la_aplicacion_no_es_superusuario(bd):
    es_superusuario = bd.execute(
        "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
    ).fetchone()[0]
    assert es_superusuario is False
