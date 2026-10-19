# Pruebas de concurrencia (RNF-02)

Verifican la propiedad central del proyecto: **ninguna orden confirmada puede exceder las existencias disponibles bajo acceso concurrente**.

Fuente: PDF, Tabla 10 (RNF-02), subpregunta SP-1, indicador I-02 y riesgo R-03.

> **Regla del PDF (riesgo R-03):** «Escribir la prueba de concurrencia **antes** de implementar la funcionalidad y ejecutarla en cada integración; revisión cruzada obligatoria del código de la transacción.»

## Escenario de referencia CP-90

| Parámetro | Valor |
| --- | --- |
| Stock inicial | **10 unidades** (un producto, una variante) |
| Solicitudes simultáneas | **50** |
| Cantidad solicitada por solicitud | **1 unidad** |
| Órdenes confirmadas esperadas | **10** |
| Solicitudes rechazadas esperadas | **40** |
| Stock final esperado | **0** |

### Aserciones obligatorias

| # | Aserción | Cómo se comprueba |
| --- | --- | --- |
| A1 | Exactamente 10 respuestas `201 Created` | Conteo de respuestas |
| A2 | Exactamente 40 respuestas `409` con `error.code = "INSUFFICIENT_STOCK"` | Conteo y verificación del código |
| A3 | `stock_quantity` final = 0 | Consulta directa a la base de datos |
| A4 | `stock_quantity` nunca fue negativo | Restricción `CHECK` activa + consulta final |
| A5 | Número de órdenes en la base = 10 | `SELECT count(*)` sobre órdenes creadas en la prueba |
| A6 | Suma de unidades en líneas de orden = 10 | Consulta de agregación |
| A7 | `stock_inicial = stock_final + unidades_confirmadas` | Invariante de conservación |
| A8 | Existen 10 registros de auditoría con `source = 'ORDEN'` | Consulta a `audit_log` |
| A9 | Ninguna respuesta es `500` | Un fallo no controlado invalida la prueba aunque los números cuadren |
| A10 | Ninguna orden quedó sin líneas ni con líneas huérfanas | Verificación de integridad referencial |

**A9 es tan importante como A1:** el criterio del PDF exige que las 40 restantes «reciban respuesta de indisponibilidad», no que fallen.

## Condiciones de ejecución

| Condición | Valor | Motivo |
| --- | --- | --- |
| Base de datos | PostgreSQL real en contenedor | La propiedad es transaccional; una base simulada no la demuestra |
| Simultaneidad | Las 50 solicitudes se lanzan lo más juntas posible, con barrera de sincronización | Sin solapamiento real la prueba no prueba nada |
| Estado inicial | Creado por la propia prueba (producto, variante, `stock_quantity = 10`) | Reproducibilidad |
| Límite de frecuencia | Desactivado o ampliado en el ambiente de pruebas | Evita que `RATE_LIMITED` enmascare el resultado |
| Repeticiones | 3 ejecuciones consecutivas en verde | Las condiciones de carrera son intermitentes |

Si el límite de frecuencia estuviera activo con el valor de producción (10 órdenes por minuto por IP), la prueba mediría el límite y no la concurrencia. Esta excepción se documenta aquí para que no se interprete como una configuración insegura.

## Variantes adicionales

| ID | Escenario | Resultado esperado |
| --- | --- | --- |
| CP-90.1 | 50 solicitudes de 1 unidad sobre 10 (caso base) | 10 confirmadas / 40 rechazadas / stock 0 |
| CP-90.2 | 20 solicitudes de 3 unidades sobre 10 | 3 confirmadas (9 unidades) / 17 rechazadas / stock 1 |
| CP-90.3 | 30 solicitudes sobre un producto con 0 unidades | 0 confirmadas / 30 rechazadas / stock 0 |
| CP-90.4 | Órdenes de dos líneas con variantes distintas, ambas escasas | Nunca se descuenta una línea sin la otra (RN-11) |
| CP-90.5 | Órdenes que referencian las mismas dos variantes en orden inverso | Sin interbloqueos: el bloqueo sigue orden determinista (RN-10) |
| CP-90.6 | Ajuste manual de inventario simultáneo con confirmación de órdenes | Sin pérdidas: el valor final refleja ambas operaciones y queda auditado |

CP-90.5 verifica que el orden determinista de bloqueo evita el interbloqueo; sin él, dos transacciones cruzadas podrían esperarse mutuamente y una fallaría con error de servidor (violando A9).

## Criterios de aceptación de la campaña

1. CP-90 y sus variantes en verde en tres ejecuciones consecutivas.
2. Ejecución dentro del canal de integración continua en **cada cambio** que toque órdenes o inventario.
3. Reporte de ejecución archivado como evidencia del indicador **I-02** (meta: 0 órdenes confirmadas que excedan las existencias).
4. Revisión cruzada del código de la transacción registrada en el Pull Request.

## Qué hacer si la prueba falla

| Síntoma | Causa probable | Acción |
| --- | --- | --- |
| Más de 10 confirmadas | Verificación y descuento fuera de la misma transacción, o sin bloqueo | Revisar ADR-005; corregir antes de continuar (defecto **crítico**) |
| Stock negativo | Falta el `CHECK` o el descuento no verifica | Restaurar la restricción y la verificación |
| Respuestas 500 | Interbloqueo o error no controlado | Revisar el orden de bloqueo (RN-10) y el manejo de errores |
| Menos de 10 confirmadas | Rechazos indebidos: bloqueo demasiado amplio o tiempos de espera | Revisar granularidad del bloqueo y tiempos |
| Resultado intermitente | Las solicitudes no son realmente simultáneas | Revisar la barrera de sincronización de la prueba |

Un fallo aquí **detiene la iteración**: RNF-02 es el núcleo no negociable del proyecto (PDF, apartado 12.3).

## Relación con otros documentos

| Documento | Qué aporta |
| --- | --- |
| [`../decisiones/ADR-005-concurrencia.md`](../decisiones/ADR-005-concurrencia.md) | Mecanismo elegido y alternativas evaluadas |
| [`../arquitectura/modelo-relacional.md`](../arquitectura/modelo-relacional.md) | Secuencia de la transacción e invariante de conservación |
| [`../arquitectura/reglas-negocio.md`](../arquitectura/reglas-negocio.md) | RN-08 … RN-11 |
| [`../api/endpoints.md`](../api/endpoints.md) | EP-05 y su contrato de errores |
| [`../api/errores.md`](../api/errores.md) | Forma exacta del `INSUFFICIENT_STOCK` que reciben las 40 solicitudes |
