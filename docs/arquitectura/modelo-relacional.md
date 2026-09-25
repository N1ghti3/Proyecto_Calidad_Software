# Modelo relacional (PostgreSQL)

Especificación física de las entidades del [modelo ER](modelo-er.md). **Es documentación, no migración:** en esta fase no se crean tablas ni scripts (regla del alcance de la fase de ingeniería).

Convenciones aplicadas (ver [`../api/convenciones.md`](../api/convenciones.md)):

- nombres de tabla en `snake_case` y **singular**;
- claves primarias `uuid`, generadas por la aplicación o por la base de datos;
- fechas en `timestamptz`, siempre en UTC;
- dinero en `bigint` con el importe en **pesos colombianos enteros** (sin decimales), sufijo `_cop`;
- booleanos con prefijo verbal (`published`, `active`);
- toda tabla con datos mutables lleva `created_at` y `updated_at`.

> `order` es palabra reservada en SQL: la tabla se llama **`order_header`** y el recurso de API sigue llamándose `order`.

---

## `category`

**Propósito:** agrupar productos para el filtro del catálogo (REQ-01).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `name` | varchar(80) | Sí | No | — | — | Sí | — | `length(name) >= 2` | Nombre visible |
| `slug` | varchar(90) | Sí | No | — | — | Sí | — | minúsculas, `[a-z0-9-]+` | Identificador legible usado en la API |
| `created_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Alta |

Índices: `UNIQUE(slug)`, `UNIQUE(name)`.

---

## `product`

**Propósito:** artículo ofrecido y su estado de publicación (REQ-01, REQ-06).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `category_id` | uuid | Sí | No | — | `category.id` | No | — | `ON DELETE RESTRICT` | Categoría |
| `name` | varchar(120) | Sí | No | — | — | No | — | `length(name) >= 3` | Nombre |
| `slug` | varchar(140) | Sí | No | — | — | Sí | — | `[a-z0-9-]+` | Ruta pública del detalle |
| `description` | text | No | Sí | — | — | No | `NULL` | ≤ 2 000 caracteres | Descripción |
| `price_cop` | bigint | Sí | No | — | — | No | — | `price_cop > 0` | Precio unitario en COP enteros |
| `published` | boolean | Sí | No | — | — | No | `false` | — | Visible en el catálogo público (RN-01) |
| `created_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Alta |
| `updated_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Última modificación |

Índices: `UNIQUE(slug)`; `INDEX(category_id)`; `INDEX(published)`; índice de texto sobre `name` sin distinción de mayúsculas ni tildes, para REQ-01.3 (CA-01-2).

Regla: el precio vive en el producto, no en la variante — el PDF no contempla precios distintos por talla. Si el negocio lo pidiera, sería un cambio de contrato (ver `../api/README.md`, sección de control de cambios).

---

## `product_variant`

**Propósito:** unidad vendible (talla) — RN-05.

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `product_id` | uuid | Sí | No | — | `product.id` | No | — | `ON DELETE RESTRICT` | Producto padre |
| `sku` | varchar(40) | Sí | No | — | — | Sí | — | mayúsculas, `[A-Z0-9-]+` | Código interno |
| `size` | varchar(20) | Sí | No | — | — | No | — | valor del catálogo de tallas | Talla |
| `active` | boolean | Sí | No | — | — | No | `true` | — | Variante ofrecida actualmente |
| `created_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Alta |

Índices y restricciones: `UNIQUE(sku)`; `UNIQUE(product_id, size)` (una talla no se repite dentro del producto); `INDEX(product_id)`.

---

## `inventory`

**Propósito:** existencias por variante. Es la fuente única de verdad del proyecto (causa C-01, RNF-02).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `variant_id` | uuid | Sí | No | Sí | `product_variant.id` | Sí | — | `ON DELETE RESTRICT` | Clave primaria y foránea a la vez (1:1) |
| `stock_quantity` | integer | Sí | No | — | — | No | `0` | **`CHECK (stock_quantity >= 0)`** | Unidades disponibles |
| `updated_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Última variación |

- La restricción `CHECK` es la última línea de defensa de RN-09: aunque la lógica de negocio fallara, la base de datos rechaza el inventario negativo.
- Las filas de esta tabla son las que se bloquean durante la confirmación de la orden (RN-10, ADR-005).
- Toda escritura aquí genera un registro en `audit_log` dentro de la misma transacción (RN-24).

---

## `product_image`

**Propósito:** imágenes optimizadas del catálogo (componente C5, RNF-01).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `product_id` | uuid | Sí | No | — | `product.id` | No | — | `ON DELETE CASCADE` | Producto |
| `url` | text | Sí | No | — | — | No | — | ruta relativa servida por C2/C5 | Ubicación del archivo optimizado |
| `alt_text` | varchar(160) | Sí | No | — | — | No | — | no vacío | Texto alternativo — obligatorio por RNF-03 |
| `position` | smallint | Sí | No | — | — | No | `0` | `position >= 0` | Orden de presentación |

Índices: `UNIQUE(product_id, position)`; `INDEX(product_id)`.

`alt_text` es obligatorio en el esquema porque la accesibilidad (RNF-03) exige texto alternativo en las imágenes del catálogo; dejarlo opcional trasladaría un requisito verificable a la buena voluntad de quien carga el producto.

---

## `order_header`

**Propósito:** orden confirmada, datos de entrega y constancia de autorización (REQ-03, REQ-04, REQ-07, REQ-08).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador interno |
| `order_number` | varchar(20) | Sí | No | — | — | Sí | — | formato `TL-AAAAMMDD-XXXXX` | Identificador público único (REQ-03.3) |
| `status` | varchar(20) | Sí | No | — | — | No | `'CONFIRMADA'` | `IN ('CONFIRMADA','PREPARADA','ENTREGADA','CANCELADA')` | Estado (RN-13) |
| `total_cop` | bigint | Sí | No | — | — | No | — | `total_cop > 0` | Total de la orden |
| `customer_name` | varchar(120) | Sí | No | — | — | No | — | no vacío | Dato personal — finalidad: entrega |
| `customer_email` | varchar(160) | Sí | No | — | — | No | — | formato correo | Dato personal — finalidad: notificación (REQ-05) |
| `customer_phone` | varchar(20) | Sí | No | — | — | No | — | 7–15 dígitos | Dato personal — finalidad: coordinación de entrega |
| `shipping_address` | varchar(200) | Sí | No | — | — | No | — | no vacío | Dato personal — finalidad: entrega |
| `shipping_city` | varchar(80) | Sí | No | — | — | No | — | no vacío | Dato personal — finalidad: entrega |
| `data_processing_consent` | boolean | Sí | No | — | — | No | — | `CHECK (data_processing_consent = true)` | Autorización expresa (RN-16) |
| `privacy_notice_version` | varchar(20) | Sí | No | — | — | No | — | — | Versión del aviso aceptado (CA-08-2) |
| `consent_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Momento de la autorización |
| `created_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Confirmación |
| `updated_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Último cambio de estado |

Índices: `UNIQUE(order_number)`; `INDEX(status, created_at DESC)` para el panel (REQ-07.1); `INDEX(lower(customer_email))` para la consulta del comprador (RN-18).

**Campos que deliberadamente no existen:** ningún dato de tarjeta, medio de pago, documento de identidad, fecha de nacimiento ni geolocalización. Cada columna personal declara su finalidad (RN-17, RNF-04).

---

## `order_item`

**Propósito:** línea de orden con copia de los datos del momento (RN-28).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `order_id` | uuid | Sí | No | — | `order_header.id` | No | — | `ON DELETE RESTRICT` | Orden |
| `variant_id` | uuid | Sí | No | — | `product_variant.id` | No | — | `ON DELETE RESTRICT` | Variante comprada |
| `product_name` | varchar(120) | Sí | No | — | — | No | — | — | Copia del nombre al confirmar |
| `size` | varchar(20) | Sí | No | — | — | No | — | — | Copia de la talla |
| `quantity` | integer | Sí | No | — | — | No | — | `quantity > 0` | Unidades |
| `unit_price_cop` | bigint | Sí | No | — | — | No | — | `unit_price_cop > 0` | Precio unitario congelado |
| `line_total_cop` | bigint | Sí | No | — | — | No | — | `= quantity * unit_price_cop` | Total de la línea |

Índices: `UNIQUE(order_id, variant_id)` (una variante aparece una sola vez por orden; cantidades se suman antes de crear la orden); `INDEX(order_id)`.

`ON DELETE RESTRICT` sobre `variant_id` implementa RN-23: un producto vendido no puede desaparecer del histórico.

---

## `admin_user`

**Propósito:** operador autenticado del panel (REQ-06, RNF-04).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `email` | varchar(160) | Sí | No | — | — | Sí | — | formato correo, minúsculas | Usuario de acceso |
| `password_hash` | text | Sí | No | — | — | No | — | resultado de función de derivación de clave | **Nunca** la contraseña (RN-20) |
| `full_name` | varchar(120) | Sí | No | — | — | No | — | — | Nombre para la auditoría |
| `active` | boolean | Sí | No | — | — | No | `true` | — | Permite revocar acceso sin borrar historial |
| `last_login_at` | timestamptz | No | Sí | — | — | — | `NULL` | — | Último ingreso |
| `created_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Alta |

---

## `audit_log`

**Propósito:** evidencia de variaciones de inventario y de estados de orden (componente C6; REQ-06.3, REQ-07.3).

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `admin_user_id` | uuid | No | Sí | — | `admin_user.id` | No | `NULL` | `ON DELETE RESTRICT` | Usuario responsable; nulo cuando el origen es una orden del comprador |
| `entity_type` | varchar(30) | Sí | No | — | — | No | — | `IN ('INVENTORY','ORDER','PRODUCT')` | Entidad afectada |
| `entity_id` | uuid | Sí | No | — | — | No | — | — | Identificador de la entidad afectada |
| `action` | varchar(30) | Sí | No | — | — | No | — | `IN ('STOCK_CHANGE','STATUS_CHANGE','PUBLISH_CHANGE')` | Tipo de cambio |
| `source` | varchar(20) | Sí | No | — | — | No | — | `IN ('AJUSTE_MANUAL','ORDEN','CANCELACION')` | Origen del cambio (REQ-06.3) |
| `old_value` | varchar(120) | No | Sí | — | — | No | `NULL` | — | Valor anterior |
| `new_value` | varchar(120) | Sí | No | — | — | No | — | — | Valor nuevo |
| `created_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Fecha del cambio |

Índices: `INDEX(entity_type, entity_id, created_at DESC)`; `INDEX(created_at DESC)`.

Tabla de solo anexado (RN-25): la aplicación no expone actualización ni borrado.

---

## `notification`

**Propósito:** estado de los avisos de confirmación (REQ-05, riesgo R-08). `DECISIÓN PROPUESTA`.

| Campo | Tipo | Obligatorio | Nullable | PK | FK | Unique | Default | Restricciones | Descripción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Sí | — | Sí | `gen_random_uuid()` | — | Identificador |
| `order_id` | uuid | Sí | No | — | `order_header.id` | No | — | `ON DELETE RESTRICT` | Orden notificada |
| `recipient_type` | varchar(20) | Sí | No | — | — | No | — | `IN ('COMPRADOR','ADMINISTRADOR')` | Destinatario |
| `recipient` | varchar(160) | Sí | No | — | — | No | — | formato correo | Dirección de envío |
| `status` | varchar(20) | Sí | No | — | — | No | `'PENDIENTE'` | `IN ('PENDIENTE','ENVIADA','FALLIDA')` | Estado del envío |
| `attempts` | smallint | Sí | No | — | — | No | `0` | `attempts >= 0` | Intentos realizados |
| `last_error` | varchar(200) | No | Sí | — | — | No | `NULL` | — | Motivo del último fallo |
| `created_at` | timestamptz | Sí | No | — | — | — | `now()` | — | Creación |
| `sent_at` | timestamptz | No | Sí | — | — | — | `NULL` | — | Envío efectivo |

Índices: `INDEX(order_id)`; `INDEX(status)` para el panel (RN-15).

---

## Transacción crítica (RNF-02) — descripción, no implementación

Secuencia prevista al confirmar una orden. La justificación y las alternativas están en [`../decisiones/ADR-005-concurrencia.md`](../decisiones/ADR-005-concurrencia.md).

1. Validar formato, consentimiento (RN-16) y cantidades (RN-29) **antes** de abrir la transacción.
2. `BEGIN`.
3. Bloquear las filas de `inventory` de todas las variantes solicitadas, **ordenadas por `variant_id` ascendente** (RN-10), con bloqueo exclusivo de fila.
4. Verificar, línea por línea, que `stock_quantity >= quantity`. Si alguna falla: `ROLLBACK` y responder `INSUFFICIENT_STOCK` con el detalle (RN-11).
5. Descontar `stock_quantity` de cada variante.
6. Insertar `order_header` y sus `order_item` con precios congelados (RN-28).
7. Insertar un `audit_log` por variante con `source = 'ORDEN'` (RN-24).
8. `COMMIT`.
9. **Fuera de la transacción**: crear las `notification` y despacharlas de forma asíncrona (RN-14, RN-15).

Invariante verificable al final de la prueba de concurrencia (CP-90): `stock_inicial = stock_final + unidades_confirmadas`.
