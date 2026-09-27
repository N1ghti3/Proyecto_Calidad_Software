# Backend — capa de datos

Estado: **iteración I-3**. Solo existe la capa de datos: los modelos de
SQLAlchemy y las migraciones de Alembic. No hay API todavía.

| Ruta | Contenido |
| --- | --- |
| `app/models/` | Las once tablas del [modelo relacional](../docs/arquitectura/modelo-relacional.md), agrupadas por dominio |
| `app/db/base.py` | Base declarativa y convención de nombres de restricciones |
| `app/core/config.py` | Variables de entorno, leídas del `.env` de la raíz |
| `alembic/` | Configuración y revisiones de migración |
| `alembic/versions/` | Una revisión por cambio de esquema |

## Requisitos previos

1. **PostgreSQL 16 en marcha.** Desde la raíz del repositorio:

   ```bash
   cp .env.example .env     # y rellenar las contraseñas
   docker compose up -d
   docker compose ps        # debe decir: running (healthy)
   ```

2. **Entorno de Python.** Desde esta carpeta:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Migraciones

```bash
alembic upgrade head        # aplica todo lo pendiente
alembic current             # en qué versión está la base
alembic history             # cadena de revisiones
alembic downgrade -1        # deshace la última
alembic check               # ¿los modelos coinciden con el esquema real?
```

Alembic lee la conexión de `DATABASE_MIGRATION_URL`, que apunta al rol
propietario. La aplicación usará `DATABASE_URL`, que apunta a un rol sin
privilegio de modificar la auditoría. Son dos roles distintos a propósito
([ADR-010](../docs/decisiones/ADR-010-numero-orden-y-roles.md)).

Para apuntar a otra base sin tocar el `.env` —lo que hace el canal de
integración continua con su base efímera:

```bash
alembic -x url=postgresql+psycopg://usuario:clave@host:5432/base upgrade head
```

## Reglas de trabajo con migraciones

Vienen de [ADR-009](../docs/decisiones/ADR-009-migraciones-y-motor.md) y no son
recomendaciones:

1. **Nunca `create_all()`**, en ningún ambiente, incluido el local. Crea las
   tablas que faltan y calla sobre las que cambiaron, de modo que el esquema
   real y los modelos pueden divergir sin que nada lo indique.
2. **Toda revisión lleva su `downgrade`** y se prueba en ambos sentidos antes de
   integrarse.
3. **La autogeneración se revisa a mano.** Alembic detecta bien las adiciones y
   mal los renombrados: un renombrado lo interpreta como borrar y crear, y eso
   destruiría datos.
4. **Los índices por expresión no se comparan solos.** Los de `lower(...)`,
   `DESC` y el GIN de trigramas se escriben en la revisión; la clase de operador
   va en `postgresql_ops` y no dentro de la expresión, porque escrita dentro
   `alembic check` da el índice por igual sin comprobarlo.

Ciclo para un cambio de esquema:

```bash
# 1. cambiar el modelo en app/models/
# 2. generar la revisión
alembic revision --autogenerate -m "descripción del cambio"
# 3. LEER la revisión generada y corregirla
# 4. probarla en ambos sentidos
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
# 5. confirmar que no queda divergencia
alembic check
```

## Cómo se llaman las restricciones

`app/db/base.py` fija una convención de nombres. No es cosmética: sin ella
PostgreSQL inventa los nombres, Alembic no puede referirse a ellos al revertir
una migración, y el error de una restricción violada no dice qué regla se violó.

Con ella, un intento de dejar el inventario en negativo responde:

```
ERROR:  new row for relation "inventory" violates check constraint
        "ck_inventory_stock_no_negativo"
```

que es una afirmación que una prueba puede verificar por nombre.

## Verificación hecha sobre esta migración

La revisión inicial se aplicó contra un PostgreSQL 16 real y se comprobó:

| Aserción | Resultado |
| --- | --- |
| Las once tablas se crean desde una base vacía | 11 tablas, 40 restricciones `CHECK`, 9 claves foráneas |
| Las claves foráneas restringen el borrado, salvo `product_image` que va en cascada | Confirmado |
| El catálogo de tallas queda sembrado | 7 filas |
| `f_unaccent()` es `IMMUTABLE` y la búsqueda ignora tildes y mayúsculas | «CAMISETA nandu» encuentra «Camiseta Ñandú Oversize» |
| El índice GIN de trigramas existe sobre `lower(f_unaccent(name))` | Confirmado |
| `UPDATE` y `DELETE` sobre `audit_log` con el rol de la aplicación | Rechazados; `SELECT` e `INSERT` permitidos (RN-25, CP-82) |
| Inventario negativo | Rechazado por `ck_inventory_stock_no_negativo` (RN-09) |
| Orden sin consentimiento | Rechazada por `ck_order_header_consentimiento_obligatorio` (RN-16) |
| Número de orden secuencial o con caracteres ambiguos | Rechazado por `ck_order_header_numero_formato` (ADR-010) |
| Ajuste manual de inventario sin motivo | Rechazado por `ck_audit_log_motivo_obligatorio` (CP-50) |
| Talla fuera del catálogo, o repetida en el mismo producto | Rechazadas (ADR-008, CP-55) |
| `downgrade base` y volver a subir | Deja solo `alembic_version`; el segundo `upgrade` funciona |
| `alembic check` tras migrar | Sin divergencias entre modelos y esquema |
