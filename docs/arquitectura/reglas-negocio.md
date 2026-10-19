# Reglas de negocio

Reglas explícitas e implícitas identificadas en `ProyectoTiendaLocalCUN.pdf`. Cada regla indica su condición, el comportamiento esperado y su trazabilidad hacia requisitos, entidades, API y pruebas.

- Las reglas derivadas de una decisión técnica del equipo, no explícitas en el PDF, están marcadas `DECISIÓN PROPUESTA`.
- Las entidades se describen en `modelo-dominio.md` y `modelo-er.md`; los endpoints en `../api/endpoints.md`; las pruebas en `../pruebas/casos-prueba.md`.

**Regla rectora del proyecto (PDF, apartado 9.1):** la verdad sobre el inventario reside en la base de datos transaccional. Ninguna comprobación hecha en el navegador es vinculante; toda regla se valida en el servidor.

---

## Catálogo y publicación

### RN-01 — Solo lo publicado es público

| Campo | Valor |
| --- | --- |
| **Descripción** | El catálogo público expone únicamente productos en estado publicado. |
| **Condición** | Petición a cualquier endpoint público de catálogo. |
| **Comportamiento esperado** | Los productos con `published = false` no aparecen en listados, búsquedas ni filtros, y su detalle responde 404. |
| **Requisitos** | REQ-01.5, REQ-06.1 |
| **Entidades** | PRODUCT |
| **API** | EP-01, EP-03 |
| **Pruebas** | CP-03 |

### RN-02 — La disponibilidad mostrada proviene del inventario real

| Campo | Valor |
| --- | --- |
| **Descripción** | La disponibilidad que ve el comprador se calcula desde las existencias almacenadas, nunca desde un valor editado manualmente aparte. |
| **Condición** | Render de listado o detalle. |
| **Comportamiento esperado** | `availableUnits` de un producto = suma de las existencias de sus variantes activas; `inStock = availableUnits > 0`. |
| **Requisitos** | REQ-01.1, REQ-01.2, RNF-02; deber de información veraz (Ley 1480 de 2011, PDF 3.3) |
| **Entidades** | PRODUCT, PRODUCT_VARIANT, INVENTORY |
| **API** | EP-01, EP-03 |
| **Pruebas** | CP-01, CP-05 |

### RN-03 — Agotado se muestra, no se oculta `DECISIÓN PROPUESTA`

| Campo | Valor |
| --- | --- |
| **Descripción** | Un producto publicado sin unidades sigue visible, marcado como agotado y sin posibilidad de compra. |
| **Condición** | `availableUnits = 0` y `published = true`. |
| **Comportamiento esperado** | Aparece en listados con `inStock = false`; el botón de compra se deshabilita; agregarlo al carrito se rechaza (RN-07). |
| **Requisitos** | REQ-01.6 |
| **Entidades** | PRODUCT, INVENTORY |
| **API** | EP-01, EP-03, EP-04 |
| **Pruebas** | CP-06 |
| **Justificación** | El criterio CA-01-0 exige un catálogo «con productos disponibles y agotados»; ocultarlos lo haría inverificable. |

### RN-04 — Los filtros operan sobre atributos de la variante

| Campo | Valor |
| --- | --- |
| **Descripción** | El filtro por talla selecciona productos que tienen una variante de esa talla; el filtro por categoría, productos de esa categoría. |
| **Condición** | Petición con `category` y/o `size`. |
| **Comportamiento esperado** | Filtros combinables con AND. Por defecto el filtro de talla no exige stock; con `inStock=true` se restringe a variantes con existencias. |
| **Requisitos** | REQ-01.4 |
| **Entidades** | PRODUCT, PRODUCT_VARIANT, CATEGORY |
| **API** | EP-01, EP-02 |
| **Pruebas** | CP-02 |

---

## Carrito

### RN-05 — La unidad vendible es la variante

| Campo | Valor |
| --- | --- |
| **Descripción** | Toda línea de carrito y de orden referencia una variante (SKU), nunca un producto. |
| **Condición** | Alta de línea de carrito u orden. |
| **Comportamiento esperado** | Una petición que referencie un producto sin variante se rechaza con `VALIDATION_ERROR`. |
| **Requisitos** | REQ-02, REQ-03, REQ-06.6 |
| **Entidades** | PRODUCT_VARIANT, ORDER_ITEM |
| **API** | EP-04, EP-05 |
| **Pruebas** | CP-11, CP-20 |
| **Justificación** | `DECISIÓN PROPUESTA` derivada de ADR-002 (inventario por variante). |

### RN-06 — La validación del carrito no reserva unidades `DECISIÓN PROPUESTA`

| Campo | Valor |
| --- | --- |
| **Descripción** | Comprobar disponibilidad al agregar al carrito es informativo; no bloquea ni aparta unidades. |
| **Condición** | Cualquier validación previa a la creación de la orden. |
| **Comportamiento esperado** | El resultado es una fotografía del momento; entre la validación y la confirmación el stock puede cambiar y la orden puede rechazarse (RN-11). |
| **Requisitos** | REQ-02.4 |
| **Entidades** | INVENTORY |
| **API** | EP-04 |
| **Pruebas** | CP-13, CP-90 |
| **Justificación** | El PDF no define reservas ni su expiración; introducirlas agregaría estado y caducidad fuera de alcance. |

### RN-07 — Cantidad solicitada ≤ existencias disponibles

| Campo | Valor |
| --- | --- |
| **Descripción** | No se admite agregar más unidades de las disponibles ni agregar una variante agotada. |
| **Condición** | `quantity > availableUnits` o `availableUnits = 0`. |
| **Comportamiento esperado** | Se impide la operación y se informa el motivo y las unidades disponibles. |
| **Requisitos** | REQ-02.2, REQ-02.3 |
| **Entidades** | INVENTORY, PRODUCT_VARIANT |
| **API** | EP-04 |
| **Pruebas** | CP-10, CP-11 |

---

## Orden e inventario (núcleo del proyecto)

### RN-08 — Orden e inventario cambian en una sola transacción

| Campo | Valor |
| --- | --- |
| **Descripción** | La verificación de existencias, su descuento y la creación de la orden ocurren dentro de una única transacción de base de datos. |
| **Condición** | Confirmación de pedido. |
| **Comportamiento esperado** | O se crea la orden y se descuentan todas las unidades, o no ocurre nada de lo anterior. |
| **Requisitos** | REQ-03.1, RNF-02 |
| **Entidades** | ORDER, ORDER_ITEM, INVENTORY |
| **API** | EP-05 |
| **Pruebas** | CP-20, CP-21, CP-90 |

### RN-09 — El inventario nunca puede ser negativo

| Campo | Valor |
| --- | --- |
| **Descripción** | Ninguna operación puede dejar las existencias de una variante por debajo de cero. |
| **Condición** | Cualquier escritura sobre existencias (orden, ajuste manual, cancelación). |
| **Comportamiento esperado** | La operación se rechaza. La restricción se declara además en la base de datos (`CHECK (stock_quantity >= 0)`) como última línea de defensa. |
| **Requisitos** | RNF-02, REQ-03, REQ-06.2 |
| **Entidades** | INVENTORY |
| **API** | EP-05, EP-15 |
| **Pruebas** | CP-53, CP-90 |

### RN-10 — Bloqueo de las filas de existencias durante la confirmación

| Campo | Valor |
| --- | --- |
| **Descripción** | La transacción bloquea las filas de existencias de las variantes solicitadas antes de verificar y descontar. |
| **Condición** | Confirmación de pedido con una o más líneas. |
| **Comportamiento esperado** | Dos solicitudes simultáneas sobre la misma variante se serializan: la segunda lee el valor ya actualizado. Las filas se bloquean en orden determinista (por `variant_id` ascendente) para evitar interbloqueos. |
| **Requisitos** | RNF-02; PDF apartado 9.3 («bloquea las filas de existencias») |
| **Entidades** | INVENTORY |
| **API** | EP-05 |
| **Pruebas** | CP-90 |
| **Nota** | El orden determinista de bloqueo es `DECISIÓN PROPUESTA`; ver ADR-005. |

### RN-11 — Todo o nada por orden completa

| Campo | Valor |
| --- | --- |
| **Descripción** | Si cualquier línea no puede satisfacerse, la orden completa se rechaza. |
| **Condición** | Al menos una línea con existencias insuficientes. |
| **Comportamiento esperado** | Se revierte la transacción, no se descuenta ninguna unidad y la respuesta detalla las líneas indisponibles con las unidades realmente disponibles (`INSUFFICIENT_STOCK`). |
| **Requisitos** | REQ-03.2 |
| **Entidades** | ORDER, INVENTORY |
| **API** | EP-05 |
| **Pruebas** | CP-23 |

### RN-12 — El pago es simulado y debe declararse

| Campo | Valor |
| --- | --- |
| **Descripción** | El sistema no procesa pagos ni almacena datos financieros, y la interfaz lo advierte explícitamente. |
| **Condición** | Flujo de checkout. |
| **Comportamiento esperado** | La respuesta de creación de orden incluye `simulatedCheckout = true`; la interfaz muestra el aviso; no existen campos de tarjeta en la API ni en el modelo de datos. |
| **Requisitos** | REQ-04.1, REQ-04.2 |
| **Entidades** | ORDER |
| **API** | EP-05, EP-06 |
| **Pruebas** | CP-30, CP-31 |

### RN-13 — Estados de la orden y transiciones válidas

| Campo | Valor |
| --- | --- |
| **Descripción** | Una orden vive en un ciclo de estados acotado; solo se admiten transiciones hacia adelante y la cancelación. |
| **Condición** | Cambio de estado solicitado por el administrador. |
| **Comportamiento esperado** | `CONFIRMADA → PREPARADA → ENTREGADA`; `CONFIRMADA`/`PREPARADA → CANCELADA`. Cualquier otra transición se rechaza con `INVALID_STATE_TRANSITION`. La cancelación devuelve las unidades al inventario en la misma transacción. |
| **Requisitos** | REQ-07.2, REQ-07.4 |
| **Entidades** | ORDER, INVENTORY, AUDIT_LOG |
| **API** | EP-18 |
| **Pruebas** | CP-60, CP-61, CP-62 |
| **Nota** | `CANCELADA` y el conjunto de transiciones son `DECISIÓN PROPUESTA`; el PDF solo nombra los estados confirmada, preparada y entregada. |

### RN-28 — La orden congela precio y descripción `DECISIÓN PROPUESTA`

| Campo | Valor |
| --- | --- |
| **Descripción** | Cada línea de orden guarda copia del nombre, la talla y el precio unitario vigentes al confirmar. |
| **Condición** | Creación de la orden. |
| **Comportamiento esperado** | Cambios posteriores de precio o de nombre del producto no alteran órdenes ya creadas. |
| **Requisitos** | REQ-03.3; Ley 527 de 1999: la orden debe conservarse íntegra y recuperable (PDF 3.3) |
| **Entidades** | ORDER_ITEM |
| **API** | EP-05, EP-06, EP-17 |
| **Pruebas** | CP-22 |

### RN-29 — Una orden tiene al menos una línea y cantidades positivas

| Campo | Valor |
| --- | --- |
| **Descripción** | No se admiten órdenes vacías ni líneas con cantidad cero o negativa. |
| **Condición** | Petición de creación de orden. |
| **Comportamiento esperado** | Se rechaza con `VALIDATION_ERROR` antes de abrir la transacción. |
| **Requisitos** | REQ-03 |
| **Entidades** | ORDER, ORDER_ITEM |
| **API** | EP-05 |
| **Pruebas** | CP-25 |

---

## Notificaciones

### RN-14 — Notificación tras la confirmación

| Campo | Valor |
| --- | --- |
| **Descripción** | Toda orden confirmada genera notificación al comprador y al administrador con identificador, productos y cantidades, en menos de cinco minutos. |
| **Condición** | Orden en estado `CONFIRMADA`. |
| **Comportamiento esperado** | Se registra la notificación y se despacha de forma asíncrona al servicio de correo. |
| **Requisitos** | REQ-05.1, REQ-05.2 |
| **Entidades** | ORDER, NOTIFICATION |
| **API** | EP-05 (efecto) |
| **Pruebas** | CP-40 |

### RN-15 — El fallo de notificación degrada, no bloquea

| Campo | Valor |
| --- | --- |
| **Descripción** | Un error o agotamiento de cuota del servicio de correo no revierte ni bloquea la orden. |
| **Condición** | Error al enviar. |
| **Comportamiento esperado** | La notificación queda con estado `FALLIDA` y se muestra en el panel de administración; la orden permanece confirmada. |
| **Requisitos** | REQ-05.3, REQ-05.4; riesgo R-08 |
| **Entidades** | NOTIFICATION |
| **API** | EP-20 |
| **Pruebas** | CP-41 |

---

## Datos personales

### RN-16 — Sin autorización no hay orden

| Campo | Valor |
| --- | --- |
| **Descripción** | La autorización de tratamiento de datos es previa y obligatoria; se valida en el servidor. |
| **Condición** | `dataProcessingConsent` ausente o falso. |
| **Comportamiento esperado** | No se crea la orden; se responde `CONSENT_REQUIRED` indicando el motivo. |
| **Requisitos** | REQ-08.1, REQ-08.5 |
| **Entidades** | ORDER |
| **API** | EP-05 |
| **Pruebas** | CP-70, CP-73 |

### RN-17 — Minimización de datos personales

| Campo | Valor |
| --- | --- |
| **Descripción** | Solo se recolectan los datos necesarios para entregar el pedido y notificar: nombre, correo, teléfono, dirección y ciudad. |
| **Condición** | Diseño del formulario, de la API y del esquema. |
| **Comportamiento esperado** | Ningún campo personal sin finalidad declarada; campos adicionales enviados por el cliente se ignoran. |
| **Requisitos** | REQ-08.3, RNF-04 |
| **Entidades** | ORDER |
| **API** | EP-05 |
| **Pruebas** | CP-82 |

### RN-18 — Acceso del comprador a su propia orden `DECISIÓN PROPUESTA`

| Campo | Valor |
| --- | --- |
| **Descripción** | El comprador consulta su orden con el número de orden más el correo con que la creó. |
| **Condición** | Consulta pública de orden. |
| **Comportamiento esperado** | Si el par número + correo no coincide, se responde 404 (no se revela la existencia de la orden). |
| **Requisitos** | REQ-03.3, RNF-04 |
| **Entidades** | ORDER |
| **API** | EP-06 |
| **Pruebas** | CP-22 |
| **Justificación** | El PDF no prevé cuentas de comprador, pero la orden debe ser recuperable (Ley 527 de 1999); exponerla solo por número permitiría enumerar datos personales de terceros. |

---

## Administración, seguridad y auditoría

### RN-19 — Toda operación de administración exige autenticación

| Campo | Valor |
| --- | --- |
| **Descripción** | Los endpoints bajo `/admin` requieren un administrador autenticado. |
| **Condición** | Petición sin credencial válida. |
| **Comportamiento esperado** | 401 `UNAUTHENTICATED`, sin efectos sobre los datos. |
| **Requisitos** | REQ-06, RNF-04 |
| **Entidades** | ADMIN_USER |
| **API** | EP-10 … EP-20 |
| **Pruebas** | CP-51 |

### RN-20 — Credenciales con función de derivación de clave

| Campo | Valor |
| --- | --- |
| **Descripción** | Las contraseñas se almacenan mediante función de derivación de clave; nunca en texto claro ni recuperables. |
| **Condición** | Alta o cambio de contraseña del administrador. |
| **Comportamiento esperado** | Se almacena únicamente el hash derivado; los errores de autenticación no distinguen usuario inexistente de contraseña incorrecta. |
| **Requisitos** | RNF-04 |
| **Entidades** | ADMIN_USER |
| **API** | EP-10 |
| **Pruebas** | CP-82 |

### RN-21 — Un producto publicable tiene al menos una variante `DECISIÓN PROPUESTA`

| Campo | Valor |
| --- | --- |
| **Descripción** | No puede publicarse un producto sin variantes, porque no tendría unidad vendible ni inventario. |
| **Condición** | Intento de publicar un producto sin variantes. |
| **Comportamiento esperado** | Se rechaza con `VALIDATION_ERROR`. |
| **Requisitos** | REQ-06.1, REQ-06.6 |
| **Entidades** | PRODUCT, PRODUCT_VARIANT |
| **API** | EP-13 |
| **Pruebas** | CP-55 |

### RN-22 — Imágenes optimizadas en el servidor

| Campo | Valor |
| --- | --- |
| **Descripción** | Las imágenes se convierten a formato moderno y se redimensionan al cargarse. |
| **Condición** | Carga de imagen desde el panel. |
| **Comportamiento esperado** | Se almacena la versión optimizada; se rechazan archivos que no sean imagen o que excedan el tamaño máximo. |
| **Requisitos** | REQ-06.5, RNF-01; riesgo R-06 |
| **Entidades** | PRODUCT_IMAGE |
| **API** | EP-16 |
| **Pruebas** | CP-54, CP-80 |

### RN-23 — Despublicar no borra

| Campo | Valor |
| --- | --- |
| **Descripción** | La baja de un producto es lógica: deja de publicarse pero conserva su historial. |
| **Condición** | Baja solicitada desde el panel. |
| **Comportamiento esperado** | El producto permanece en la base de datos y en las órdenes anteriores; no se elimina físicamente. |
| **Requisitos** | REQ-06.7; Ley 527 de 1999 |
| **Entidades** | PRODUCT, ORDER_ITEM |
| **API** | EP-13 |
| **Pruebas** | CP-52 |

### RN-24 — Toda variación de existencias se audita

| Campo | Valor |
| --- | --- |
| **Descripción** | Cada cambio de existencias genera un registro con usuario, valor anterior, valor nuevo, origen y fecha. |
| **Condición** | Ajuste manual, descuento por orden o devolución por cancelación. |
| **Comportamiento esperado** | Se escribe en `AUDIT_LOG` dentro de la misma transacción del cambio; el origen distingue `AJUSTE_MANUAL`, `ORDEN` y `CANCELACION`. |
| **Requisitos** | REQ-06.3, REQ-03.4 |
| **Entidades** | AUDIT_LOG, INVENTORY |
| **API** | EP-15, EP-05, EP-18, EP-19 |
| **Pruebas** | CP-24, CP-50 |

### RN-25 — La auditoría es de solo anexado

| Campo | Valor |
| --- | --- |
| **Descripción** | Los registros de auditoría no se editan ni se borran desde la aplicación. |
| **Condición** | Cualquier operación sobre auditoría. |
| **Comportamiento esperado** | Solo existen operaciones de inserción y de consulta; la API no expone actualización ni borrado. |
| **Requisitos** | REQ-06.3, REQ-07.3; componente C6 (fuente de evidencia de los indicadores) |
| **Entidades** | AUDIT_LOG |
| **API** | EP-19 |
| **Pruebas** | CP-50, CP-60 |
| **Nota** | `DECISIÓN PROPUESTA`: el PDF exige registro, no inmutabilidad explícita; sin ella la auditoría no sirve como evidencia. |

### RN-26 — Las órdenes solo son visibles para el administrador

| Campo | Valor |
| --- | --- |
| **Descripción** | El listado completo de órdenes y los datos personales asociados no son públicos. |
| **Condición** | Consulta de listado de órdenes. |
| **Comportamiento esperado** | Requiere autenticación (RN-19); el comprador solo accede a la suya por RN-18. |
| **Requisitos** | REQ-07.1, RNF-04 |
| **Entidades** | ORDER |
| **API** | EP-17 |
| **Pruebas** | CP-51 |

### RN-27 — Todo cambio de estado de orden se audita

| Campo | Valor |
| --- | --- |
| **Descripción** | Cada transición de estado queda registrada con usuario, estado anterior, estado nuevo y fecha. |
| **Condición** | Cambio de estado o cancelación. |
| **Comportamiento esperado** | Registro en `AUDIT_LOG` en la misma transacción del cambio. |
| **Requisitos** | REQ-07.3; Ley 527 de 1999 (toda modificación del estado debe quedar registrada) |
| **Entidades** | AUDIT_LOG, ORDER |
| **API** | EP-18, EP-19 |
| **Pruebas** | CP-60, CP-62 |

---

## Resumen de trazabilidad de reglas

| Regla | REQ | Entidad principal | Endpoint | Prueba |
| --- | --- | --- | --- | --- |
| RN-01 | REQ-01, REQ-06 | PRODUCT | EP-01, EP-03 | CP-03 |
| RN-02 | REQ-01, RNF-02 | INVENTORY | EP-01, EP-03 | CP-01 |
| RN-03 | REQ-01 | PRODUCT | EP-01 | CP-06 |
| RN-04 | REQ-01 | PRODUCT_VARIANT | EP-01 | CP-02 |
| RN-05 | REQ-02, REQ-03 | PRODUCT_VARIANT | EP-04, EP-05 | CP-11 |
| RN-06 | REQ-02 | INVENTORY | EP-04 | CP-13 |
| RN-07 | REQ-02 | INVENTORY | EP-04 | CP-10 |
| RN-08 | REQ-03, RNF-02 | ORDER | EP-05 | CP-20 |
| RN-09 | RNF-02, REQ-06 | INVENTORY | EP-05, EP-15 | CP-53, CP-90 |
| RN-10 | RNF-02 | INVENTORY | EP-05 | CP-90 |
| RN-11 | REQ-03 | ORDER | EP-05 | CP-23 |
| RN-12 | REQ-04 | ORDER | EP-05 | CP-31 |
| RN-13 | REQ-07 | ORDER | EP-18 | CP-61 |
| RN-14 | REQ-05 | NOTIFICATION | EP-05 | CP-40 |
| RN-15 | REQ-05 | NOTIFICATION | EP-20 | CP-41 |
| RN-16 | REQ-08 | ORDER | EP-05 | CP-70 |
| RN-17 | REQ-08, RNF-04 | ORDER | EP-05 | CP-82 |
| RN-18 | REQ-03, RNF-04 | ORDER | EP-06 | CP-22 |
| RN-19 | REQ-06, RNF-04 | ADMIN_USER | EP-10+ | CP-51 |
| RN-20 | RNF-04 | ADMIN_USER | EP-10 | CP-82 |
| RN-21 | REQ-06 | PRODUCT | EP-13 | CP-55 |
| RN-22 | REQ-06, RNF-01 | PRODUCT_IMAGE | EP-16 | CP-54 |
| RN-23 | REQ-06 | PRODUCT | EP-13 | CP-52 |
| RN-24 | REQ-06, REQ-03 | AUDIT_LOG | EP-15 | CP-50 |
| RN-25 | REQ-06, REQ-07 | AUDIT_LOG | EP-19 | CP-50 |
| RN-26 | REQ-07, RNF-04 | ORDER | EP-17 | CP-51 |
| RN-27 | REQ-07 | AUDIT_LOG | EP-18 | CP-60 |
| RN-28 | REQ-03 | ORDER_ITEM | EP-05 | CP-22 |
| RN-29 | REQ-03 | ORDER | EP-05 | CP-25 |
