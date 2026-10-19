# ADR-010 — Generación del número de orden y roles de base de datos

- **Estado:** Aceptada
- **Fecha:** 2026-09-27
- **Decide:** Hedixon Cardozo (backend) y Jhon Ortiz (calidad y DevOps), con acuerdo del equipo
- **Respaldo en el PDF:** parcial. REQ-03.3 exige que la orden reciba un identificador único y el apartado 3.3 exige que la orden se conserve íntegra y recuperable (Ley 527 de 1999). El **mecanismo de generación** y la **protección de la auditoría en el motor** son `DECISIÓN PROPUESTA`.

## Contexto

Dos vacíos distintos, agrupados en un mismo registro porque comparten la misma pregunta de fondo: **qué garantiza la base de datos por sí sola y qué queda confiado a que el código se comporte.**

1. [`../api/convenciones.md`](../api/convenciones.md) fija el formato `TL-AAAAMMDD-XXXXX` del número de orden, pero no cómo se produce la parte variable. Y el mismo documento prohíbe «exponer identificadores secuenciales que permitan enumerar órdenes o clientes».
2. RN-25 declara la auditoría de solo anexado y el modelo relacional lo repite, pero la única garantía real es que la aplicación no expone la operación de actualización. Eso no es una garantía: es una costumbre que el próximo cambio de código puede romper sin que nada lo impida.

## Alternativas consideradas

### Número de orden

1. **Secuencia diaria**, reiniciada cada día mediante una fila de contador.
2. **Secuencia global** de PostgreSQL, rellenada a cinco dígitos.
3. **Cinco caracteres aleatorios** de un alfabeto acotado.

| Criterio | A1 contador diario | A2 secuencia global | A3 aleatorio |
| --- | --- | --- | --- |
| Cumple la prohibición de identificadores enumerables | **No** | **No** | Sí |
| Contención dentro de la transacción crítica | **Alta**: la fila del contador se bloquea | Ninguna: `nextval` no bloquea | Ninguna |
| Riesgo de colisión | Ninguno | Ninguno | Despreciable, y lo atrapa `UNIQUE` |
| Legible para el comprador | Sí | Sí | Sí |
| Revela el volumen de ventas del negocio | Sí | Sí | No |

A1 es la peor opción posible aquí: introduciría una fila bloqueada **dentro de la transacción que RNF-02 pone a prueba con cincuenta solicitudes simultáneas**, justo el lugar donde no debe añadirse contención. A2 no bloquea, pero un comprador que recibe `TL-20260415-00042` sabe que el negocio lleva 42 órdenes, y además contradice la convención propia del proyecto.

### Protección de la auditoría

1. **Solo a nivel de aplicación** (estado actual).
2. **Privilegios de base de datos**: el rol de la aplicación no tiene permiso de actualizar ni borrar.
3. **Disparador** que rechaza toda actualización o borrado.

| Criterio | A1 aplicación | A2 privilegios | A3 disparador |
| --- | --- | --- | --- |
| Resiste un error de programación futuro | **No** | Sí | Sí |
| Coste en ejecución | Ninguno | Ninguno | Uno por operación |
| Compatible con la prohibición de lógica en la base (ADR-001) | Sí | Sí | Discutible |
| Verificable desde una prueba | No | Sí | Sí |

## Decisión

### Número de orden: aleatorio, generado en la aplicación

- Formato `TL-` + fecha UTC en `AAAAMMDD` + `-` + **cinco caracteres aleatorios**.
- Alfabeto de 32 símbolos: `23456789ABCDEFGHJKLMNPQRSTUVWXYZ`. Se excluyen `0`, `1`, `I` y `O` porque el número se dicta por teléfono y se transcribe a mano.
- Generación con el módulo `secrets` de Python, **en la capa de servicio**, nunca en el motor: ADR-001 prohíbe lógica de negocio en la base.
- La restricción `UNIQUE(order_number)` es la garantía final. Ante colisión se reintenta hasta tres veces y, agotadas, la transacción falla con `INTERNAL_ERROR`.
- Espacio: 32⁵ ≈ 33,5 millones de combinaciones por día. Para el volumen de un micronegocio la probabilidad de colisión es despreciable.

El número **no es un secreto**: RN-18 ya exige número más correo para consultar una orden. Lo aleatorio no sustituye ese control, evita que el identificador filtre el volumen del negocio y cumple la convención propia del proyecto.

### Roles de base de datos: dos, con privilegios distintos

| Rol | Uso | Privilegios |
| --- | --- | --- |
| `tiendalocal_owner` | Migraciones y creación de extensiones | Propietario del esquema |
| `tiendalocal_app` | Conexión de la aplicación en ejecución | `SELECT`, `INSERT`, `UPDATE`, `DELETE` sobre las tablas operativas; **solo `SELECT` e `INSERT` sobre `audit_log`** |

```sql
REVOKE UPDATE, DELETE ON audit_log FROM tiendalocal_app;
```

Se elige privilegios sobre disparador porque es declarativo, no cuesta nada en ejecución y no abre la puerta a poner comportamiento en el motor. Un disparador habría obligado a discutir dónde termina «proteger» y empieza «decidir».

Consecuencia operativa: `.env.example` necesita **dos cadenas de conexión**, `DATABASE_URL` para la aplicación y `DATABASE_MIGRATION_URL` para Alembic. Hoy declara una sola.

## Consecuencias

**Positivas**

- La transacción crítica no gana ni un bloqueo más: el número se genera antes de abrirla.
- El identificador público deja de revelar cuántas órdenes lleva el negocio.
- La inmutabilidad de la auditoría pasa de ser una promesa del código a una restricción del motor, y CP-82 puede comprobarla intentando una actualización y esperando el rechazo.
- Si un cambio futuro introdujera por error un borrado de auditoría, fallaría en pruebas en lugar de destruir evidencia.

**Negativas / riesgos**

- Un número aleatorio no permite ordenar órdenes por su identificador. No hace falta: el listado administrativo ordena por `created_at` y la fecha ya viaja dentro del propio número.
- Dos roles significan dos credenciales que gestionar y un modo de fallo nuevo: si la aplicación arranca con las credenciales del propietario, la protección desaparece sin aviso. CP-82 debe verificar **con qué rol se conecta la aplicación**, no solo que la tabla esté protegida.
- La generación en la aplicación implica que una inserción manual en la base puede saltarse el formato. Se acota con la restricción de formato ya declarada sobre `order_number`.

## Verificación

| Aserción | Caso |
| --- | --- |
| El número de orden es único y recupera la orden íntegra | CP-22 |
| El formato coincide con `TL-AAAAMMDD-XXXXX` | Pruebas de API de EP-05 y EP-06 |
| Un `UPDATE` sobre `audit_log` con el rol de la aplicación es rechazado | CP-82 |
| La aplicación se conecta con `tiendalocal_app`, no con el propietario | CP-82 |
| Los registros de auditoría de una orden existen y no se alteran | CP-24, CP-50 |
