# Endpoints

Base: `/api/v1` (versionado en la ruta — [`../decisiones/ADR-004-versionamiento-api.md`](../decisiones/ADR-004-versionamiento-api.md)).
Modelos: [modelos.md](modelos.md) · Errores: [errores.md](errores.md) · Convenciones: [convenciones.md](convenciones.md).

## Índice

| ID | Método | Ruta | Actor | Auth | Requisito |
| --- | --- | --- | --- | --- | --- |
| EP-01 | GET | `/products` | Comprador | No | REQ-01 |
| EP-02 | GET | `/categories` | Comprador | No | REQ-01 |
| EP-03 | GET | `/products/{slug}` | Comprador | No | REQ-01 |
| EP-04 | POST | `/cart/validate` | Comprador | No | REQ-02 |
| EP-05 | POST | `/orders` | Comprador | No | REQ-03, REQ-04, REQ-05, REQ-08 |
| EP-06 | GET | `/orders/{orderNumber}` | Comprador | No (número + correo) | REQ-03, REQ-04 |
| EP-10 | POST | `/auth/login` | Administrador | No | RNF-04 |
| EP-11 | GET | `/auth/me` | Administrador | Sí | RNF-04 |
| EP-12 | POST | `/admin/products` | Administrador | Sí | REQ-06 |
| EP-13 | PATCH | `/admin/products/{id}/publish` | Administrador | Sí | REQ-06 |
| EP-14 | POST | `/admin/products/{id}/variants` | Administrador | Sí | REQ-06 |
| EP-15 | PATCH | `/admin/variants/{id}/inventory` | Administrador | Sí | REQ-06 |
| EP-16 | POST | `/admin/products/{id}/images` | Administrador | Sí | REQ-06, RNF-01 |
| EP-17 | GET | `/admin/orders` | Administrador | Sí | REQ-07 |
| EP-18 | PATCH | `/admin/orders/{id}/status` | Administrador | Sí | REQ-07 |
| EP-19 | GET | `/admin/audit-logs` | Administrador | Sí | REQ-06, REQ-07 |
| EP-20 | GET | `/admin/notifications` | Administrador | Sí | REQ-05 |
| EP-21 | GET | `/admin/products` | Administrador | Sí | REQ-06 |
| EP-22 | PATCH | `/admin/products/{id}` | Administrador | Sí | REQ-06 |
| EP-23 | GET | `/admin/orders/{id}` | Administrador | Sí | REQ-07 |
| EP-24 | GET | `/admin/inventory` | Administrador | Sí | REQ-06 |

Cabeceras comunes: `Content-Type: application/json; charset=utf-8` en peticiones con cuerpo; `Authorization: Bearer <token>` en todo `/admin` y en `/auth/me`. Toda respuesta incluye `X-Request-Id`, el mismo valor que aparece en `error.requestId`.

---

# Endpoints públicos

## EP-01 — Listar catálogo

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/products` |
| **Descripción** | Listado paginado de productos publicados, con búsqueda, filtros y orden. |
| **Actor** | Comprador |
| **Autenticación** | No |
| **Path parameters** | — |

**Query parameters**

| Parámetro | Tipo | Obligatorio | Default | Restricciones |
| --- | --- | --- | --- | --- |
| `q` | string | No | — | 2–80 caracteres; busca en el nombre, sin distinción de mayúsculas ni tildes |
| `category` | string (slug) | No | — | Debe existir; repetible |
| `size` | string | No | — | Repetible (`?size=M&size=L`) |
| `inStock` | boolean | No | — | `true` limita a productos con unidades |
| `sort` | string | No | `createdAt:desc` | `name`, `priceCop`, `createdAt` con `:asc`/`:desc` |
| `page` | integer | No | 1 | ≥ 1 |
| `pageSize` | integer | No | 12 | 1–50 |

**Request body:** ninguno.
**Response 200:** `Page<ProductSummaryResponse>`.

```json
{
  "items": [
    {
      "id": "2b91c0de-5f41-4c2a-9bd3-77a0f1e2c3d4",
      "slug": "camiseta-oversize-negra",
      "name": "Camiseta oversize negra",
      "priceCop": 85000,
      "categoryName": "Camisetas",
      "imageUrl": "/media/p/2b91-800.webp",
      "imageAlt": "Camiseta negra vista frontal",
      "availableUnits": 7,
      "inStock": true,
      "sizes": ["S", "M", "L"]
    }
  ],
  "meta": { "page": 1, "pageSize": 12, "totalItems": 37, "totalPages": 4 }
}
```

| Aspecto | Valor |
| --- | --- |
| **Estados HTTP** | 200 · 400 |
| **Errores** | `VALIDATION_ERROR` (filtro, orden o paginación inválidos) |
| **Reglas de negocio** | RN-01, RN-02, RN-03, RN-04 |
| **Requisitos** | REQ-01.1, REQ-01.3, REQ-01.4, REQ-01.5, REQ-01.6 |
| **Historias** | HU-01, HU-02, HU-03 |
| **Pruebas** | CP-01, CP-02, CP-03, CP-04, CP-06 |

---

## EP-02 — Listar categorías

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/categories` |
| **Descripción** | Categorías disponibles para construir el filtro. |
| **Actor** | Comprador |
| **Autenticación** | No |
| **Parámetros** | — |
| **Response 200** | `array<CategoryResponse>` (sin paginar: el catálogo de un micronegocio no lo justifica) |
| **Estados HTTP** | 200 |
| **Errores** | — |
| **Reglas** | RN-04 |
| **Requisitos** | REQ-01.4 |
| **Historias** | HU-03 |
| **Pruebas** | CP-02 |

---

## EP-03 — Detalle de producto

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/products/{slug}` |
| **Descripción** | Detalle con imágenes y disponibilidad por talla. |
| **Actor** | Comprador |
| **Autenticación** | No |
| **Path parameters** | `slug` (string, obligatorio) |
| **Query parameters** | — |
| **Response 200** | `ProductResponse` |
| **Estados HTTP** | 200 · 404 |
| **Errores** | `NOT_FOUND` si no existe o no está publicado (RN-01) |
| **Reglas** | RN-01, RN-02, RN-03 |
| **Requisitos** | REQ-01.2 |
| **Historias** | HU-04 |
| **Pruebas** | CP-03, CP-05 |

Un producto despublicado responde 404, no 403: el catálogo público no revela su existencia.

---

## EP-04 — Validar carrito

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `POST /api/v1/cart/validate` |
| **Descripción** | Comprueba disponibilidad de una o varias líneas. **No reserva unidades** (RN-06). |
| **Actor** | Comprador |
| **Autenticación** | No |
| **Request body** | `CartValidationRequest` |
| **Response 200** | `CartValidationResponse` — se devuelve 200 aunque alguna línea no esté disponible: es una consulta, y el detalle viaja en `items[].available` |
| **Estados HTTP** | 200 · 400 · 404 |
| **Errores** | `VALIDATION_ERROR` (cantidad fuera de rango, `variantId` repetido); `NOT_FOUND` (variante inexistente o inactiva) |
| **Reglas** | RN-05, RN-06, RN-07 |
| **Requisitos** | REQ-02.2, REQ-02.3, REQ-02.5 |
| **Historias** | HU-05, HU-06 |
| **Pruebas** | CP-10, CP-11, CP-13 |

Se usa POST y no GET porque el carrito puede tener varias líneas y no debe quedar en el historial ni en los registros del proxy. `DECISIÓN PROPUESTA`.

---

## EP-05 — Crear orden (checkout simulado)

**El endpoint crítico del proyecto.**

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `POST /api/v1/orders` |
| **Descripción** | Verifica existencias, descuenta inventario y crea la orden en una sola transacción; devuelve la orden confirmada y dispara las notificaciones. |
| **Actor** | Comprador |
| **Autenticación** | No |
| **Headers** | `Content-Type: application/json`; opcional `Idempotency-Key` (ver nota) |
| **Request body** | `CreateOrderRequest` |
| **Response 201** | `OrderResponse` con `status = "CONFIRMADA"` y `simulatedCheckout = true` |

**Secuencia de validación (orden obligatorio, define qué error gana):**

1. Formato del cuerpo → `VALIDATION_ERROR` (400).
2. Consentimiento (RN-16) → `CONSENT_REQUIRED` (400).
3. Existencia de variantes → `NOT_FOUND` (404).
4. Transacción: bloqueo, verificación y descuento (RN-08, RN-10, RN-11) → `INSUFFICIENT_STOCK` (409) si falla.

| Aspecto | Valor |
| --- | --- |
| **Estados HTTP** | 201 · 400 · 404 · 409 · 429 · 500 |
| **Errores** | `VALIDATION_ERROR`, `CONSENT_REQUIRED`, `NOT_FOUND`, `INSUFFICIENT_STOCK`, `RATE_LIMITED`, `INTERNAL_ERROR` |
| **Reglas** | RN-05, RN-08, RN-09, RN-10, RN-11, RN-12, RN-14, RN-16, RN-17, RN-28, RN-29 |
| **Requisitos** | REQ-03, REQ-04, REQ-05, REQ-08, RNF-02 |
| **Historias** | HU-07, HU-08, HU-09, HU-10 |
| **Pruebas** | CP-20 … CP-25, CP-30, CP-31, CP-70, CP-73, **CP-90 (concurrencia)** |

Garantías:

- Si la respuesta es 201, las unidades ya están descontadas y la orden es recuperable por EP-06.
- Si la respuesta es 409, **no se descontó ninguna unidad** y el detalle indica qué líneas fallaron.
- La notificación ocurre después del `COMMIT` y su fallo no cambia la respuesta (RN-15).

`Idempotency-Key` es `DECISIÓN PROPUESTA`: si el comprador reintenta por un corte de red, el backend devuelve la orden ya creada en lugar de duplicarla. Si el cliente no la envía, el comportamiento es el normal.

---

## EP-06 — Consultar una orden

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/orders/{orderNumber}` |
| **Descripción** | Consulta de la propia orden por su número, validando el correo con que se creó (RN-18). |
| **Actor** | Comprador |
| **Autenticación** | No, pero exige coincidencia de número + correo |
| **Path parameters** | `orderNumber` (string, formato `TL-AAAAMMDD-XXXXX`) |
| **Query parameters** | `email` (string, obligatorio) |
| **Response 200** | `OrderResponse` con datos de contacto enmascarados |
| **Estados HTTP** | 200 · 400 · 404 |
| **Errores** | `VALIDATION_ERROR` (falta `email`); `NOT_FOUND` si el par no coincide |
| **Reglas** | RN-12, RN-18 |
| **Requisitos** | REQ-03.3, REQ-04.3 |
| **Historias** | HU-11 |
| **Pruebas** | CP-22 |

---

# Endpoints de administración

Todos exigen `Authorization: Bearer <token>` (RN-19). Un token ausente o vencido devuelve `UNAUTHENTICATED` (401) sin efectos secundarios.

## EP-10 — Iniciar sesión

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `POST /api/v1/auth/login` |
| **Descripción** | Autentica al administrador y entrega un token de acceso. |
| **Actor** | Administrador |
| **Autenticación** | No (es el punto de entrada) |
| **Request body** | `LoginRequest` |
| **Response 200** | `LoginResponse` |
| **Estados HTTP** | 200 · 400 · 401 · 429 |
| **Errores** | `VALIDATION_ERROR`, `INVALID_CREDENTIALS`, `RATE_LIMITED` |
| **Reglas** | RN-19, RN-20 |
| **Requisitos** | REQ-06, RNF-04 |
| **Historias** | HU-12 |
| **Pruebas** | CP-51, CP-82 |

El error no distingue entre correo inexistente y contraseña incorrecta. Límite de intentos por dirección IP y por cuenta (`RATE_LIMITED`) — `DECISIÓN PROPUESTA` derivada de OWASP A07.

## EP-11 — Sesión actual

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/auth/me` |
| **Descripción** | Devuelve el administrador autenticado; el frontend la usa al cargar para saber si la sesión sigue viva. |
| **Response 200** | `AdminUserResponse` |
| **Estados HTTP** | 200 · 401 |
| **Errores** | `UNAUTHENTICATED` |
| **Reglas** | RN-19 |
| **Requisitos** | RNF-04 |
| **Historias** | HU-12 |
| **Pruebas** | CP-51 |

## EP-12 — Crear producto

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `POST /api/v1/admin/products` |
| **Descripción** | Alta de producto con sus variantes y existencias iniciales, en un único envío (REQ-06.4). |
| **Request body** | `ProductCreateRequest` |
| **Response 201** | `ProductResponse` |
| **Estados HTTP** | 201 · 400 · 401 · 409 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED`, `CONFLICT` (slug o sku duplicado, talla repetida) |
| **Reglas** | RN-05, RN-19, RN-21, RN-24 |
| **Requisitos** | REQ-06.1, REQ-06.4, REQ-06.6 |
| **Historias** | HU-13 |
| **Pruebas** | CP-50, CP-51, CP-55 |

El producto nace despublicado salvo que se envíe `published: true`, y publicar exige al menos una variante activa (RN-21). Las existencias iniciales generan registro de auditoría con `source = AJUSTE_MANUAL`.

## EP-13 — Publicar o despublicar

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `PATCH /api/v1/admin/products/{id}/publish` |
| **Path parameters** | `id` (uuid) |
| **Request body** | `PublishRequest` |
| **Response 200** | `ProductResponse` |
| **Estados HTTP** | 200 · 400 · 401 · 404 |
| **Errores** | `VALIDATION_ERROR` (publicar sin variantes activas, RN-21), `UNAUTHENTICATED`, `NOT_FOUND` |
| **Reglas** | RN-01, RN-21, RN-23 |
| **Requisitos** | REQ-06.1, REQ-06.7 |
| **Historias** | HU-14 |
| **Pruebas** | CP-52, CP-55 |

Despublicar **no borra**: el producto sigue en la administración y en las órdenes previas. Queda auditado con `action = PUBLISH_CHANGE`.

## EP-14 — Agregar variante

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `POST /api/v1/admin/products/{id}/variants` |
| **Path parameters** | `id` (uuid del producto) |
| **Request body** | `VariantRequest` |
| **Response 201** | `ProductVariantResponse` |
| **Estados HTTP** | 201 · 400 · 401 · 404 · 409 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED`, `NOT_FOUND`, `CONFLICT` (talla o sku repetido) |
| **Reglas** | RN-05, RN-24 |
| **Requisitos** | REQ-06.1, REQ-06.6 |
| **Historias** | HU-13 |
| **Pruebas** | CP-50 |

## EP-15 — Ajustar existencias

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `PATCH /api/v1/admin/variants/{id}/inventory` |
| **Descripción** | Fija el valor final de existencias de una variante y registra la auditoría correspondiente. |
| **Path parameters** | `id` (uuid de la variante) |
| **Request body** | `InventoryAdjustmentRequest` |
| **Response 200** | `InventoryResponse` |
| **Estados HTTP** | 200 · 400 · 401 · 404 |
| **Errores** | `VALIDATION_ERROR` (`stockQuantity` negativo o `reason` ausente), `UNAUTHENTICATED`, `NOT_FOUND` |
| **Reglas** | RN-09, RN-19, RN-24, RN-25 |
| **Requisitos** | REQ-06.2, REQ-06.3 |
| **Historias** | HU-15 |
| **Pruebas** | CP-50, CP-53 |

El ajuste y su registro de auditoría ocurren en la misma transacción; el registro guarda `oldValue`, `newValue`, usuario, motivo y fecha (criterio CA-06-0).

## EP-16 — Cargar imagen de producto

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `POST /api/v1/admin/products/{id}/images` |
| **Headers** | `Content-Type: multipart/form-data` |
| **Path parameters** | `id` (uuid del producto) |
| **Form fields** | `file` (imagen, obligatorio), `alt` (string, obligatorio, ≤ 160), `position` (integer, opcional) |
| **Response 201** | `ProductImageResponse` con la URL ya optimizada |
| **Estados HTTP** | 201 · 400 · 401 · 404 · 413 · 415 |
| **Errores** | `VALIDATION_ERROR` (falta `alt`), `UNAUTHENTICATED`, `NOT_FOUND`, `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE` |
| **Reglas** | RN-22 |
| **Requisitos** | REQ-06.5, RNF-01, RNF-03 |
| **Historias** | HU-13 |
| **Pruebas** | CP-54, CP-80 |

`alt` es obligatorio porque RNF-03 exige texto alternativo. Formatos admitidos y tamaño máximo se declaran en `details` del error.

## EP-17 — Listar órdenes

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/admin/orders` |
| **Query parameters** | `status` (enum, repetible), `q` (número de orden o nombre del comprador), `dateFrom`, `dateTo` (`AAAA-MM-DD`), `sort` (`createdAt`, `totalCop`), `page`, `pageSize` |
| **Response 200** | `Page<OrderSummaryResponse>` |
| **Estados HTTP** | 200 · 400 · 401 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED` |
| **Reglas** | RN-19, RN-26 |
| **Requisitos** | REQ-07.1 |
| **Historias** | HU-16, HU-20 |
| **Pruebas** | CP-51, CP-60 |

## EP-18 — Cambiar estado de una orden

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `PATCH /api/v1/admin/orders/{id}/status` |
| **Path parameters** | `id` (uuid) |
| **Request body** | `OrderStatusUpdateRequest` |
| **Response 200** | `OrderResponse` |
| **Estados HTTP** | 200 · 400 · 401 · 404 · 409 |
| **Errores** | `VALIDATION_ERROR` (falta `reason` al cancelar), `UNAUTHENTICATED`, `NOT_FOUND`, `INVALID_STATE_TRANSITION` |
| **Reglas** | RN-09, RN-13, RN-27 |
| **Requisitos** | REQ-07.2, REQ-07.3, REQ-07.4 |
| **Historias** | HU-17, HU-18 |
| **Pruebas** | CP-60, CP-61, CP-62 |

Cancelar devuelve las unidades al inventario **en la misma transacción** y genera auditoría con `source = CANCELACION`.

## EP-19 — Consultar auditoría

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/admin/audit-logs` |
| **Query parameters** | `entityType`, `entityId`, `action`, `source`, `dateFrom`, `dateTo`, `page`, `pageSize` |
| **Response 200** | `Page<AuditEntryResponse>` ordenado por `createdAt:desc` |
| **Estados HTTP** | 200 · 400 · 401 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED` |
| **Reglas** | RN-24, RN-25, RN-27 |
| **Requisitos** | REQ-06.3, REQ-07.3 |
| **Historias** | HU-19 |
| **Pruebas** | CP-24, CP-50, CP-60 |

Solo lectura: no existen endpoints de modificación ni de borrado de auditoría (RN-25).

## EP-20 — Consultar notificaciones

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/admin/notifications` |
| **Query parameters** | `status` (enum), `orderNumber`, `page`, `pageSize` |
| **Response 200** | `Page<NotificationResponse>` |
| **Estados HTTP** | 200 · 400 · 401 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED` |
| **Reglas** | RN-15 |
| **Requisitos** | REQ-05.3 |
| **Historias** | HU-20 |
| **Pruebas** | CP-41 |

Es el mecanismo de degradación del riesgo R-08: si el correo falla, el administrador ve aquí qué pedidos no fueron notificados.

## EP-21 — Listar productos (administración)

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/admin/products` |
| **Query parameters** | `q`, `category`, `published` (boolean), `lowStock` (boolean), `sort`, `page`, `pageSize` |
| **Response 200** | `Page<ProductSummaryResponse>` incluyendo despublicados, con `published` explícito |
| **Estados HTTP** | 200 · 400 · 401 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED` |
| **Reglas** | RN-19 |
| **Requisitos** | REQ-06.1 |
| **Historias** | HU-13, HU-14 |
| **Pruebas** | CP-51, CP-52 |

## EP-22 — Editar producto

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `PATCH /api/v1/admin/products/{id}` |
| **Request body** | `ProductUpdateRequest` (campos opcionales; solo se aplican los enviados) |
| **Response 200** | `ProductResponse` |
| **Estados HTTP** | 200 · 400 · 401 · 404 · 409 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED`, `NOT_FOUND`, `CONFLICT` |
| **Reglas** | RN-19, RN-28 (cambiar el precio no afecta órdenes anteriores) |
| **Requisitos** | REQ-06.1 |
| **Historias** | HU-13 |
| **Pruebas** | CP-22, CP-50 |

## EP-23 — Detalle de orden (administración)

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/admin/orders/{id}` |
| **Response 200** | `OrderResponse` **sin enmascarar**: el administrador necesita la dirección completa para despachar |
| **Estados HTTP** | 200 · 401 · 404 |
| **Errores** | `UNAUTHENTICATED`, `NOT_FOUND` |
| **Reglas** | RN-19, RN-26 |
| **Requisitos** | REQ-07.1 |
| **Historias** | HU-16 |
| **Pruebas** | CP-51, CP-60 |

## EP-24 — Vista de inventario

| Campo | Valor |
| --- | --- |
| **Método y ruta** | `GET /api/v1/admin/inventory` |
| **Query parameters** | `q`, `lowStockThreshold` (integer, default 3), `page`, `pageSize` |
| **Response 200** | `Page<InventoryResponse>` ordenado por existencias ascendentes |
| **Estados HTTP** | 200 · 400 · 401 |
| **Errores** | `VALIDATION_ERROR`, `UNAUTHENTICATED` |
| **Reglas** | RN-19 |
| **Requisitos** | REQ-06.2 |
| **Historias** | HU-15 |
| **Pruebas** | CP-50 |

---

## Endpoints que deliberadamente no existen

| Endpoint ausente | Motivo |
| --- | --- |
| Registro e inicio de sesión de compradores | No hay cuentas de comprador (PDF, apartado 9.3) |
| Carrito en el servidor (`/cart` con estado) | El carrito vive en la sesión del cliente (RN-06) |
| Reserva de unidades | No previsto por el PDF; la garantía es transaccional (RN-08) |
| Pagos, reembolsos, facturación | Excluidos del alcance (RN-12) |
| Envíos y seguimiento | Excluidos del alcance |
| Borrado físico de productos u órdenes | Prohibido por RN-23 y Ley 527 de 1999 |
| Modificación o borrado de auditoría | Prohibido por RN-25 |
