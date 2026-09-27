# database/

Recursos de PostgreSQL que **no** son migraciones.

Las migraciones viven en [`../backend/alembic/`](../backend/alembic/), porque
Alembic necesita importar los modelos de SQLAlchemy para poder comparar el
código con el esquema real ([ADR-009](../docs/decisiones/ADR-009-migraciones-y-motor.md)).

| Ruta | Contenido |
| --- | --- |
| `schema.sql` | Volcado del esquema vigente. **Artefacto generado.** |
| `seeds/` | Datos de siembra de desarrollo y demostración. |

## `schema.sql`

Existe para leer el esquema completo de un tirón, sin reconstruirlo mentalmente
a partir de la cadena de revisiones. **No se edita a mano:** si este archivo y
las migraciones difieren, este archivo es el que miente.

Se regenera desde una base ya migrada a `head`:

```bash
pg_dump --schema-only --no-owner --no-privileges --no-comments \
  -h 127.0.0.1 -U tiendalocal_owner -d tiendalocal \
  | grep -vE '^-- Dumped|^\\(un)?restrict '
```

Las líneas `\restrict`, `\unrestrict` y el sello de fecha se descartan porque
cambian en cada ejecución y harían que el archivo apareciera modificado en Git
sin que el esquema haya cambiado.

## `seeds/`

Datos para trabajar y para demostrar, nunca para producción.

| Archivo | Contenido |
| --- | --- |
| `catalogo_desarrollo.py` | Los datos: 4 categorías, 14 productos, sus variantes e imágenes |
| `sembrar_desarrollo.py` | El guion que los inserta |

### Uso

```powershell
# Desde la raíz del repositorio, con la base ya migrada
backend\.venv\Scripts\python.exe database\seeds\sembrar_desarrollo.py

backend\.venv\Scripts\python.exe database\seeds\sembrar_desarrollo.py --resumen
backend\.venv\Scripts\python.exe database\seeds\sembrar_desarrollo.py --reiniciar
```

### Qué siembra y por qué

**No es el punto de partida de las pruebas automatizadas.** La estrategia de
pruebas lo fija: «cada prueba de integración crea y limpia sus propios datos;
ninguna depende del orden de ejecución», y CP-90 dice que su estado inicial lo
crea la propia prueba. Estos datos sirven para desarrollar, para demostrar y
para las auditorías que necesitan una aplicación poblada:

| Uso | Qué exige |
| --- | --- |
| CP-80, rendimiento (RNF-01) | **Doce productos publicados con imagen** |
| CP-81, accesibilidad (RNF-03) | Texto alternativo real, no de relleno |
| CP-83, usabilidad (RNF-05) | Un catálogo donde dar de alta un producto más |

Estados incluidos a propósito: un producto con una talla agotada y otras
disponibles, uno publicado con **todas** sus tallas en cero, una artesanía de
pieza única agotada, uno sin publicar **con** variantes activas (CP-03) y uno sin
publicar **sin** variantes activas, que RN-21 impide publicar.

### Reglas

- **Ningún dato personal real.** Correos en `@example.com`, el dominio reservado
  para ejemplos, que no entrega correo a nadie. Ningún nombre de negocio,
  persona o dirección que exista (riesgo R-02, apartado 12.4 del PDF).
- **Las contraseñas salen del `.env`**, y lo que se almacena es su hash Argon2id,
  nunca la contraseña (RN-20).
- **Se conecta con el rol de la aplicación**, no con el propietario. Así la
  siembra comprueba de paso que ese rol tiene los privilegios que necesita.
- **Todo en una transacción**: o queda el catálogo completo, o no queda nada.
- El **catálogo de tallas no está aquí**: es parte del esquema y lo siembra la
  migración inicial ([ADR-008](../docs/decisiones/ADR-008-catalogo-tallas.md)).
- Las rutas de imagen apuntan a `/media/productos/…`, que es lo que servirán C2
  y C5. **Esos archivos todavía no existen**, así que la interfaz mostrará el
  texto alternativo — que es una forma útil de revisarlo.
