# Modelos de API (DTO)

Catálogo centralizado de los objetos que viajan por la API. Cada modelo debe poder convertirse **sin reinterpretación** en un esquema Pydantic (backend) y en una interfaz TypeScript (frontend).

Reglas de lectura:

- **Obligatorio**: el campo debe estar presente en la petición o siempre viene en la respuesta.
- **Nullable**: el valor puede ser `null`.
- Tipos: `string`, `integer`, `boolean`, `uuid`, `datetime` (ISO 8601 UTC), `enum`, `array<T>`, `object`.
- Convenciones de nombres y formatos: [convenciones.md](convenciones.md).

Índice:

| Modelo | Uso |
| --- | --- |
| [`CategoryResponse`](#categoryresponse) | Respuesta |
| [`ProductSummaryResponse`](#productsummaryresponse) | Respuesta (listado) |
| [`ProductResponse`](#productresponse) | Respuesta (detalle) |
| [`ProductVariantResponse`](#productvariantresponse) | Respuesta |
| [`ProductImageResponse`](#productimageresponse) | Respuesta |
| [`CartItemRequest`](#cartitemrequest) | Petición |
| [`CartValidationRequest`](#cartvalidationrequest) | Petición |
| [`CartValidationResponse`](#cartvalidationresponse) | Respuesta |
| [`CreateOrderRequest`](#createorderrequest) | Petición |
| [`CreateOrderItemRequest`](#createorderitemrequest) | Petición |
| [`CustomerRequest`](#customerrequest) | Petición |
| [`OrderResponse`](#orderresponse) | Respuesta |
| [`OrderSummaryResponse`](#ordersummaryresponse) | Respuesta (listado admin) |
| [`OrderItemResponse`](#orderitemresponse) | Respuesta |
| [`LoginRequest` / `LoginResponse`](#loginrequest--loginresponse) | Autenticación |
| [`AdminUserResponse`](#adminuserresponse) | Respuesta |
| [`ProductCreateRequest` / `ProductUpdateRequest`](#productcreaterequest--productupdaterequest) | Petición admin |
| [`VariantRequest`](#variantrequest) | Petición admin |
| [`PublishRequest`](#publishrequest) | Petición admin |
| [`InventoryAdjustmentRequest`](#inventoryadjustmentrequest) | Petición admin |
| [`InventoryResponse`](#inventoryresponse) | Respuesta admin |
| [`OrderStatusUpdateRequest`](#orderstatusupdaterequest) | Petición admin |
| [`AuditEntryResponse`](#auditentryresponse) | Respuesta admin |
| [`NotificationResponse`](#notificationresponse) | Respuesta admin |
| [`PageMeta` y `Page<T>`](#pagemeta-y-paget) | Envoltura de colecciones |
| [`ErrorResponse`](#errorresponse) | Errores |

---

## CategoryResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador | `"7c3f…"` |
| `name` | string | Sí | No | Nombre visible | `"Camisetas"` |
| `slug` | string | Sí | No | Valor usado en el filtro `category` | `"camisetas"` |
| `productCount` | integer | Sí | No | Productos publicados en la categoría | `12` |

---

## ProductSummaryResponse

Elemento del listado de catálogo (EP-01). Contiene lo mínimo para pintar una tarjeta sin peticiones adicionales (RNF-01).

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador | `"2b91…"` |
| `slug` | string | Sí | No | Ruta del detalle | `"camiseta-oversize-negra"` |
| `name` | string | Sí | No | Nombre | `"Camiseta oversize negra"` |
| `priceCop` | integer | Sí | No | Precio en COP enteros | `85000` |
| `categoryName` | string | Sí | No | Nombre de la categoría | `"Camisetas"` |
| `imageUrl` | string | Sí | Sí | Imagen principal optimizada; `null` si no tiene | `"/media/p/2b91-800.webp"` |
| `imageAlt` | string | Sí | Sí | Texto alternativo (RNF-03) | `"Camiseta negra de corte amplio"` |
| `availableUnits` | integer | Sí | No | Suma de existencias de variantes activas | `7` |
| `inStock` | boolean | Sí | No | `availableUnits > 0` (RN-02, RN-03) | `true` |
| `sizes` | array\<string\> | Sí | No | Tallas ofrecidas, con o sin existencias | `["S","M","L"]` |

---

## ProductResponse

Detalle de producto (EP-03). Extiende el resumen con descripción, imágenes y variantes.

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador | `"2b91…"` |
| `slug` | string | Sí | No | Ruta pública | `"camiseta-oversize-negra"` |
| `name` | string | Sí | No | Nombre | `"Camiseta oversize negra"` |
| `description` | string | Sí | Sí | Descripción | `"Algodón 100 %…"` |
| `priceCop` | integer | Sí | No | Precio | `85000` |
| `category` | [`CategoryResponse`](#categoryresponse) | Sí | No | Categoría | — |
| `images` | array\<[`ProductImageResponse`](#productimageresponse)\> | Sí | No | Imágenes ordenadas; puede ser `[]` | — |
| `variants` | array\<[`ProductVariantResponse`](#productvariantresponse)\> | Sí | No | Variantes activas; al menos una si está publicado (RN-21) | — |
| `availableUnits` | integer | Sí | No | Suma de existencias | `7` |
| `inStock` | boolean | Sí | No | Disponibilidad general | `true` |
| `published` | boolean | Sí | No | Siempre `true` en el endpoint público | `true` |
| `updatedAt` | datetime | Sí | No | Última modificación | `"2026-04-10T18:05:00Z"` |

---

## ProductVariantResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | **Identificador que se usa para comprar** (RN-05) | `"9a4c…"` |
| `sku` | string | Sí | No | Código interno | `"CAM-OVR-NEG-M"` |
| `size` | string | Sí | No | Talla | `"M"` |
| `availableUnits` | integer | Sí | No | Existencias de esta variante | `3` |
| `inStock` | boolean | Sí | No | `availableUnits > 0` | `true` |

---

## ProductImageResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `url` | string | Sí | No | Ruta servida por C2/C5 | `"/media/p/2b91-800.webp"` |
| `alt` | string | Sí | No | Texto alternativo (obligatorio por RNF-03) | `"Camiseta negra vista frontal"` |
| `position` | integer | Sí | No | Orden de presentación, desde 0 | `0` |
| `width` | integer | Sí | No | Ancho en píxeles | `800` |
| `height` | integer | Sí | No | Alto en píxeles | `800` |

`width` y `height` se envían para que el frontend reserve espacio y evite saltos de diseño (contribuye a RNF-01).

---

## CartItemRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `variantId` | uuid | Sí | No | Debe existir y estar activa | `"9a4c…"` |
| `quantity` | integer | Sí | No | `>= 1`, `<= 20` | `2` |

El tope de 20 unidades por línea es `DECISIÓN PROPUESTA`: evita peticiones absurdas sin afectar la operación de un micronegocio.

---

## CartValidationRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `items` | array\<[`CartItemRequest`](#cartitemrequest)\> | Sí | No | 1 a 50 elementos, `variantId` único | — |

---

## CartValidationResponse

Resultado **informativo**: no reserva unidades (RN-06).

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `valid` | boolean | Sí | No | `true` si todas las líneas son satisfacibles ahora | `false` |
| `items` | array\<object\> | Sí | No | Resultado por línea | — |
| `items[].variantId` | uuid | Sí | No | Variante evaluada | `"9a4c…"` |
| `items[].productName` | string | Sí | No | Nombre para mostrar | `"Camiseta oversize negra"` |
| `items[].size` | string | Sí | No | Talla | `"M"` |
| `items[].requestedQuantity` | integer | Sí | No | Cantidad solicitada | `5` |
| `items[].availableUnits` | integer | Sí | No | Existencias al momento de consultar | `3` |
| `items[].available` | boolean | Sí | No | `availableUnits >= requestedQuantity` | `false` |
| `items[].unitPriceCop` | integer | Sí | No | Precio unitario vigente | `85000` |
| `totalCop` | integer | Sí | No | Total de las líneas satisfacibles | `255000` |
| `checkedAt` | datetime | Sí | No | Momento de la comprobación | `"2026-04-15T14:30:00Z"` |

---

## CustomerRequest

Datos personales mínimos (RN-17). Cada campo tiene finalidad declarada.

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Finalidad | Ejemplo |
| --- | --- | --- | --- | --- | --- | --- |
| `name` | string | Sí | No | 3–120 caracteres | Identificar al destinatario | `"Ana Ríos"` |
| `email` | string | Sí | No | Formato correo, ≤ 160 | Notificación (REQ-05) y consulta de la orden | `"ana@example.com"` |
| `phone` | string | Sí | No | 7–15 dígitos, opcional `+` | Coordinar la entrega | `"+573001234567"` |
| `address` | string | Sí | No | 5–200 caracteres | Entrega | `"Calle 45 # 12-34, apto 201"` |
| `city` | string | Sí | No | 2–80 caracteres | Entrega | `"Bogotá D.C."` |

---

## CreateOrderItemRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `variantId` | uuid | Sí | No | Variante activa y existente | `"9a4c…"` |
| `quantity` | integer | Sí | No | `>= 1`, `<= 20` | `2` |

---

## CreateOrderRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `items` | array\<[`CreateOrderItemRequest`](#createorderitemrequest)\> | Sí | No | 1–50 elementos, `variantId` único (RN-29) | — |
| `customer` | [`CustomerRequest`](#customerrequest) | Sí | No | — | — |
| `dataProcessingConsent` | boolean | Sí | No | Debe ser `true`; si no, `CONSENT_REQUIRED` (RN-16) | `true` |
| `privacyNoticeVersion` | string | Sí | No | Versión del aviso mostrado, p. ej. `"1.0"` | `"1.0"` |

Ejemplo:

```json
{
  "items": [{ "variantId": "9a4c0f2e-1f4b-4a8e-9f1e-2c7d6b5a4321", "quantity": 2 }],
  "customer": {
    "name": "Ana Ríos",
    "email": "ana@example.com",
    "phone": "+573001234567",
    "address": "Calle 45 # 12-34, apto 201",
    "city": "Bogotá D.C."
  },
  "dataProcessingConsent": true,
  "privacyNoticeVersion": "1.0"
}
```

---

## OrderItemResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `variantId` | uuid | Sí | No | Variante comprada | `"9a4c…"` |
| `productName` | string | Sí | No | Nombre congelado (RN-28) | `"Camiseta oversize negra"` |
| `size` | string | Sí | No | Talla congelada | `"M"` |
| `quantity` | integer | Sí | No | Unidades | `2` |
| `unitPriceCop` | integer | Sí | No | Precio unitario congelado | `85000` |
| `lineTotalCop` | integer | Sí | No | `quantity * unitPriceCop` | `170000` |

---

## OrderResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador interno | `"0f2e…"` |
| `orderNumber` | string | Sí | No | Identificador público (REQ-03.3) | `"TL-20260415-00042"` |
| `status` | enum | Sí | No | `CONFIRMADA` \| `PREPARADA` \| `ENTREGADA` \| `CANCELADA` | `"CONFIRMADA"` |
| `items` | array\<[`OrderItemResponse`](#orderitemresponse)\> | Sí | No | Al menos una línea | — |
| `totalCop` | integer | Sí | No | Total de la orden | `170000` |
| `customer` | object | Sí | No | Datos de entrega (ver nota) | — |
| `customer.name` | string | Sí | No | Nombre | `"Ana Ríos"` |
| `customer.email` | string | Sí | No | Correo | `"ana@example.com"` |
| `customer.phone` | string | Sí | No | Teléfono | `"+573001234567"` |
| `customer.address` | string | Sí | No | Dirección | `"Calle 45 # 12-34"` |
| `customer.city` | string | Sí | No | Ciudad | `"Bogotá D.C."` |
| `simulatedCheckout` | boolean | Sí | No | Siempre `true`; el frontend muestra el aviso (RN-12) | `true` |
| `dataProcessingConsent` | boolean | Sí | No | Autorización registrada | `true` |
| `privacyNoticeVersion` | string | Sí | No | Versión aceptada | `"1.0"` |
| `createdAt` | datetime | Sí | No | Confirmación | `"2026-04-15T14:32:05Z"` |
| `updatedAt` | datetime | Sí | No | Último cambio de estado | `"2026-04-15T14:32:05Z"` |

Nota: en la consulta pública (EP-06) los datos del comprador se devuelven **enmascarados** salvo los necesarios para reconocer la orden: `email` y `phone` se muestran parcialmente (`a***@example.com`). Es `DECISIÓN PROPUESTA` para reducir el impacto si alguien obtiene el número de orden (RN-18, RNF-04).

---

## OrderSummaryResponse

Elemento del listado administrativo (EP-17).

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador | `"0f2e…"` |
| `orderNumber` | string | Sí | No | Número público | `"TL-20260415-00042"` |
| `status` | enum | Sí | No | Estado actual | `"CONFIRMADA"` |
| `totalCop` | integer | Sí | No | Total | `170000` |
| `itemCount` | integer | Sí | No | Número de líneas | `1` |
| `customerName` | string | Sí | No | Nombre del comprador | `"Ana Ríos"` |
| `shippingCity` | string | Sí | No | Ciudad de entrega | `"Bogotá D.C."` |
| `notificationStatus` | enum | Sí | No | `PENDIENTE` \| `ENVIADA` \| `FALLIDA` (RN-15) | `"ENVIADA"` |
| `createdAt` | datetime | Sí | No | Fecha | `"2026-04-15T14:32:05Z"` |

---

## LoginRequest / LoginResponse

`LoginRequest`

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `email` | string | Sí | No | Formato correo | `"admin@tiendalocal.co"` |
| `password` | string | Sí | No | 8–128 caracteres | `"********"` |

`LoginResponse`

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `accessToken` | string | Sí | No | Token para `Authorization: Bearer` | `"eyJhbGciOi…"` |
| `tokenType` | string | Sí | No | Siempre `"Bearer"` | `"Bearer"` |
| `expiresIn` | integer | Sí | No | Vigencia en segundos | `28800` |
| `user` | [`AdminUserResponse`](#adminuserresponse) | Sí | No | Usuario autenticado | — |

---

## AdminUserResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador | `"5d17…"` |
| `email` | string | Sí | No | Correo de acceso | `"admin@tiendalocal.co"` |
| `fullName` | string | Sí | No | Nombre mostrado y usado en auditoría | `"Propietaria"` |

Nunca se expone `passwordHash` ni ningún derivado de la contraseña (RN-20).

---

## ProductCreateRequest / ProductUpdateRequest

`ProductCreateRequest` (EP-12) — un único formulario, con variantes y existencias iniciales (REQ-06.4).

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `name` | string | Sí | No | 3–120 caracteres | `"Camiseta oversize negra"` |
| `description` | string | No | Sí | ≤ 2000 caracteres | `"Algodón 100 %…"` |
| `priceCop` | integer | Sí | No | `> 0` | `85000` |
| `categoryId` | uuid | Sí | No | Categoría existente | `"7c3f…"` |
| `variants` | array\<[`VariantRequest`](#variantrequest)\> | Sí | No | 1–20 elementos, talla única | — |
| `published` | boolean | No | No | Default `false` | `false` |

`ProductUpdateRequest` (EP-12, PATCH): mismos campos, **todos opcionales**; se aplican solo los enviados. `variants` no se modifica aquí (se usa EP-14) para evitar borrados accidentales.

---

## VariantRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `size` | string | Sí | No | 1–20 caracteres, única dentro del producto | `"M"` |
| `sku` | string | No | Sí | Si se omite, lo genera el backend | `"CAM-OVR-NEG-M"` |
| `initialStock` | integer | Sí | No | `>= 0` | `5` |
| `active` | boolean | No | No | Default `true` | `true` |

---

## PublishRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `published` | boolean | Sí | No | Publicar requiere al menos una variante activa (RN-21) | `true` |

---

## InventoryAdjustmentRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `stockQuantity` | integer | Sí | No | `>= 0` — es el **valor final**, no un delta | `12` |
| `reason` | string | Sí | No | 3–120 caracteres; se guarda en auditoría | `"Conteo físico del 15/04"` |

Se usa el valor final y no un incremento para que el administrador vea en pantalla exactamente lo que quedará almacenado (RNF-05) y para que la auditoría registre `old_value` y `new_value` sin ambigüedad (REQ-06.3). `DECISIÓN PROPUESTA`.

---

## InventoryResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `variantId` | uuid | Sí | No | Variante | `"9a4c…"` |
| `sku` | string | Sí | No | Código | `"CAM-OVR-NEG-M"` |
| `productName` | string | Sí | No | Producto | `"Camiseta oversize negra"` |
| `size` | string | Sí | No | Talla | `"M"` |
| `stockQuantity` | integer | Sí | No | Existencias actuales | `12` |
| `updatedAt` | datetime | Sí | No | Última variación | `"2026-04-15T14:40:00Z"` |

---

## OrderStatusUpdateRequest

| Campo | Tipo | Obligatorio | Nullable | Restricciones | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `status` | enum | Sí | No | `PREPARADA` \| `ENTREGADA` \| `CANCELADA`; transición válida según RN-13 | `"PREPARADA"` |
| `reason` | string | Condicional | Sí | Obligatorio cuando `status = CANCELADA`; 3–120 caracteres | `"El comprador desistió"` |

---

## AuditEntryResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador | `"c8b2…"` |
| `entityType` | enum | Sí | No | `INVENTORY` \| `ORDER` \| `PRODUCT` | `"INVENTORY"` |
| `entityId` | uuid | Sí | No | Entidad afectada | `"9a4c…"` |
| `action` | enum | Sí | No | `STOCK_CHANGE` \| `STATUS_CHANGE` \| `PUBLISH_CHANGE` | `"STOCK_CHANGE"` |
| `source` | enum | Sí | No | `AJUSTE_MANUAL` \| `ORDEN` \| `CANCELACION` | `"ORDEN"` |
| `oldValue` | string | Sí | Sí | Valor anterior | `"10"` |
| `newValue` | string | Sí | No | Valor nuevo | `"8"` |
| `performedBy` | string | Sí | Sí | Nombre del administrador; `null` si el origen fue una orden del comprador | `"Propietaria"` |
| `reason` | string | Sí | Sí | Motivo informado en el ajuste | `"Conteo físico del 15/04"` |
| `createdAt` | datetime | Sí | No | Fecha del cambio | `"2026-04-15T14:40:00Z"` |

---

## NotificationResponse

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `id` | uuid | Sí | No | Identificador | `"3ae1…"` |
| `orderNumber` | string | Sí | No | Orden asociada | `"TL-20260415-00042"` |
| `recipientType` | enum | Sí | No | `COMPRADOR` \| `ADMINISTRADOR` | `"COMPRADOR"` |
| `recipient` | string | Sí | No | Dirección de envío | `"ana@example.com"` |
| `status` | enum | Sí | No | `PENDIENTE` \| `ENVIADA` \| `FALLIDA` | `"FALLIDA"` |
| `attempts` | integer | Sí | No | Intentos realizados | `3` |
| `lastError` | string | Sí | Sí | Motivo del último fallo | `"Cuota diaria agotada"` |
| `createdAt` | datetime | Sí | No | Creación | `"2026-04-15T14:32:06Z"` |
| `sentAt` | datetime | Sí | Sí | Envío efectivo | `null` |

---

## PageMeta y Page\<T\>

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `items` | array\<T\> | Sí | No | Elementos de la página; `[]` si no hay | — |
| `meta.page` | integer | Sí | No | Página actual | `1` |
| `meta.pageSize` | integer | Sí | No | Tamaño solicitado | `12` |
| `meta.totalItems` | integer | Sí | No | Total de coincidencias | `37` |
| `meta.totalPages` | integer | Sí | No | Total de páginas | `4` |

---

## ErrorResponse

Estructura única de error. Detalle y catálogo de códigos: [errores.md](errores.md).

| Campo | Tipo | Obligatorio | Nullable | Descripción | Ejemplo |
| --- | --- | --- | --- | --- | --- |
| `error.code` | string | Sí | No | Código estable en inglés | `"INSUFFICIENT_STOCK"` |
| `error.message` | string | Sí | No | Texto legible en español, **no apto para lógica** | `"No hay unidades suficientes"` |
| `error.details` | object | Sí | No | Contexto estructurado; `{}` si no aplica | — |
| `error.requestId` | string | Sí | No | Identificador de la petición para soporte | `"req_01HX…"` |

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "No hay unidades suficientes para completar el pedido",
    "details": {
      "items": [
        { "variantId": "9a4c0f2e-…", "productName": "Camiseta oversize negra", "size": "M", "requestedQuantity": 2, "availableUnits": 0 }
      ]
    },
    "requestId": "req_01HX8Z5K"
  }
}
```

---

## Equivalencias de tipos

| Tipo del contrato | Pydantic (backend) | TypeScript (frontend) |
| --- | --- | --- |
| `string` | `str` | `string` |
| `integer` | `int` | `number` |
| `boolean` | `bool` | `boolean` |
| `uuid` | `UUID` | `string` |
| `datetime` | `datetime` (UTC) | `string` (ISO) |
| `enum` | `Literal[...]` o `StrEnum` | unión de literales |
| `array<T>` | `list[T]` | `T[]` |
| campo nullable | `T \| None` | `T \| null` |
| campo opcional en petición | valor por defecto declarado | `?:` |
