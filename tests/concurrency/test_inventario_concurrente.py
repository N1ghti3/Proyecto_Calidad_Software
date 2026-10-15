"""RNF-02 / CP-90 — ninguna orden confirmada excede las existencias.

Fuente: `docs/pruebas/pruebas-concurrencia.md`. Riesgo R-03 del PDF: la prueba
se escribe **antes** de implementar la creación de órdenes.

Todavía no existe `POST /api/v1/orders`, así que estas pruebas ejecutan en la
base la transacción que describe ADR-005, con el rol de la aplicación y
conexiones simultáneas reales. Verifican que el mecanismo elegido funciona en
este motor. Cuando exista el servicio, `comprar()` se sustituye por la llamada a
la API y las aserciones siguen siendo las mismas.

El último caso es un **control negativo**: la misma compra sin bloqueo de fila.
Debe producir sobreventa. Si no la produjera, la prueba no estaría generando
concurrencia real y los verdes de las demás no demostrarían nada.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import psycopg
import pytest

from apoyo import Variante, conectar, crear_variante, nuevo_numero_orden, DATOS_COMPRADOR

CONFIRMADA = "CONFIRMADA"
SIN_STOCK = "SIN_STOCK"


@dataclass(frozen=True)
class Linea:
    variante: Variante
    cantidad: int


# ----------------------------------------------------------------- arnés


def comprar(conn: psycopg.Connection, lineas: list[Linea]) -> str:
    """Transacción de ADR-005, tal como la describe modelo-relacional.md.

    1. Bloquear las filas de inventario, ordenadas por variant_id (RN-10).
    2. Verificar todas las líneas; si alguna no alcanza, revertir (RN-11).
    3. Descontar, crear la orden y sus líneas, auditar (RN-08, RN-24).
    """
    por_variante = {l.variante.id: l for l in lineas}
    with conn.transaction():
        bloqueadas = conn.execute(
            "SELECT variant_id, stock_quantity FROM inventory "
            "WHERE variant_id = ANY(%s) ORDER BY variant_id FOR UPDATE",
            (list(por_variante),),
        ).fetchall()
        stock = dict(bloqueadas)

        if any(stock[vid] < linea.cantidad for vid, linea in por_variante.items()):
            raise _SinStock

        total = sum(l.cantidad * l.variante.precio_cop for l in lineas)
        orden_id = conn.execute(
            "INSERT INTO order_header (order_number, total_cop, data_processing_consent, "
            "privacy_notice_version, customer_name, customer_email, customer_phone, "
            "shipping_address, shipping_city) "
            "VALUES (%(numero)s, %(total)s, true, '1.0', %(customer_name)s, "
            "%(customer_email)s, %(customer_phone)s, %(shipping_address)s, "
            "%(shipping_city)s) RETURNING id",
            {"numero": nuevo_numero_orden(), "total": total, **DATOS_COMPRADOR},
        ).fetchone()[0]

        for vid in sorted(por_variante):
            linea = por_variante[vid]
            anterior = stock[vid]
            nuevo = anterior - linea.cantidad
            conn.execute(
                "UPDATE inventory SET stock_quantity = %s, updated_at = now() "
                "WHERE variant_id = %s",
                (nuevo, vid),
            )
            conn.execute(
                "INSERT INTO order_item (order_id, variant_id, product_name, size, "
                "quantity, unit_price_cop, line_total_cop) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (orden_id, vid, linea.variante.nombre_producto, linea.variante.talla,
                 linea.cantidad, linea.variante.precio_cop,
                 linea.cantidad * linea.variante.precio_cop),
            )
            conn.execute(
                "INSERT INTO audit_log (entity_type, entity_id, action, source, "
                "old_value, new_value) VALUES ('INVENTORY', %s, 'STOCK_CHANGE', "
                "'ORDEN', %s, %s)",
                (vid, str(anterior), str(nuevo)),
            )
    return CONFIRMADA


def comprar_sin_bloqueo(conn: psycopg.Connection, variante: Variante) -> str:
    """CONTROL NEGATIVO: lee y escribe sin bloquear la fila.

    Es el defecto que ADR-005 existe para evitar (actualización perdida). La
    pausa entre leer y escribir garantiza que las solicitudes se solapen.
    """
    with conn.transaction():
        leido = conn.execute(
            "SELECT stock_quantity FROM inventory WHERE variant_id = %s", (variante.id,)
        ).fetchone()[0]
        if leido < 1:
            raise _SinStock
        time.sleep(0.05)
        conn.execute(
            "UPDATE inventory SET stock_quantity = %s WHERE variant_id = %s",
            (leido - 1, variante.id),
        )
    return CONFIRMADA


class _SinStock(Exception):
    """Rechazo esperado: la transacción ya se revirtió al salir del bloque."""


def lanzar_simultaneas(url_app: str, solicitudes: int, operacion) -> Counter:
    """Ejecuta `operacion(conn)` desde `solicitudes` conexiones a la vez.

    Cada hilo abre su conexión **antes** de la barrera, de modo que todos
    empiezan a la vez y no en el orden en que lograron conectarse. Cualquier
    excepción distinta del rechazo esperado se cuenta como error (aserción A9:
    una respuesta 500 invalida la prueba aunque los números cuadren).
    """
    barrera = threading.Barrier(solicitudes)

    def _una():
        with conectar(url_app, autocommit=True) as conn:
            barrera.wait(timeout=30)
            try:
                return operacion(conn)
            except _SinStock:
                return SIN_STOCK
            except Exception as error:  # noqa: BLE001 - se informa en la aserción
                return f"ERROR {type(error).__name__}: {error}"

    with ThreadPoolExecutor(max_workers=solicitudes) as ejecutor:
        return Counter(ejecutor.map(lambda _: _una(), range(solicitudes)))


# ---------------------------------------------------------------- apoyo


@pytest.fixture
def preparar(base_sesion):
    """Crea y CONFIRMA variantes: las otras conexiones deben verlas."""
    def _crear(*stocks: int) -> list[Variante]:
        with conectar(base_sesion.url_app) as conn:
            variantes = [crear_variante(conn, stock=s) for s in stocks]
            conn.commit()
        return variantes
    return _crear


def _stock(url, variante: Variante) -> int:
    with conectar(url) as conn:
        return conn.execute(
            "SELECT stock_quantity FROM inventory WHERE variant_id = %s", (variante.id,)
        ).fetchone()[0]


def _consultar(url, sql, params) -> int:
    with conectar(url) as conn:
        return conn.execute(sql, params).fetchone()[0]


def _sin_errores(resultado: Counter) -> None:
    errores = {k: v for k, v in resultado.items() if k.startswith("ERROR")}
    assert not errores, f"Respuestas no controladas (A9): {errores}"


# ---------------------------------------------------------------- casos


def test_cp90_cincuenta_solicitudes_sobre_diez_unidades(base_sesion, preparar):
    """Escenario de referencia del PDF: 10 confirmadas, 40 rechazadas, stock 0."""
    (variante,) = preparar(10)
    url = base_sesion.url_app

    resultado = lanzar_simultaneas(url, 50, lambda c: comprar(c, [Linea(variante, 1)]))

    _sin_errores(resultado)                                    # A9
    assert resultado[CONFIRMADA] == 10                         # A1
    assert resultado[SIN_STOCK] == 40                          # A2
    assert _stock(url, variante) == 0                          # A3, A4

    ordenes = _consultar(
        url, "SELECT count(DISTINCT order_id) FROM order_item WHERE variant_id = %s",
        (variante.id,),
    )
    unidades = _consultar(
        url, "SELECT coalesce(sum(quantity), 0) FROM order_item WHERE variant_id = %s",
        (variante.id,),
    )
    auditorias = _consultar(
        url, "SELECT count(*) FROM audit_log WHERE entity_id = %s AND source = 'ORDEN'",
        (variante.id,),
    )
    assert ordenes == 10                                       # A5
    assert unidades == 10                                      # A6
    assert 10 == _stock(url, variante) + unidades              # A7, conservación
    assert auditorias == 10                                    # A8


def test_cp90_2_solicitudes_de_tres_unidades(base_sesion, preparar):
    (variante,) = preparar(10)
    url = base_sesion.url_app

    resultado = lanzar_simultaneas(url, 20, lambda c: comprar(c, [Linea(variante, 3)]))

    _sin_errores(resultado)
    assert resultado[CONFIRMADA] == 3
    assert resultado[SIN_STOCK] == 17
    assert _stock(url, variante) == 1


def test_cp90_3_producto_agotado(base_sesion, preparar):
    (variante,) = preparar(0)
    url = base_sesion.url_app

    resultado = lanzar_simultaneas(url, 30, lambda c: comprar(c, [Linea(variante, 1)]))

    _sin_errores(resultado)
    assert resultado == Counter({SIN_STOCK: 30})
    assert _stock(url, variante) == 0


def test_cp90_4_orden_de_dos_lineas_es_todo_o_nada(base_sesion, preparar):
    """Nunca se descuenta una línea sin la otra (RN-11)."""
    abundante, escasa = preparar(10, 3)
    url = base_sesion.url_app

    resultado = lanzar_simultaneas(
        url, 20, lambda c: comprar(c, [Linea(abundante, 1), Linea(escasa, 1)])
    )

    _sin_errores(resultado)
    assert resultado[CONFIRMADA] == 3
    assert _stock(url, escasa) == 0
    # Si alguna orden rechazada hubiera descontado la línea abundante, aquí
    # quedarían menos de 7.
    assert _stock(url, abundante) == 7


def test_cp90_5_ordenes_cruzadas_no_producen_interbloqueo(base_sesion, preparar):
    """La mitad pide [A, B] y la otra mitad [B, A] (RN-10).

    Como el bloqueo sigue el orden de variant_id y no el de la petición, nunca
    hay dos transacciones esperándose mutuamente. Un interbloqueo aparecería
    como `ERROR DeadlockDetected`.
    """
    a, b = preparar(20, 20)
    url = base_sesion.url_app
    turno = iter(range(1000))
    candado = threading.Lock()

    def _cruzada(conn):
        with candado:
            par = next(turno) % 2 == 0
        lineas = [Linea(a, 1), Linea(b, 1)] if par else [Linea(b, 1), Linea(a, 1)]
        return comprar(conn, lineas)

    resultado = lanzar_simultaneas(url, 30, _cruzada)

    _sin_errores(resultado)
    assert resultado[CONFIRMADA] == 20
    assert _stock(url, a) == 0 and _stock(url, b) == 0


def test_control_negativo_sin_bloqueo_hay_sobreventa(base_sesion, preparar):
    """Sin `FOR UPDATE`, las 50 solicitudes leen 10 y todas «confirman».

    Esta prueba pasa cuando el defecto SE PRODUCE. Es la evidencia de que el
    arnés genera concurrencia real y de que el bloqueo es lo que la controla.
    """
    (variante,) = preparar(10)
    url = base_sesion.url_app

    resultado = lanzar_simultaneas(url, 50, lambda c: comprar_sin_bloqueo(c, variante))

    _sin_errores(resultado)
    confirmadas = resultado[CONFIRMADA]
    assert confirmadas > 10, "sin bloqueo debería haber sobreventa"
    # La conservación se rompe: se «vendieron» más unidades de las que bajó el stock.
    assert _stock(url, variante) + confirmadas != 10
