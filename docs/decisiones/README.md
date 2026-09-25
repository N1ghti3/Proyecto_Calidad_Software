# Decisiones técnicas (ADR)

Registro de decisiones de arquitectura. Cada decisión relevante se documenta con su contexto, las alternativas evaluadas, la decisión y sus consecuencias.

## Índice

| ID | Decisión | Estado | Afecta a |
| --- | --- | --- | --- |
| [ADR-001](ADR-001-arquitectura.md) | Arquitectura en capas sobre los componentes C1–C6 del PDF | Aceptada | Todo el equipo |
| [ADR-002](ADR-002-modelo-inventario.md) | El inventario pertenece a la variante (SKU), no al producto | Aceptada | Backend, frontend, pruebas |
| [ADR-003](ADR-003-convenciones-api.md) | `snake_case` en base de datos, `camelCase` en API y TypeScript | Aceptada | Backend, frontend |
| [ADR-004](ADR-004-versionamiento-api.md) | Versión en la ruta (`/api/v1`) | Aceptada | Backend, frontend |
| [ADR-005](ADR-005-concurrencia.md) | Bloqueo pesimista de fila más restricción `CHECK` | Aceptada | Backend, pruebas |
| [ADR-006](ADR-006-autenticacion.md) | Token de portador para el administrador, sin cuentas de comprador | **Pendiente** de validar en I-3 | Backend, frontend |
| [ADR-007](ADR-007-notificaciones.md) | Notificación asíncrona con registro persistente | **Pendiente** de confirmar proveedor | Backend, DevOps |

## Estados

| Estado | Significado |
| --- | --- |
| **Aceptada** | Decisión vigente; el código debe cumplirla |
| **Pendiente** | Falta información o validación; no se implementa hasta resolverla |
| **Reemplazada** | Sustituida por otro ADR, que se indica |

## Convenciones

- Archivo: `ADR-NNN-titulo-en-kebab-case.md`.
- Un ADR aceptado **no se edita**: si la decisión cambia, se crea uno nuevo que lo reemplaza.
- Toda decisión que el PDF no respalde explícitamente se marca `DECISIÓN PROPUESTA` también en los documentos donde se aplica.
- Un cambio de contrato derivado de un ADR sigue el procedimiento de [`../api/README.md`](../api/README.md#control-de-cambios).

## Plantilla

```markdown
# ADR-NNN — Título

- **Estado:** Propuesta | Aceptada | Pendiente | Reemplazada por ADR-NNN
- **Fecha:** AAAA-MM-DD
- **Decide:** rol o integrante
- **Respaldo en el PDF:** apartado o tabla, o «no respaldado — DECISIÓN PROPUESTA»

## Contexto
## Alternativas consideradas
## Decisión
## Consecuencias
## Verificación
```
