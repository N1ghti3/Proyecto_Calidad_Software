"""ADR-009 / ADR-011 — búsqueda sin tildes y orden alfabético en español.

Estas propiedades dependen de cómo se inicializó el clúster. `docker-compose.yml`
advierte que cambiar la colación sobre un volumen existente «no tiene efecto y
no avisa»: estas pruebas son el aviso.
"""

from __future__ import annotations

from apoyo import crear_variante


def test_adr011_la_base_usa_icu_es_co(bd):
    proveedor, locale = bd.execute(
        "SELECT datlocprovider, daticulocale FROM pg_database "
        "WHERE datname = current_database()"
    ).fetchone()
    assert (proveedor, locale) == ("i", "es-CO")


def test_adr011_el_orden_alfabetico_respeta_las_tildes(bd):
    nombres = ["Zapato", "Bolso", "Éxito", "abrigo", "Ábaco"]
    filas = bd.execute(
        "SELECT n FROM unnest(%s::text[]) AS t(n) ORDER BY n", (nombres,)
    ).fetchall()
    # Por bytes saldría: Bolso, Zapato, abrigo, Ábaco, Éxito.
    assert [f[0] for f in filas] == ["Ábaco", "abrigo", "Bolso", "Éxito", "Zapato"]


def test_adr011_upper_convierte_letras_con_tilde(bd):
    # ck_size_catalog_codigo_mayusculas depende de esto.
    assert bd.execute("SELECT upper('única')").fetchone()[0] == "ÚNICA"


def test_adr009_f_unaccent_es_inmutable(bd):
    # Sin IMMUTABLE no podría usarse en el índice de búsqueda.
    volatilidad = bd.execute(
        "SELECT provolatile FROM pg_proc WHERE proname = 'f_unaccent'"
    ).fetchone()[0]
    assert volatilidad == "i"


def test_adr009_existe_el_indice_gin_de_trigramas(bd):
    definicion = bd.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'idx_product_name_search'"
    ).fetchone()[0]
    assert "USING gin" in definicion
    assert "gin_trgm_ops" in definicion
    assert "f_unaccent" in definicion


def test_ca01_2_la_busqueda_ignora_tildes_y_mayusculas(bd):
    variante = crear_variante(bd, stock=1)
    bd.execute(
        "UPDATE product SET name = 'Camiseta Ñandú Oversize' WHERE id = %s",
        (variante.producto_id,),
    )
    encontrados = bd.execute(
        "SELECT id FROM product "
        "WHERE lower(f_unaccent(name)) LIKE '%%' || lower(f_unaccent(%s)) || '%%'",
        ("CAMISETA nandu",),
    ).fetchall()
    assert (variante.producto_id,) in encontrados
