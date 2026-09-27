# ADR-008 — Catálogo de tallas como tabla de referencia

- **Estado:** Aceptada
- **Fecha:** 2026-09-27
- **Decide:** Hedixon Cardozo (backend), con acuerdo del equipo
- **Respaldo en el PDF:** ninguno. `DECISIÓN PROPUESTA`. El PDF exige filtrar por talla (REQ-01) y mostrar la disponibilidad de cada una (CA-01-3), pero no define qué tallas existen ni cómo se validan.

## Contexto

[`../arquitectura/modelo-relacional.md`](../arquitectura/modelo-relacional.md) describe la restricción de `product_variant.size` como «valor del catálogo de tallas», pero ese catálogo no existe en ninguna parte del modelo. Hoy `size` es un `varchar(20)` sin restricción, lo que produce tres problemas concretos:

1. **El filtro no puede validarse.** [`../api/convenciones.md`](../api/convenciones.md) establece que un valor de filtro no válido produce `VALIDATION_ERROR` y «nunca se ignora en silencio». Sin catálogo, `GET /products?size=XXXL` no tiene contra qué compararse y devolvería una página vacía, que es exactamente el comportamiento prohibido.
2. **El alta de producto queda a texto libre.** RNF-05 mide que un propietario sin formación técnica complete el formulario en menos de cinco minutos; un campo libre admite `M`, `m`, `Mediana` y `Talla M` como valores distintos para la misma talla, y el filtro dejaría de funcionar sin que nadie lo note.
3. **ADR-002 ya presupone un valor convenido.** Para las artesanías de pieza única prevé `size = "ÚNICA"`, que es un valor de catálogo sin catálogo que lo respalde.

## Alternativas consideradas

1. **Tipo enumerado de PostgreSQL** (`CREATE TYPE size_code AS ENUM (...)`).
2. **`varchar` con restricción `CHECK` contra una lista literal.**
3. **`varchar` libre** (estado actual del modelo).
4. **Tabla de referencia** `size_catalog` con clave foránea desde `product_variant`.

| Criterio | A1 enumerado | A2 `CHECK` | A3 libre | A4 tabla |
| --- | --- | --- | --- | --- |
| Permite validar el filtro (convenciones) | Sí | Sí | **No** | Sí |
| Agregar una talla | Migración | Migración | Trivial | Fila nueva, sin migración |
| Permite desactivar una talla sin borrarla | No | No | — | Sí (`active`) |
| Permite ordenar las tallas para la interfaz | No (orden alfabético) | No | No | Sí (`position`) |
| Etiqueta visible distinta del código | No | No | No | Sí (`label`) |
| Coste en el modelo | Ninguno | Ninguno | Ninguno | Una tabla más |

A1 y A2 resuelven la validación pero convierten «agregar la talla XXL» en una migración de esquema, lo que contradice el ritmo de un micronegocio. A1 además no admite orden propio: `L` aparecería antes que `M` y `S`, y el desplegable del panel saldría desordenado.

## Decisión

Se crea la tabla de referencia **`size_catalog`**:

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `code` | `varchar(20)` PK | Valor que viaja por la API (`"M"`, `"ÚNICA"`) |
| `label` | `varchar(40)` | Etiqueta visible en el panel y en el filtro |
| `position` | `smallint` | Orden de presentación; evita el orden alfabético |
| `active` | `boolean` | Permite retirar una talla sin borrar el histórico |
| `created_at` | `timestamptz` | Alta |

Reglas de aplicación:

1. **`product_variant.size` referencia `size_catalog.code`** con borrado restringido. Una talla en uso no puede eliminarse.
2. **`order_item.size` NO lleva clave foránea.** Es una copia congelada del momento de la compra (RN-28): si apuntara al catálogo, retirar una talla alteraría órdenes pasadas y rompería el deber de conservación íntegra de la Ley 527 de 1999.
3. **El filtro `size` de EP-01 valida contra el catálogo.** Un valor inexistente produce `VALIDATION_ERROR` (400), conforme a las convenciones.
4. **Semilla inicial:** `XS`, `S`, `M`, `L`, `XL`, `XXL` y `ÚNICA`, esta última para los productos de pieza única previstos en ADR-002.
5. El catálogo **no se expone como endpoint propio** en este alcance: las tallas disponibles ya viajan en `ProductSummaryResponse.sizes` y en `ProductResponse.variants[]`. Añadir un endpoint sería una adición compatible si el panel lo necesitara.

## Consecuencias

**Positivas**

- El filtro por talla cumple la regla de rechazar valores no válidos sin inventar comportamiento.
- El formulario de alta muestra un desplegable ordenado en lugar de un campo libre, lo que ayuda al umbral de RNF-05.
- Agregar o retirar una talla es una fila, no una migración ni un despliegue.
- `ÚNICA` deja de ser una convención verbal y pasa a ser un valor del sistema.

**Negativas / riesgos**

- El modelo pasa de diez a **once tablas**. Es el coste de que la validación exista.
- El alta de producto depende de que el catálogo esté sembrado: si la semilla falla, no pueden crearse variantes. Se mitiga incluyendo el catálogo en la migración inicial, no en las semillas de desarrollo.
- Un valor de `size` en `order_item` puede quedar huérfano respecto del catálogo si la talla se retira. **Es el comportamiento deseado**, y por eso se documenta aquí: el histórico no sigue al catálogo.

**Sobre el contrato de API:** no cambia. `size` sigue siendo una cadena en todos los modelos. Lo que cambia es que un valor no válido en el filtro pasa a rechazarse, que es lo que [`../api/convenciones.md`](../api/convenciones.md) ya exigía. No se aplica el procedimiento de cambio incompatible.

## Verificación

| Aserción | Caso |
| --- | --- |
| El filtro por talla devuelve lo esperado | CP-02 |
| El detalle muestra disponibilidad por talla | CP-05 |
| Una talla no existente en el filtro produce 400 | Prueba de API de EP-01 (`sort`/filtros inválidos) |
| No puede repetirse una talla dentro del producto | CP-55, unicidad de `(product_id, size)` |
| Retirar una talla no altera órdenes anteriores | CP-22 |
