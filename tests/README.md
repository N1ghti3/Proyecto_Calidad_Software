# Pruebas automatizadas

Estado: **capa de datos** (iteración I-3). Todavía no hay API ni frontend, de
modo que las campañas de API, E2E, rendimiento y accesibilidad empiezan cuando
exista ese código. Estrategia completa en
[`docs/pruebas/estrategia-pruebas.md`](../docs/pruebas/estrategia-pruebas.md).

## Ejecutar

### Opción A — solo con Docker (no requiere Python)

Desde la raíz del repositorio:

```bash
docker compose -f docker-compose.test.yml run --rm pruebas
```

Al terminar, apagar la base de pruebas:

```bash
docker compose -f docker-compose.test.yml down
```

Usa un PostgreSQL propio, en memoria y en el puerto 55432: **no toca la base de
desarrollo** ni sus datos.

### Opción B — con el Python de tu equipo

```bash
docker compose -f docker-compose.test.yml up -d postgres-pruebas
pip install -r backend/requirements-dev.txt
```

```powershell
# PowerShell
$env:TEST_DATABASE_ADMIN_URL = "postgresql+psycopg://tiendalocal_owner:pruebas_owner@127.0.0.1:55432/postgres"
pytest
```

```bash
# bash
export TEST_DATABASE_ADMIN_URL=postgresql+psycopg://tiendalocal_owner:pruebas_owner@127.0.0.1:55432/postgres
pytest
```

Sin `TEST_DATABASE_ADMIN_URL`, las pruebas de base de datos **se omiten** y solo
corren las unitarias.

### En GitHub

[`.github/workflows/pruebas.yml`](../.github/workflows/pruebas.yml) ejecuta todo
en cada push y en cada Pull Request hacia `main`, y publica el reporte como
artefacto.

## Qué hay

| Carpeta | Pruebas | Qué verifica |
| --- | --- | --- |
| `unit/` | 27 | Derivación de contraseñas (RN-20), configuración (ADR-010) y coherencia del catálogo de siembra con el esquema |
| `integration/` | 46 | Migraciones (ADR-009), restricciones del esquema, privilegios de roles (RN-25, CP-82), búsqueda y colación (ADR-011), siembra |
| `concurrency/` | 6 | CP-90 y variantes (RNF-02), más un control negativo |

### Cómo están escritas

- **Contra PostgreSQL real**, nunca contra una base simulada: lo que se verifica
  es lo que el motor garantiza.
- **Cada sesión crea su propia base**, la migra desde cero con Alembic y la
  borra al terminar. Ninguna prueba depende de otra ni del orden de ejecución.
- **Con el rol de la aplicación** (`tiendalocal_app`), no con el propietario:
  una restricción que solo se cumple para el propietario no protege nada.
- **Las restricciones se verifican por nombre.** Un rechazo por otra causa no
  hace pasar la prueba.

### Concurrencia (CP-90)

`POST /api/v1/orders` aún no existe. Las pruebas ejecutan **en la base** la
transacción de [ADR-005](../docs/decisiones/ADR-005-concurrencia.md) desde 50
conexiones simultáneas. Cuando exista el servicio, la función `comprar()` se
sustituye por la llamada a la API y las aserciones se mantienen.

| Caso | Escenario | Esperado |
| --- | --- | --- |
| CP-90 | 50 solicitudes de 1 unidad, stock 10 | 10 confirmadas, 40 rechazadas, stock 0, aserciones A1–A9 |
| CP-90.2 | 20 solicitudes de 3 unidades, stock 10 | 3 confirmadas, stock 1 |
| CP-90.3 | 30 solicitudes, stock 0 | 0 confirmadas |
| CP-90.4 | Órdenes de dos líneas, una escasa | Todo o nada: la línea abundante no se descuenta en las rechazadas |
| CP-90.5 | Órdenes cruzadas [A, B] y [B, A] | Sin interbloqueos |
| Control negativo | La misma compra **sin** `FOR UPDATE` | **Debe haber sobreventa** |

El control negativo pasa cuando el defecto se produce. Es la evidencia de que la
prueba genera concurrencia real y de que el bloqueo es lo que la controla.

## Verificación de las propias pruebas

Una suite que nunca falla no demuestra nada. El 15/10/2026 se introdujeron
defectos a propósito para comprobar que se detectan:

| Defecto introducido | Detectado por |
| --- | --- |
| Quitar el `REVOKE` de la auditoría en la migración | 2 pruebas de privilegios (RN-25) |
| Quitar `ck_inventory_stock_no_negativo` | La prueba de RN-09 y el conteo de restricciones |
| Quitar `FOR UPDATE` de la compra | 4 de los 5 casos de CP-90 |

Lección del segundo caso: `alembic check` **no** detecta una restricción
`CHECK` ausente. Por eso `test_migraciones.py` cuenta las restricciones además
de ejecutar la comparación.

## Hallazgo para la API

`test_el_telefono_se_almacena_solo_con_digitos`: el esquema exige 7–15 dígitos
sin `+`, pero el contrato aceptaba `+573001234567` en `CustomerRequest.phone`,
de modo que la base habría rechazado pedidos válidos. Quedó resuelto en el
[contrato 1.1.0](../docs/api/README.md#registro-de-cambios): el backend quita el
`+` antes de guardar. Cuando exista `POST /api/v1/orders`, hace falta una prueba
de API que envíe el teléfono con `+` y verifique que la orden se crea.
