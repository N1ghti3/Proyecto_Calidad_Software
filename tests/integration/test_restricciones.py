"""Restricciones del esquema que protegen reglas de negocio.

Cada prueba verifica **qué restricción** rechazó la operación, por su nombre, y
no solo que «algo falló». Un error de otra restricción haría pasar la prueba
mientras la regla que interesa sigue sin protección.

Todas usan el rol de la aplicación y se revierten al terminar.
"""

from __future__ import annotations

import psycopg
import pytest

from apoyo import crear_variante, insertar_orden


def esperar_violacion(conn: psycopg.Connection, restriccion: str, sql: str, params=None):
    """Ejecuta `sql` y comprueba que lo rechaza exactamente `restriccion`.

    `conn.transaction()` abre un punto de guardado: tras el rechazo, la
    conexión sigue utilizable para el resto de la prueba.
    """
    with pytest.raises(psycopg.errors.IntegrityError) as error:
        with conn.transaction():
            conn.execute(sql, params)
    assert error.value.diag.constraint_name == restriccion


# ------------------------------------------------------------- inventario


def test_rn09_el_inventario_no_acepta_valores_negativos(bd):
    variante = crear_variante(bd, stock=2)
    esperar_violacion(
        bd, "ck_inventory_stock_no_negativo",
        "UPDATE inventory SET stock_quantity = stock_quantity - 3 WHERE variant_id = %s",
        (variante.id,),
    )


def test_rn09_descontar_hasta_cero_si_se_permite(bd):
    variante = crear_variante(bd, stock=2)
    bd.execute(
        "UPDATE inventory SET stock_quantity = stock_quantity - 2 WHERE variant_id = %s",
        (variante.id,),
    )
    stock = bd.execute(
        "SELECT stock_quantity FROM inventory WHERE variant_id = %s", (variante.id,)
    ).fetchone()[0]
    assert stock == 0


# ------------------------------------------------------------------ orden


def test_rn16_no_hay_orden_sin_consentimiento(bd):
    esperar_violacion(
        bd, "ck_order_header_consentimiento_obligatorio",
        *_sql_orden(data_processing_consent=False),
    )


@pytest.mark.parametrize("numero", [
    "TL-20261015-00001",   # secuencial: contiene 0 y 1
    "TL-20261015-ABCIO",   # I y O se confunden al dictarlo
    "TL-20261015-abcde",   # minúsculas
    "TL-2026101-ABCDE",    # fecha incompleta
    "TL20261015ABCDE",     # sin separadores
])
def test_adr010_numero_de_orden_con_formato_invalido(bd, numero):
    esperar_violacion(bd, "ck_order_header_numero_formato", *_sql_orden(order_number=numero))


def test_adr010_el_numero_de_orden_es_unico(bd):
    insertar_orden(bd, 50_000, order_number="TL-20261015-ABCDE")
    esperar_violacion(
        bd, "uq_order_header_order_number",
        *_sql_orden(order_number="TL-20261015-ABCDE"),
    )


def test_rn13_estado_fuera_del_ciclo_definido(bd):
    esperar_violacion(bd, "ck_order_header_estado_valido", *_sql_orden(status="PAGADA"))


def test_el_total_de_la_orden_es_positivo(bd):
    esperar_violacion(bd, "ck_order_header_total_positivo", *_sql_orden(total_cop=0))


def test_el_telefono_se_almacena_solo_con_digitos(bd):
    """El esquema exige 7–15 dígitos, sin `+`.

    OJO, integración: `docs/api/modelos.md` acepta `+573001234567` en
    `CustomerRequest.phone`. La API deberá quitar el `+` antes de guardar, o
    esta restricción rechazará pedidos válidos con un error 500.
    """
    esperar_violacion(
        bd, "ck_order_header_telefono_formato", *_sql_orden(customer_phone="+573001234567")
    )


# ------------------------------------------------------- línea de orden


def test_rn28_el_total_de_linea_es_cantidad_por_precio(bd):
    variante = crear_variante(bd, stock=5, precio_cop=40_000)
    orden = insertar_orden(bd, 80_000)
    esperar_violacion(
        bd, "ck_order_item_total_linea_coherente",
        "INSERT INTO order_item (order_id, variant_id, product_name, size, quantity, "
        "unit_price_cop, line_total_cop) VALUES (%s, %s, 'X', 'M', 2, 40000, 70000)",
        (orden, variante.id),
    )


def test_rn29_la_cantidad_de_una_linea_es_positiva(bd):
    variante = crear_variante(bd, stock=5)
    orden = insertar_orden(bd, 50_000)
    esperar_violacion(
        bd, "ck_order_item_cantidad_positiva",
        "INSERT INTO order_item (order_id, variant_id, product_name, size, quantity, "
        "unit_price_cop, line_total_cop) VALUES (%s, %s, 'X', 'M', 0, 50000, 0)",
        (orden, variante.id),
    )


def test_una_variante_aparece_una_sola_vez_por_orden(bd):
    variante = crear_variante(bd, stock=5)
    orden = insertar_orden(bd, 100_000)
    sql = (
        "INSERT INTO order_item (order_id, variant_id, product_name, size, quantity, "
        "unit_price_cop, line_total_cop) VALUES (%s, %s, 'X', 'M', 1, 50000, 50000)"
    )
    bd.execute(sql, (orden, variante.id))
    esperar_violacion(bd, "uq_order_item_order_id_variant_id", sql, (orden, variante.id))


# ------------------------------------------------------------- catálogo


def test_adr008_la_talla_debe_existir_en_el_catalogo(bd):
    variante = crear_variante(bd, stock=1)
    esperar_violacion(
        bd, "fk_product_variant_size",
        "INSERT INTO product_variant (product_id, sku, size) VALUES (%s, 'SKU-XXXL', 'XXXL')",
        (variante.producto_id,),
    )


def test_adr008_una_talla_no_se_repite_en_el_mismo_producto(bd):
    variante = crear_variante(bd, stock=1, talla="M")
    esperar_violacion(
        bd, "uq_product_variant_product_id_size",
        "INSERT INTO product_variant (product_id, sku, size) VALUES (%s, 'SKU-OTRO-M', 'M')",
        (variante.producto_id,),
    )


def test_el_sku_solo_admite_mayusculas_digitos_y_guiones(bd):
    variante = crear_variante(bd, stock=1)
    esperar_violacion(
        bd, "ck_product_variant_sku_formato",
        "INSERT INTO product_variant (product_id, sku, size) VALUES (%s, 'sku-única', 'L')",
        (variante.producto_id,),
    )


def test_el_precio_del_producto_es_positivo(bd):
    variante = crear_variante(bd, stock=1)
    esperar_violacion(
        bd, "ck_product_precio_positivo",
        "UPDATE product SET price_cop = 0 WHERE id = %s", (variante.producto_id,),
    )


def test_rnf03_toda_imagen_lleva_texto_alternativo(bd):
    variante = crear_variante(bd, stock=1)
    esperar_violacion(
        bd, "ck_product_image_alt_text_no_vacio",
        "INSERT INTO product_image (product_id, url, alt_text, width, height) "
        "VALUES (%s, '/media/x.webp', '   ', 800, 800)",
        (variante.producto_id,),
    )


# ------------------------------------------------------ borrado e histórico


def test_rn23_no_se_puede_borrar_una_variante_ya_vendida(bd):
    variante = crear_variante(bd, stock=5)
    orden = insertar_orden(bd, 50_000)
    bd.execute(
        "INSERT INTO order_item (order_id, variant_id, product_name, size, quantity, "
        "unit_price_cop, line_total_cop) VALUES (%s, %s, %s, 'M', 1, 50000, 50000)",
        (orden, variante.id, variante.nombre_producto),
    )
    bd.execute("DELETE FROM inventory WHERE variant_id = %s", (variante.id,))
    esperar_violacion(
        bd, "fk_order_item_variant_id",
        "DELETE FROM product_variant WHERE id = %s", (variante.id,),
    )


def test_borrar_un_producto_sin_variantes_borra_sus_imagenes(bd):
    # product_image es la única relación en cascada: las imágenes no tienen
    # sentido sin su producto.
    variante = crear_variante(bd, stock=0)
    bd.execute(
        "INSERT INTO product_image (product_id, url, alt_text, width, height) "
        "VALUES (%s, '/media/x.webp', 'Vista frontal', 800, 800)",
        (variante.producto_id,),
    )
    bd.execute("DELETE FROM inventory WHERE variant_id = %s", (variante.id,))
    bd.execute("DELETE FROM product_variant WHERE id = %s", (variante.id,))
    bd.execute("DELETE FROM product WHERE id = %s", (variante.producto_id,))

    restantes = bd.execute(
        "SELECT count(*) FROM product_image WHERE product_id = %s", (variante.producto_id,)
    ).fetchone()[0]
    assert restantes == 0


# --------------------------------------------------------------- auditoría


def test_un_ajuste_manual_exige_motivo(bd):
    variante = crear_variante(bd, stock=1)
    esperar_violacion(
        bd, "ck_audit_log_motivo_obligatorio",
        "INSERT INTO audit_log (entity_type, entity_id, action, source, old_value, new_value) "
        "VALUES ('INVENTORY', %s, 'STOCK_CHANGE', 'AJUSTE_MANUAL', '1', '5')",
        (variante.id,),
    )


def test_el_descuento_por_orden_no_exige_motivo(bd):
    variante = crear_variante(bd, stock=1)
    bd.execute(
        "INSERT INTO audit_log (entity_type, entity_id, action, source, old_value, new_value) "
        "VALUES ('INVENTORY', %s, 'STOCK_CHANGE', 'ORDEN', '1', '0')",
        (variante.id,),
    )


# ------------------------------------------------------------------ apoyo


def _sql_orden(**cambios):
    """SQL de una cabecera de orden válida, con columnas sobrescritas."""
    from apoyo import DATOS_COMPRADOR, nuevo_numero_orden

    fila = {
        "order_number": nuevo_numero_orden(),
        "total_cop": 50_000,
        "data_processing_consent": True,
        "privacy_notice_version": "1.0",
        **DATOS_COMPRADOR,
        **cambios,
    }
    columnas = ", ".join(fila)
    marcadores = ", ".join(f"%({c})s" for c in fila)
    return f"INSERT INTO order_header ({columnas}) VALUES ({marcadores})", fila
