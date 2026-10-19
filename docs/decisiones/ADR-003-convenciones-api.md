# ADR-003 — `snake_case` en base de datos, `camelCase` en API y TypeScript

- **Estado:** Aceptada
- **Fecha:** 2026-09-25
- **Decide:** Equipo completo
- **Respaldo en el PDF:** ninguno. `DECISIÓN PROPUESTA`. El PDF exige trabajo desacoplado y trazabilidad, pero no fija convenciones de nombres.

## Contexto

Tres personas trabajando en horarios distintos, con dos lenguajes cuyas convenciones nativas difieren: Python usa `snake_case`, TypeScript usa `camelCase`, y PostgreSQL se comporta mejor con identificadores en minúsculas y guion bajo.

Sin una regla oficial, el mismo dato aparecería como `stock_quantity`, `stockQuantity` y `availableUnits` según quién lo escriba, y cada desalineación se descubriría en integración, no al escribir el código.

## Alternativas consideradas

1. **`snake_case` en todo** (base de datos, API y frontend).
2. **`camelCase` en todo**, incluida la base de datos.
3. **Mixto por plano:** `snake_case` en base de datos, `camelCase` en API y frontend, con traducción en una única capa.

| Criterio | A1 todo snake | A2 todo camel | A3 mixto |
| --- | --- | --- | --- |
| Naturalidad en PostgreSQL | Alta | Baja (exige comillas dobles) | Alta |
| Naturalidad en TypeScript | Baja | Alta | Alta |
| Naturalidad en Python | Alta | Baja | Alta (traducción en esquemas) |
| Puntos donde puede fallar la traducción | 0 | 0 | 1 (controlado) |
| Riesgo de errores por comillas en SQL | Bajo | Alto | Bajo |

## Decisión

Convención mixta con **traducción en un único lugar**: los esquemas de la capa de interfaz de C3.

| Plano | Estilo |
| --- | --- |
| PostgreSQL | `snake_case`, tablas en singular |
| API (JSON) | `camelCase` |
| TypeScript | `camelCase` (tipos en `PascalCase`) |
| Python interno | `snake_case`, traducido al serializar |
| Rutas HTTP | `kebab-case`, sustantivos en plural |

Reglas complementarias, detalladas en [`../api/convenciones.md`](../api/convenciones.md): identificadores UUID, fechas ISO 8601 en UTC con sufijo `At`, dinero entero en COP con sufijo `Cop`, enumeraciones en `SCREAMING_SNAKE_CASE`, paginación `page`/`pageSize` con `meta`, filtros repetibles y orden `campo:direccion`.

Se admite que el nombre de base de datos y el de la API difieran cuando describen cosas distintas, **siempre que la equivalencia esté documentada**: `inventory.stock_quantity` (lo almacenado por variante) ↔ `availableUnits` (lo que el comprador puede pedir).

## Consecuencias

**Positivas**

- Cada lenguaje se escribe en su estilo natural; nadie pelea con el suyo.
- Una sola capa traduce: si algo no coincide, se sabe dónde mirar.
- El rechazo de campos desconocidos (`VALIDATION_ERROR`) convierte un error de nombre en un fallo inmediato y explícito, no en un dato silenciosamente ignorado.

**Negativas / riesgos**

- Existe un punto de traducción que puede equivocarse. Se mitiga con la prueba transversal API-T3 y con la tabla de equivalencias de `convenciones.md`.
- Los desarrolladores deben consultar la tabla cuando el nombre no es evidente; es el costo de no imponer un estilo ajeno a dos de los tres planos.

## Verificación

- API-T1 … API-T5: forma de respuestas, fechas, dinero y colecciones.
- API-T3: un campo desconocido produce `VALIDATION_ERROR`.
- Revisión cruzada de Pull Request contra `convenciones.md`.
