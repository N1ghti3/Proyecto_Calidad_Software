# ADR-011 — Colación del clúster y orden alfabético del catálogo

- **Estado:** Aceptada
- **Fecha:** 2026-09-27
- **Decide:** Jhon Ortiz (DevOps y calidad), con acuerdo del equipo
- **Respaldo en el PDF:** ninguno. `DECISIÓN PROPUESTA`. El PDF exige listar el catálogo (REQ-01) pero no dice en qué orden, y no menciona colaciones.

## Contexto

ADR-009 fija la imagen `postgres:16-alpine`. Alpine usa **musl** como biblioteca de C, y musl no implementa las colaciones de `libc`: declara el locale que se le pida y ordena por bytes de todas formas. El clúster resultante lo declara sin ambigüedad y lo cumple a medias:

```
datcollate  | datlocprovider
------------+----------------
en_US.utf8  | c
```

Medido sobre el contenedor del proyecto, con seis nombres de producto verosímiles:

| Orden | `ORDER BY name` (estado actual) | `ORDER BY name COLLATE "es-CO-x-icu"` |
| --- | --- | --- |
| 1 | Camiseta Ñandú | Ábaco decorativo |
| 2 | Chaqueta | camiseta basica |
| 3 | Cinturón | Camiseta Ñandú |
| 4 | Zapato artesanal | Chaqueta |
| 5 | camiseta basica | Cinturón |
| 6 | **Ábaco decorativo** | Zapato artesanal |

Dos defectos visibles para el comprador: los nombres con tilde inicial caen al final de la lista, y los que empiezan en minúscula se ordenan después de todos los que empiezan en mayúscula. Para un catálogo en español, con productos llamados «Ábaco», «Ñandú» o «Órbita», eso no es un detalle tipográfico: es una lista que parece rota.

No es un error de programación. Es el motor haciendo exactamente lo que se le pidió, porque nadie le pidió otra cosa.

**Por qué se decide ahora:** el proveedor de colación de un clúster se fija en su inicialización y no puede cambiarse después sin recrearlo. Hoy el volumen está vacío; mañana recrearlo cuesta borrar datos.

## Alternativas consideradas

1. **No hacer nada.** Ordenar por `created_at` y no ofrecer orden alfabético.
2. **Anotar cada consulta:** `ORDER BY name COLLATE "es-CO-x-icu"` donde haga falta.
3. **Anotar las columnas:** `COLLATE "es-CO-x-icu"` en `product.name` y `category.name`.
4. **Fijar el proveedor ICU en el clúster**, con `POSTGRES_INITDB_ARGS`.

| Criterio | A1 nada | A2 por consulta | A3 por columna | A4 clúster |
| --- | --- | --- | --- | --- |
| El catálogo ordena bien en español | **No** | Sí, donde se recuerde | Sí | Sí |
| Alguien tiene que acordarse | — | **En cada consulta** | Al crear una columna de texto | Nadie |
| Un olvido produce un fallo visible en pruebas | — | **No: produce una lista mal ordenada** | No | — |
| Cubre columnas futuras | — | No | No | Sí |
| Exige recrear el volumen | No | No | No | **Sí** |
| Queda declarado donde se lee | — | En el código | En el esquema | En `docker-compose.yml` |

A2 es la peor de las que funcionan, y por la misma razón que ADR-010 rechazó proteger la auditoría solo desde la aplicación: una garantía que depende de que alguien se acuerde no es una garantía. Un `ORDER BY name` sin anotar no falla, no avisa y no rompe ninguna prueba: simplemente entrega una lista mal ordenada, que es el modo de fallo más difícil de detectar.

A3 es correcta y acotada, pero traslada el mismo olvido un nivel más arriba: la próxima columna de texto que alguien ordene alfabéticamente nace con el problema otra vez.

A4 tiene el único coste real —recrear el volumen— y es el que hoy vale cero.

## Decisión

El clúster se inicializa con **proveedor de colación ICU y locale `es-CO`**:

```yaml
POSTGRES_INITDB_ARGS: "--locale-provider=icu --icu-locale=es-CO --locale=C --encoding=UTF8"
```

Consecuencias de cada parte:

- `--locale-provider=icu --icu-locale=es-CO`: la colación por omisión de toda la base pasa a ser la de español de Colombia. Ninguna consulta ni ninguna columna necesita anotarse.
- `--locale=C`: el locale de `libc` que queda debajo, para lo que ICU no cubre. Se declara explícitamente en lugar de heredar el `LANG` de la imagen, que en musl no significa nada. **Verificado:** con proveedor ICU, PostgreSQL 16 usa ICU también para `upper()` y `lower()`, de modo que `upper('única')` devuelve `ÚNICA` y no `úNICA`. Eso importa porque `ck_size_catalog_codigo_mayusculas` y `ck_admin_user_correo_minusculas` dependen de esas funciones.
- `--encoding=UTF8`: explícito, para no depender del entorno de la imagen.

El orden alfabético del catálogo queda, por tanto, **como propiedad del motor y no como responsabilidad de quien escribe la consulta**. Es la misma línea que ADR-010: lo que puede declararse en la base no se confía a la costumbre del código.

### Lo que esta decisión no hace

- **No reemplaza a `f_unaccent`.** La búsqueda de CA-01-2 seguirá usando `lower(f_unaccent(name))` y su índice GIN de trigramas. Una colación que ignora tildes al *ordenar* no sirve para *buscar* con `LIKE`, y el índice necesita una expresión inmutable. Son dos problemas distintos con dos soluciones distintas.
- **No cambia el contrato de API.** El orden de la respuesta ya estaba definido por el parámetro `sort` de EP-01; lo que cambia es que ahora `name` ordena como esperaría una persona que lee español.

## Consecuencias

**Positivas**

- El catálogo ordena bien en español sin que nadie anote nada, hoy y en las columnas que se agreguen después.
- La colación queda declarada en `docker-compose.yml`, que es donde alguien que levanta el proyecto va a mirar, y se aplica igual en cada máquina y en el servidor.
- `upper()` y `lower()` pasan a manejar correctamente los acentos, lo que hace ciertas dos restricciones que hasta ahora lo eran solo para texto ASCII.
- La colación ICU resultante es **determinista**, de modo que `LIKE`, las expresiones regulares de las restricciones y los índices de patrón siguen funcionando. Verificado.

**Negativas / riesgos**

- **Recrear el volumen es destructivo.** `docker compose down -v` borra los datos. Se hace ahora justamente porque no hay ninguno; quien clone el repositorio más adelante recibe la configuración correcta desde su primera inicialización.
- **`POSTGRES_INITDB_ARGS` solo actúa en la primera inicialización.** Un volumen ya existente ignora el cambio sin avisar. Un clúster que no cumpla lo aquí decidido no se distingue a simple vista: hay que consultarlo. Por eso la verificación de abajo es una consulta y no una inspección del archivo.
- **`LC_CTYPE=C`** implica que las clases de caracteres POSIX (`[[:alpha:]]`, `\w`) no reconocen letras acentuadas. Ninguna restricción del esquema depende de ellas: las de formato usan rangos explícitos (`[a-z0-9-]`, `[A-Z0-9-]`, `[0-9]`). Una restricción futura que use clases POSIX sobre texto en español debe tenerlo en cuenta.
- **Dependencia de ICU en la imagen.** `postgres:16-alpine` viene compilada con ICU y expone `es-CO-x-icu`; se verificó en el contenedor del proyecto antes de decidir. Si alguna vez se cambiara a una imagen sin ICU, la inicialización fallaría de entrada —fallo ruidoso, no silencioso— y la alternativa registrada es A3.

## Verificación

| Aserción | Cómo se comprueba |
| --- | --- |
| El clúster usa proveedor ICU con locale `es-CO` | `select datlocprovider, daticulocale from pg_database where datname = current_database();` debe dar `i` y `es-CO` |
| El catálogo ordena bien sin anotar la consulta | `ORDER BY name` sobre nombres con tilde inicial y minúscula inicial |
| `upper()` y `lower()` manejan acentos | `select upper('única');` debe dar `ÚNICA` |
| La colación es determinista y `LIKE` sigue operando | `select collisdeterministic from pg_collation where collname = 'default';` debe dar `true` |
| La migración inicial aplica sin cambios sobre un clúster ICU | `alembic upgrade head` y luego `alembic check` |
| La búsqueda sin tildes sigue usando su propio camino | CP-04 |
