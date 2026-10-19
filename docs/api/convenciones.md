# Convenciones de nombres y formatos

**Regla oficial única.** Si el código no coincide con este documento, se corrige el código o se actualiza el contrato mediante el procedimiento de [README.md](README.md#control-de-cambios); nunca se inventa un nombre alternativo.

Registro de la decisión: [`../decisiones/ADR-003-convenciones-api.md`](../decisiones/ADR-003-convenciones-api.md). `DECISIÓN PROPUESTA` — el PDF no define convenciones.

## Regla base por plano

| Plano | Estilo | Ejemplo |
| --- | --- | --- |
| Base de datos (PostgreSQL) | `snake_case`, tabla singular | `product_variant.stock_quantity` |
| API (JSON) | `camelCase` | `availableUnits` |
| TypeScript (frontend) | `camelCase` para campos, `PascalCase` para tipos | `interface ProductResponse { availableUnits: number }` |
| Python (backend) | `snake_case` interno; los esquemas de la API traducen a `camelCase` al serializar | `available_units` → `availableUnits` |
| Rutas HTTP | `kebab-case`, sustantivos en **plural** | `/api/v1/products`, `/api/v1/admin/audit-logs` |

**La traducción ocurre en un solo lugar:** los esquemas de la capa de interfaz de C3. Ni el frontend ni la base de datos hacen conversiones ad hoc.

## Identificadores

| Regla | Detalle |
| --- | --- |
| Tipo | UUID v4 en formato canónico, como cadena en JSON |
| Nombre | `id` para el propio recurso; `<entidad>Id` para referencias (`variantId`, `orderId`, `categoryId`) |
| Identificador público de orden | `orderNumber`, formato `TL-AAAAMMDD-XXXXX` (ejemplo `TL-20260415-00042`). Es el que ve el comprador |
| Rutas legibles | `slug` en minúsculas con guiones, para producto y categoría; el detalle público se consulta por `slug` |
| Prohibido | Exponer identificadores secuenciales que permitan enumerar órdenes o clientes |

## Fechas y horas

| Regla | Detalle |
| --- | --- |
| Formato | ISO 8601 con zona, siempre **UTC**: `2026-04-15T14:32:05Z` |
| Tipo en base de datos | `timestamptz` |
| Nombres | `createdAt`, `updatedAt`, `sentAt`, `consentAt` — sufijo `At` |
| Presentación local | Responsabilidad del frontend (America/Bogota, UTC−05:00); la API nunca envía hora local |
| Fechas sin hora | `date` en formato `AAAA-MM-DD` (no se usa en el alcance actual) |

## Booleanos

| Regla | Detalle |
| --- | --- |
| Nombres | Afirmativos, sin negación: `published`, `active`, `inStock`, `dataProcessingConsent` |
| Prohibido | `notPublished`, `disabled`, `isNotActive` |
| Prefijo `is` | Solo en modelos de vista del frontend, nunca en el JSON de la API |

## Dinero

| Regla | Detalle |
| --- | --- |
| Moneda | Peso colombiano (COP) exclusivamente — el PDF excluye múltiples monedas |
| Tipo | Entero (`integer` en JSON, `bigint` en base de datos). **Sin decimales**: el COP no usa centavos en el comercio minorista |
| Nombres | Sufijo `Cop` en la API (`priceCop`, `unitPriceCop`, `lineTotalCop`, `totalCop`); `_cop` en base de datos |
| Prohibido | Números de punto flotante y cadenas con formato (`"$ 85.000"`); el formato es responsabilidad del frontend |
| Ejemplo | `"priceCop": 85000` se presenta como `$ 85.000` |

## Cantidades

| Regla | Detalle |
| --- | --- |
| Tipo | Entero no negativo |
| Nombres | `quantity` (lo que se pide), `availableUnits` (lo que hay), `stockQuantity` (valor administrativo de la variante) |
| Reglas | `quantity >= 1` en peticiones; `availableUnits >= 0` siempre |

## Enumeraciones

| Regla | Detalle |
| --- | --- |
| Formato | `SCREAMING_SNAKE_CASE`, valor estable en **español** para estados de negocio y en **inglés** para códigos técnicos de error |
| Estados de orden | `CONFIRMADA`, `PREPARADA`, `ENTREGADA`, `CANCELADA` |
| Origen de auditoría | `AJUSTE_MANUAL`, `ORDEN`, `CANCELACION` |
| Acción de auditoría | `STOCK_CHANGE`, `STATUS_CHANGE`, `PUBLISH_CHANGE` |
| Estado de notificación | `PENDIENTE`, `ENVIADA`, `FALLIDA` |
| Destinatario | `COMPRADOR`, `ADMINISTRADOR` |
| Códigos de error | Inglés, `SCREAMING_SNAKE_CASE`: `INSUFFICIENT_STOCK` (ver [errores.md](errores.md)) |
| Regla de evolución | Agregar un valor a una enumeración es **cambio compatible**; el frontend debe tratar un valor desconocido sin romperse |

Los textos que ve el usuario nunca se derivan del valor crudo: el frontend mantiene su propio diccionario de etiquetas.

## Paginación

Todas las colecciones se paginan con el mismo esquema.

| Parámetro | Tipo | Default | Máximo | Descripción |
| --- | --- | --- | --- | --- |
| `page` | integer ≥ 1 | 1 | — | Número de página |
| `pageSize` | integer ≥ 1 | 12 | 50 | Elementos por página |

Respuesta:

```json
{
  "items": [],
  "meta": { "page": 1, "pageSize": 12, "totalItems": 37, "totalPages": 4 }
}
```

Reglas: `items` siempre es un arreglo (vacío si no hay resultados, nunca `null`); una página fuera de rango devuelve `items: []` con `meta` coherente, no un error.

## Filtros

| Regla | Detalle |
| --- | --- |
| Nombres | `camelCase` en la cadena de consulta: `category`, `size`, `inStock`, `status` |
| Valores múltiples | Repetición del parámetro: `?size=M&size=L` (equivale a OR dentro del mismo filtro) |
| Combinación | Filtros distintos se combinan con AND |
| Búsqueda de texto | Parámetro `q`, mínimo 2 caracteres, sin distinción de mayúsculas ni tildes |
| Valores no válidos | `VALIDATION_ERROR` (400); nunca se ignoran en silencio |

## Ordenamiento

| Regla | Detalle |
| --- | --- |
| Parámetro | `sort` |
| Formato | `campo:direccion`, con `asc` o `desc`: `?sort=priceCop:asc` |
| Valores admitidos por recurso | Productos: `name`, `priceCop`, `createdAt`. Órdenes: `createdAt`, `totalCop` |
| Default | Productos `createdAt:desc`; órdenes `createdAt:desc` |
| Valor no admitido | `VALIDATION_ERROR` |

## Cabeceras

| Cabecera | Uso |
| --- | --- |
| `Content-Type: application/json; charset=utf-8` | Peticiones y respuestas con cuerpo (excepto carga de imagen: `multipart/form-data`) |
| `Authorization: Bearer <token>` | Endpoints `/admin` |
| `Accept-Language` | No se usa: la interfaz es únicamente en español (el PDF excluye internacionalización) |

## Reglas transversales de la API

1. Las respuestas nunca devuelven `null` en colecciones; usan arreglo vacío.
2. Un campo ausente y un campo `null` significan lo mismo: sin valor. No se usan cadenas vacías como marcador.
3. Los campos desconocidos en una petición se **rechazan** con `VALIDATION_ERROR` (evita que un error de nombre pase inadvertido entre frontend y backend).
4. Toda respuesta de error usa la estructura única de [errores.md](errores.md).
5. Ningún endpoint devuelve datos personales de un comprador sin autenticación, salvo la consulta de la propia orden (RN-18).
6. Las rutas nunca incluyen verbos; la acción la indica el método HTTP. Excepción documentada: las transiciones de estado se expresan como subrecurso (`/status`).

## Ejemplo de coherencia entre planos

| Concepto | Base de datos | API (JSON) | TypeScript |
| --- | --- | --- | --- |
| Existencias de la variante | `inventory.stock_quantity` | `availableUnits` | `availableUnits: number` |
| Precio | `product.price_cop` | `priceCop` | `priceCop: number` |
| Imagen principal | `product_image.url` | `imageUrl` | `imageUrl: string \| null` |
| Texto alternativo | `product_image.alt_text` | `imageAlt` | `imageAlt: string \| null` |
| Publicado | `product.published` | `published` | `published: boolean` |
| Número de orden | `order_header.order_number` | `orderNumber` | `orderNumber: string` |

La diferencia entre `stock_quantity` y `availableUnits` es deliberada y está documentada: el nombre de base de datos describe lo almacenado por variante y el de la API describe lo que el comprador puede pedir.
