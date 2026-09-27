# ADR-009 — Estrategia de migraciones, versión del motor y extensiones

- **Estado:** Aceptada
- **Fecha:** 2026-09-27
- **Decide:** Jhon Ortiz (DevOps y calidad) y Hedixon Cardozo (backend), con acuerdo del equipo
- **Respaldo en el PDF:** parcial. El PDF exige despliegue reproducible en contenedores (RNF-06), que el canal automatizado detenga el despliegue si una prueba falla (OE-3) y que cada iteración produzca una etiqueta que asocie código, documentos y reportes (apartado 11). **No nombra herramienta de migraciones, versión del motor ni extensiones:** `DECISIÓN PROPUESTA`.

## Contexto

El modelo relacional está especificado hasta el nivel de campo, pero nada dice cómo se lleva ese modelo a una base real ni sobre qué versión de PostgreSQL. Tres vacíos concretos bloquean la primera migración:

1. **Sin herramienta de migraciones** no hay forma de saber en qué versión de esquema está una base, ni de deshacer un cambio.
2. **Sin versión fijada del motor**, `gen_random_uuid()` puede existir o no: es nativo desde PostgreSQL 13 y antes exige la extensión `pgcrypto`. El `docker-compose.yml` actual no declara ningún servicio.
3. **Sin extensiones declaradas**, el criterio CA-01-2 no puede cumplirse: exige que la búsqueda por nombre encuentre coincidencias **parciales** «sin distinción de mayúsculas ni tildes», y eso no se resuelve comparando en minúsculas.

## Alternativas consideradas

### Migraciones

1. **`SQLAlchemy.create_all()`** al arrancar la aplicación.
2. **Archivos SQL numerados** con un ejecutor propio.
3. **Alembic.**

| Criterio | A1 `create_all` | A2 SQL numerado | A3 Alembic |
| --- | --- | --- | --- |
| Versión de esquema registrada en la base | **No** | Manual | Sí (`alembic_version`) |
| Reversible | **No** | Manual | Sí (`downgrade`) |
| Detecta divergencia entre modelos y esquema | No | No | Sí (autogeneración con revisión) |
| Dependencia nueva | Ninguna | Ninguna | Ninguna: viene con SQLAlchemy |
| Esfuerzo (R-05) | Nulo | Medio | Bajo |

A1 queda descartada de raíz: crea tablas que existan y calla sobre las que cambiaron, de modo que una base desplegada y el modelo pueden divergir sin que nada lo indique.

### Búsqueda sin tildes ni mayúsculas (CA-01-2)

1. **`lower(name) LIKE`** sin tratamiento de tildes.
2. **`unaccent` con índice funcional** y comparación por prefijo.
3. **`unaccent` + `pg_trgm`** con índice GIN, que admite coincidencia en cualquier posición.
4. **Columna `name_normalized`** mantenida por la aplicación.

| Criterio | A1 `lower` | A2 funcional | A3 GIN trigramas | A4 columna |
| --- | --- | --- | --- | --- |
| Encuentra «camiséta» al buscar «camiseta» | **No** | Sí | Sí | Sí |
| Coincidencia parcial en el medio del nombre | Con `%…%` sin índice | Solo por prefijo | Sí | Con `%…%` sin índice |
| Usa índice | Solo por prefijo | Sí | Sí | Solo por prefijo |
| Requiere extensiones | No | Sí | Sí | No |
| Riesgo de desincronización | Ninguno | Ninguno | Ninguno | El de toda columna derivada |

A1 incumple el criterio. A4 lo cumple pero traslada a la aplicación una normalización que el motor ya sabe hacer, y añade una columna que puede quedar desactualizada. Como el equipo autoaloja PostgreSQL en un contenedor, instalar extensiones no tiene coste ni depende de un proveedor.

## Decisión

### Migraciones: Alembic

- La **primera migración crea el esquema completo**, incluida la semilla de `size_catalog` (ADR-008), que es parte del esquema y no de los datos de prueba.
- **Prohibido `create_all()`** en cualquier ambiente, incluido el local.
- Toda migración lleva su `downgrade` y se prueba en ambos sentidos antes de integrarse.
- El canal de integración continua levanta una base vacía y **aplica todas las migraciones desde cero en cada cambio**; si falla, no despliega (criterio de OE-3).

### Ubicación de los artefactos

Alembic necesita importar los modelos de SQLAlchemy, de modo que vive junto al backend:

| Ruta | Contenido |
| --- | --- |
| `backend/alembic/` | Configuración y revisiones de migración |
| `database/seeds/` | Datos de siembra de desarrollo y demostración |
| `database/schema.sql` | Volcado del esquema vigente, **generado**, como referencia de lectura |

Esto corrige la descripción de `database/` del `README.md` del repositorio, que hoy dice que contiene las migraciones.

### Motor: PostgreSQL 16, fijado

- Imagen `postgres:16-alpine`, con la versión declarada explícitamente en `docker-compose.yml` y en el canal automatizado.
- `gen_random_uuid()` es nativo: **no se instala `pgcrypto`**.
- Nivel de aislamiento por omisión (`READ COMMITTED`), conforme a ADR-005.

### Extensiones e índice de búsqueda

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent() no es IMMUTABLE y por eso no puede usarse directamente en un índice.
-- La envoltura fija el diccionario y declara la inmutabilidad.
CREATE FUNCTION f_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
  AS $$ SELECT public.unaccent('public.unaccent', $1) $$;

CREATE INDEX idx_product_name_search
  ON product USING gin (lower(f_unaccent(name)) gin_trgm_ops);
```

La consulta de búsqueda compara `lower(f_unaccent(name))` contra `lower(f_unaccent(:q))`. La función envoltorio no es lógica de negocio: normaliza texto, y ADR-001 prohíbe reglas de negocio en la base, no funciones de utilidad.

### Aclaración sobre RNF-06

El umbral de **250 MB corresponde a la imagen de la aplicación**, no a la de PostgreSQL ni a la suma de las imágenes del despliegue. Queda escrito aquí porque el requisito no lo precisa y su lectura literal haría fallar CP-84 sin motivo.

## Consecuencias

**Positivas**

- Una base desplegada declara en qué versión de esquema está, y esa versión es reversible.
- Aplicar las migraciones desde cero en cada cambio convierte un error de migración en un fallo de integración, no en una sorpresa durante el despliegue.
- CA-01-2 queda cubierto con un índice real: la búsqueda no degrada el catálogo.
- La versión fijada elimina la clase de fallo «funciona en mi máquina».

**Negativas / riesgos**

- Alembic autogenera revisiones que **deben revisarse a mano**: detecta bien las adiciones y mal los renombrados, que interpreta como borrar y crear. Un renombrado sin revisar destruiría datos. Se controla en la revisión cruzada obligatoria.
- Las extensiones exigen privilegios de superusuario en la creación. Con el motor autoalojado no es problema; si el proyecto migrara a una instancia gestionada que las bloquee, la alternativa registrada es A4 (columna normalizada).
- `database/schema.sql` es un artefacto generado: si alguien lo edita a mano, miente. Se regenera desde las migraciones y nunca al revés.

## Verificación

| Aserción | Caso |
| --- | --- |
| Búsqueda insensible a mayúsculas y tildes | CP-04 |
| Imagen de aplicación inferior a 250 MB y despliegue sin pasos manuales | CP-84 |
| Las migraciones aplican desde cero en una base vacía | Canal de integración continua, en cada cambio |
| El esquema resultante coincide con `modelo-relacional.md` | Revisión cruzada de Pull Request |
