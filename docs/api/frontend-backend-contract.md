# Contrato Frontend ↔ Backend

Documento oficial de integración. Responde, pantalla por pantalla: **qué envía el frontend**, **qué recibe**, **qué errores puede recibir** y **qué estados debe manejar**.

- Brandon (frontend) puede implementar cada pantalla leyendo solo este documento y [modelos.md](modelos.md).
- Hedixon (backend) sabe qué espera cada pantalla y qué comportamiento debe garantizar.
- Jhon (calidad) obtiene de aquí los estados y errores que deben verificarse.

## Estados obligatorios en toda pantalla que llame a la API

| Estado | Cuándo | Comportamiento esperado |
| --- | --- | --- |
| **Loading** | Petición en curso | Indicador visible; controles de envío deshabilitados; no se pierde lo ya escrito |
| **Success** | 2xx con datos | Render normal |
| **Empty** | 2xx con `items: []` | Mensaje explícito («no hay resultados») y camino de salida (limpiar filtros) — no una pantalla en blanco |
| **Validation error** | 400 `VALIDATION_ERROR` | Marcar cada campo de `details.fields`; foco en el primero (RNF-03) |
| **Business error** | 409 / `CONSENT_REQUIRED` | Mensaje en lenguaje del usuario con la acción a seguir; nunca el código crudo |
| **Authentication error** | 401 | Limpiar sesión y redirigir al inicio de sesión conservando el destino |
| **Network error** | Sin respuesta o tiempo agotado | Mensaje de conexión y botón de reintentar |
| **Server error** | 500 / 503 | Mensaje genérico con el `requestId` visible; ofrecer reintentar |

Regla transversal: **la lógica se decide con `error.code`, nunca con `error.message`**.

---

## P-01 · Listado de catálogo

**Endpoints:** `GET /products` (EP-01), `GET /categories` (EP-02)

**Qué envía el frontend**

| Campo | Tipo | Formato | Obligatorio | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `q` | string | query | No | 2–80 caracteres | `camiseta` |
| `category` | string | query, repetible | No | slug existente | `camisetas` |
| `size` | string | query, repetible | No | — | `M` |
| `inStock` | boolean | query | No | — | `true` |
| `sort` | string | query | No | `campo:direccion` | `priceCop:asc` |
| `page` / `pageSize` | integer | query | No | `pageSize ≤ 50` | `1` / `12` |

**Qué recibe:** `Page<ProductSummaryResponse>`

| Campo | Tipo | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- |
| `items[].name` | string | No | Nombre | `"Camiseta oversize negra"` |
| `items[].priceCop` | integer | No | Precio en COP enteros; el frontend lo formatea | `85000` |
| `items[].imageUrl` | string | Sí | Imagen optimizada; si es `null` se usa marcador accesible | `"/media/p/2b91-800.webp"` |
| `items[].imageAlt` | string | Sí | Texto alternativo (RNF-03) | `"Camiseta negra"` |
| `items[].availableUnits` | integer | No | Existencias totales | `7` |
| `items[].inStock` | boolean | No | Habilita o no la compra | `true` |
| `items[].sizes` | array\<string\> | No | Tallas ofrecidas | `["S","M","L"]` |
| `meta.*` | integer | No | Paginación | — |

**Errores**

| HTTP | Código | Significado | Comportamiento esperado |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | Filtro u orden inválido | Revertir al último filtro válido e informar |
| — | Red | Sin respuesta | Estado de red con reintento |

**Estados:** Loading (esqueleto de tarjetas para no desplazar el contenido, RNF-01) · Success · Empty («sin resultados» + limpiar filtros) · Validation error · Network · Server.

---

## P-02 · Detalle de producto

**Endpoint:** `GET /products/{slug}` (EP-03)

**Envía:** `slug` en la ruta.
**Recibe:** `ProductResponse`, incluido `variants[]` con `id`, `size`, `availableUnits`, `inStock`.

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `NOT_FOUND` | 404 | Pantalla «producto no disponible» con enlace al catálogo; no reintentar |

**Estados:** Loading · Success · Empty (producto sin variantes activas: mostrar «no disponible») · Network · Server.

Reglas de interfaz: la talla es de selección obligatoria antes de agregar; las tallas con `inStock: false` se muestran deshabilitadas con su motivo; el botón de compra se deshabilita si `inStock` general es `false` (RN-03).

---

## P-03 · Carrito

**Endpoint:** `POST /cart/validate` (EP-04)

**Qué envía**

| Campo | Tipo | Formato | Obligatorio | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `items[].variantId` | uuid | JSON | Sí | Variante activa | `"9a4c…"` |
| `items[].quantity` | integer | JSON | Sí | 1–20 | `2` |

**Qué recibe:** `CartValidationResponse` con `valid`, `items[].available`, `items[].availableUnits`, `items[].unitPriceCop`, `totalCop`, `checkedAt`.

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | Corregir cantidades; marcar la línea |
| `NOT_FOUND` | 404 | La variante ya no existe: retirar la línea informando al usuario |

**Estados:** Loading · Success · Empty (carrito vacío con enlace al catálogo) · Business error (alguna línea con `available: false`: marcarla y bloquear «continuar») · Network · Server.

Notas obligatorias: el total mostrado proviene de `totalCop`, no se calcula en el cliente; la validación **no reserva** unidades, por lo que el frontend no debe prometer disponibilidad (RN-06).

---

## P-04 · Checkout (datos y autorización)

**Endpoint:** `POST /orders` (EP-05)

**Qué envía**

| Campo | Tipo | Formato | Obligatorio | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `items[].variantId` | uuid | JSON | Sí | Único por línea | `"9a4c…"` |
| `items[].quantity` | integer | JSON | Sí | 1–20 | `2` |
| `customer.name` | string | JSON | Sí | 3–120 | `"Ana Ríos"` |
| `customer.email` | string | JSON | Sí | Formato correo | `"ana@example.com"` |
| `customer.phone` | string | JSON | Sí | 7–15 dígitos | `"+573001234567"` |
| `customer.address` | string | JSON | Sí | 5–200 | `"Calle 45 # 12-34"` |
| `customer.city` | string | JSON | Sí | 2–80 | `"Bogotá D.C."` |
| `dataProcessingConsent` | boolean | JSON | Sí | Debe ser `true` | `true` |
| `privacyNoticeVersion` | string | JSON | Sí | Versión mostrada | `"1.0"` |
| `Idempotency-Key` | string | header | No | Identificador del intento | `"chk_8f2a…"` |

**Qué recibe (201):** `OrderResponse` con `orderNumber`, `status: "CONFIRMADA"`, `items[]`, `totalCop`, `simulatedCheckout: true`.

**Errores**

| HTTP | Código | Significado | Comportamiento esperado |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | Datos inválidos | Marcar campos de `details.fields`; conservar lo escrito |
| 400 | `CONSENT_REQUIRED` | Falta la autorización | Resaltar la casilla y el enlace al aviso; no reenviar hasta marcarla |
| 404 | `NOT_FOUND` | Variante inexistente | Retirar la línea y volver al carrito |
| 409 | `INSUFFICIENT_STOCK` | Alguien compró antes | Mostrar por línea `availableUnits`; ofrecer ajustar cantidades o eliminar la línea; **no reintentar automáticamente** |
| 429 | `RATE_LIMITED` | Demasiados intentos | Esperar `details.retryAfterSeconds` |
| 500 | `INTERNAL_ERROR` | Fallo del servidor | Mensaje con `requestId`; permitir reintento (con `Idempotency-Key` si se usó) |

**Estados:** Loading (bloquear el botón para evitar doble envío) · Success (ir a confirmación) · Validation error · Business error (`CONSENT_REQUIRED`, `INSUFFICIENT_STOCK`) · Network (la orden pudo haberse creado: ofrecer consultar por `orderNumber` o reintentar con la misma `Idempotency-Key`) · Server.

Obligatorio por REQ-04/RN-12: el aviso de simulación de pago es visible **antes** de confirmar, no solo después.

---

## P-05 · Confirmación

**Endpoint:** ninguno (usa la respuesta de EP-05); `GET /orders/{orderNumber}?email=` (EP-06) al recargar.

**Recibe:** `OrderResponse`. **Muestra:** `orderNumber` destacado, líneas con `productName`, `size`, `quantity`, `unitPriceCop`, `lineTotalCop`, `totalCop`, aviso de simulación y nota de que llegará una notificación (REQ-05).

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `NOT_FOUND` | 404 | Número o correo no coinciden: formulario para reintentar |
| `VALIDATION_ERROR` | 400 | Falta el correo |

**Estados:** Loading · Success · Validation error · Network · Server.

El frontend **no** afirma que la notificación fue enviada: solo que la orden quedó confirmada (RN-15).

---

## P-06 · Consulta de orden

**Endpoint:** `GET /orders/{orderNumber}?email=` (EP-06)

**Envía:** `orderNumber` (ruta) y `email` (query).
**Recibe:** `OrderResponse` con contacto enmascarado.
**Errores:** `NOT_FOUND` (404, respuesta única para número inexistente o correo que no coincide), `VALIDATION_ERROR` (400).
**Estados:** Loading · Success · Validation error · Empty/no encontrado · Network · Server.

---

## P-10 · Inicio de sesión (administración)

**Endpoint:** `POST /auth/login` (EP-10)

| Envía | Tipo | Obligatorio | Restricciones |
| --- | --- | --- | --- |
| `email` | string | Sí | Formato correo |
| `password` | string | Sí | 8–128 |

**Recibe:** `LoginResponse` (`accessToken`, `expiresIn`, `user`).

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `INVALID_CREDENTIALS` | 401 | Mensaje genérico; no indicar si el correo existe |
| `RATE_LIMITED` | 429 | Mostrar la espera requerida |
| `VALIDATION_ERROR` | 400 | Marcar campos |

**Estados:** Loading · Success · Validation error · Authentication error · Network · Server.

El token se guarda en memoria durante la sesión; al recibir 401 en cualquier pantalla se limpia y se vuelve aquí.

---

## P-11 · Lista de productos (administración)

**Endpoints:** `GET /admin/products` (EP-21), `PATCH /admin/products/{id}/publish` (EP-13)

**Recibe:** `Page<ProductSummaryResponse>` con `published` explícito.

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `UNAUTHENTICATED` | 401 | Volver al inicio de sesión |
| `VALIDATION_ERROR` | 400 | Publicar sin variantes activas (RN-21): explicar que debe agregar al menos una talla |
| `NOT_FOUND` | 404 | Refrescar la lista |

**Estados:** Loading · Success · Empty («aún no hay productos» + acción de crear) · Validation error · Authentication error · Network · Server.

---

## P-12 · Formulario único de producto

**Endpoints:** `POST /admin/products` (EP-12), `PATCH /admin/products/{id}` (EP-22), `POST /admin/products/{id}/images` (EP-16), `POST /admin/products/{id}/variants` (EP-14)

**Qué envía**

| Campo | Tipo | Formato | Obligatorio | Restricciones |
| --- | --- | --- | --- | --- |
| `name` | string | JSON | Sí | 3–120 |
| `description` | string | JSON | No | ≤ 2000 |
| `priceCop` | integer | JSON | Sí | > 0, sin decimales |
| `categoryId` | uuid | JSON | Sí | Categoría existente |
| `variants[].size` | string | JSON | Sí | Única por producto |
| `variants[].initialStock` | integer | JSON | Sí | ≥ 0 |
| `published` | boolean | JSON | No | Default `false` |
| `file` | archivo | multipart | Sí para imagen | ≤ 5 MB, jpeg/png/webp |
| `alt` | string | multipart | Sí para imagen | ≤ 160 (RNF-03) |

**Recibe:** `ProductResponse` y `ProductImageResponse`.

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | Marcar campos; el precio se envía en enteros |
| `CONFLICT` | 409 | Talla o SKU repetido: señalar la fila |
| `PAYLOAD_TOO_LARGE` | 413 | Indicar el máximo de `details.maxBytes` |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Indicar formatos de `details.allowed` |
| `UNAUTHENTICATED` | 401 | Volver al inicio de sesión sin perder lo escrito |

**Estados:** Loading (progreso de carga de imagen) · Success (confirmación explícita, RNF-05) · Validation error · Business error · Authentication error · Network · Server.

La tarea medida en RNF-05 es esta pantalla: debe completarse en menos de cinco minutos sin ayuda.

---

## P-13 · Inventario

**Endpoints:** `GET /admin/inventory` (EP-24), `PATCH /admin/variants/{id}/inventory` (EP-15)

| Envía | Tipo | Obligatorio | Restricciones |
| --- | --- | --- | --- |
| `stockQuantity` | integer | Sí | ≥ 0; es el **valor final**, no un ajuste relativo |
| `reason` | string | Sí | 3–120; queda en auditoría |

**Recibe:** `InventoryResponse`.

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | Valor negativo o motivo ausente |
| `NOT_FOUND` | 404 | Variante eliminada: refrescar |
| `UNAUTHENTICATED` | 401 | Volver al inicio de sesión |

**Estados:** Loading · Success (mostrar el valor resultante y la hora) · Empty · Validation error · Authentication error · Network · Server.

La pantalla debe dejar claro que se escribe el valor final; es la principal fuente de error del propietario (RNF-05).

---

## P-14 · Órdenes

**Endpoints:** `GET /admin/orders` (EP-17), `GET /admin/orders/{id}` (EP-23), `PATCH /admin/orders/{id}/status` (EP-18)

**Recibe:** `Page<OrderSummaryResponse>` y `OrderResponse` completo (sin enmascarar).

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `INVALID_STATE_TRANSITION` | 409 | Recargar la orden y mostrar su estado real con las transiciones posibles |
| `VALIDATION_ERROR` | 400 | Cancelar sin motivo: pedir el motivo |
| `UNAUTHENTICATED` | 401 | Volver al inicio de sesión |
| `NOT_FOUND` | 404 | Refrescar el listado |

**Estados:** Loading · Success · Empty («aún no hay órdenes») · Business error · Authentication error · Network · Server.

La interfaz solo ofrece las transiciones válidas según RN-13; el estado `notificationStatus = FALLIDA` se muestra como aviso para contactar al comprador por otro medio.

---

## P-15 · Auditoría

**Endpoint:** `GET /admin/audit-logs` (EP-19)

**Recibe:** `Page<AuditEntryResponse>` ordenado por fecha descendente, con `oldValue`, `newValue`, `performedBy`, `source` y `reason`.

| Errores | HTTP | Comportamiento |
| --- | --- | --- |
| `VALIDATION_ERROR` | 400 | Rango de fechas inválido |
| `UNAUTHENTICATED` | 401 | Volver al inicio de sesión |

**Estados:** Loading · Success · Empty · Validation error · Authentication error · Network · Server.
Pantalla de solo lectura: no existen acciones de edición (RN-25).

---

## P-16 · Notificaciones

**Endpoint:** `GET /admin/notifications` (EP-20)

**Recibe:** `Page<NotificationResponse>` con `status`, `attempts`, `lastError`.
**Errores:** `VALIDATION_ERROR` (400), `UNAUTHENTICATED` (401).
**Estados:** Loading · Success · Empty · Authentication error · Network · Server.

Es la salida del riesgo R-08: permite al administrador ver qué órdenes no se notificaron.

---

## Resumen pantalla ↔ endpoint ↔ requisito

| Pantalla | Endpoints | Requisitos | Historias |
| --- | --- | --- | --- |
| P-01 Listado | EP-01, EP-02 | REQ-01 | HU-01, HU-02, HU-03 |
| P-02 Detalle | EP-03 | REQ-01 | HU-04 |
| P-03 Carrito | EP-04 | REQ-02 | HU-05, HU-06 |
| P-04 Checkout | EP-05 | REQ-03, REQ-04, REQ-08 | HU-07, HU-08, HU-09 |
| P-05 Confirmación | EP-05, EP-06 | REQ-04, REQ-05 | HU-08, HU-10 |
| P-06 Consulta de orden | EP-06 | REQ-03 | HU-11 |
| P-10 Login | EP-10, EP-11 | RNF-04 | HU-12 |
| P-11 Productos | EP-21, EP-13 | REQ-06 | HU-13, HU-14 |
| P-12 Formulario de producto | EP-12, EP-22, EP-14, EP-16 | REQ-06, RNF-05 | HU-13 |
| P-13 Inventario | EP-24, EP-15 | REQ-06 | HU-15 |
| P-14 Órdenes | EP-17, EP-23, EP-18 | REQ-07 | HU-16, HU-17, HU-18 |
| P-15 Auditoría | EP-19 | REQ-06, REQ-07 | HU-19 |
| P-16 Notificaciones | EP-20 | REQ-05 | HU-20 |

## Compromisos mutuos

**El backend garantiza que:**

1. Los nombres y tipos son exactamente los de [modelos.md](modelos.md).
2. Todo error usa la estructura y los códigos de [errores.md](errores.md).
3. Un 201 en `POST /orders` implica inventario ya descontado.
4. Un 409 `INSUFFICIENT_STOCK` implica que **no se modificó nada**.
5. Las colecciones nunca son `null`.
6. Ningún cambio incompatible llega sin pasar por el procedimiento de [README.md](README.md#control-de-cambios).

**El frontend garantiza que:**

1. No implementa reglas de negocio propias ni asume disponibilidad sin consultar.
2. Decide con `error.code`, no con `error.message`.
3. Implementa los ocho estados en cada pantalla que llame a la API.
4. Envía exactamente los campos del contrato, sin extras (se rechazan con `VALIDATION_ERROR`).
5. Muestra el aviso de simulación de pago antes de confirmar.
6. Respeta el presupuesto de peso de RNF-01 y el texto alternativo de RNF-03.
