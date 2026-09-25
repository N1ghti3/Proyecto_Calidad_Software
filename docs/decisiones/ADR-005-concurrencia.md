# ADR-005 — Control de concurrencia: bloqueo pesimista de fila más restricción `CHECK`

- **Estado:** Aceptada
- **Fecha:** 2026-09-25
- **Decide:** Hedixon Cardozo (backend) y Jhon Ortiz (calidad), con acuerdo del equipo
- **Respaldo en el PDF:** apartado 9.3 — «base de datos relacional con transacciones ACID y **bloqueo a nivel de fila** sobre el registro de existencias»; RNF-02 y subpregunta SP-1. El **orden determinista de bloqueo**, la restricción `CHECK` y la respuesta detallada son `DECISIÓN PROPUESTA`.

## Contexto

Es la decisión más importante del proyecto. RNF-02 exige que, con 10 unidades y 50 solicitudes simultáneas, se confirmen exactamente 10 órdenes, se rechacen 40 y el stock final sea 0. El PDF lo trata además como condición de cumplimiento legal (Ley 1480 de 2011, información veraz de disponibilidad).

Sin control de concurrencia, dos transacciones leen el mismo valor de existencias antes de que cualquiera lo modifique y ambas confirman (actualización perdida).

## Alternativas consideradas

1. **Bloqueo pesimista de fila** (`SELECT … FOR UPDATE` sobre `inventory`) dentro de la transacción.
2. **Actualización condicional atómica** (`UPDATE inventory SET stock_quantity = stock_quantity - :n WHERE variant_id = :id AND stock_quantity >= :n`, verificando filas afectadas).
3. **Bloqueo optimista** con columna de versión y reintento.
4. **Nivel de aislamiento `SERIALIZABLE`** para toda la transacción.

| Criterio | A1 pesimista | A2 condicional | A3 optimista | A4 serializable |
| --- | --- | --- | --- | --- |
| Respaldo explícito en el PDF | **Sí** | No | No | No |
| Correcto con órdenes de varias líneas | Sí | Sí, con cuidado | Sí, con reintentos | Sí |
| Complejidad de implementación | Baja | Baja | Media (bucle de reintento) | Baja |
| Comportamiento con 50 solicitudes | Serializa, espera acotada | Serializa por fila | Muchos reintentos | Muchos abortos por serialización |
| Facilidad de explicar el rechazo al comprador | Alta | Alta | Media | Baja |
| Riesgo de interbloqueo | Existe si el orden de bloqueo varía | Menor | Bajo | Existe |

A3 y A4 fueron descartadas porque, con 50 solicitudes sobre la misma fila, generan reintentos o abortos que se traducirían en respuestas 500 y en tiempos impredecibles: la aserción A9 de CP-90 exige que las 40 rechazadas reciban `INSUFFICIENT_STOCK`, no un error de servidor.

## Decisión

Combinación de bloqueo pesimista con defensa en profundidad:

1. **Bloqueo de fila** sobre `inventory` de todas las variantes de la orden, dentro de la transacción, **ordenadas por `variant_id` ascendente** para evitar interbloqueos cuando dos órdenes comparten variantes en distinto orden.
2. **Verificación línea por línea** de `stock_quantity >= quantity`; si alguna falla, `ROLLBACK` completo y respuesta `409 INSUFFICIENT_STOCK` con el detalle de las líneas afectadas y sus unidades disponibles (RN-11).
3. **Descuento, creación de la orden y registro de auditoría** dentro de la misma transacción.
4. **Restricción `CHECK (stock_quantity >= 0)`** en la tabla como última línea de defensa: si un futuro cambio de código omitiera la verificación, la base de datos rechazaría la escritura.
5. **Nivel de aislamiento:** el predeterminado de PostgreSQL (`READ COMMITTED`), suficiente porque el bloqueo explícito serializa el acceso a las filas relevantes.
6. **Notificaciones fuera de la transacción**, después del `COMMIT` (RN-14, RN-15): una llamada al servicio de correo dentro de la transacción mantendría el bloqueo durante una operación de red.

Secuencia completa en [`../arquitectura/modelo-relacional.md`](../arquitectura/modelo-relacional.md#transacción-crítica-rnf-02--descripción-no-implementación).

## Consecuencias

**Positivas**

- Es el mecanismo que el PDF nombra explícitamente: la decisión no introduce divergencia con el documento.
- El rechazo es determinista y explicable: el comprador recibe qué línea falló y cuántas unidades quedan.
- La restricción `CHECK` hace que el inventario negativo sea imposible incluso ante un error de programación.
- La transacción es corta: bloquea, verifica, descuenta y confirma, sin operaciones de red en medio.

**Negativas / riesgos**

- Las solicitudes sobre la misma variante se serializan: con mucha concurrencia crece el tiempo de espera. Para el volumen de un micronegocio es aceptable, y CP-90 mide el comportamiento real.
- Un bloqueo mal acotado (por ejemplo, bloquear toda la tabla) degradaría el rendimiento: la revisión cruzada del código de la transacción es obligatoria (riesgo R-03).
- Si el orden de bloqueo no se respeta, aparecen interbloqueos: se verifica con CP-90.5.

## Verificación

| Aserción | Caso |
| --- | --- |
| 10 confirmadas / 40 rechazadas / stock 0 | CP-90 |
| Ninguna respuesta 500 | CP-90 (A9) |
| Sin interbloqueos con órdenes cruzadas | CP-90.5 |
| Órdenes multilínea: todo o nada | CP-90.4, CP-23 |
| Invariante `stock_inicial = stock_final + confirmadas` | CP-90 (A7) |
| `CHECK` activo | CP-53, CP-90 (A4) |

La prueba se escribe **antes** de implementar la funcionalidad y se ejecuta en cada integración (riesgo R-03).
