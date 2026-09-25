# ADR-004 — Versión de la API en la ruta (`/api/v1`)

- **Estado:** Aceptada
- **Fecha:** 2026-09-25
- **Decide:** Equipo completo
- **Respaldo en el PDF:** ninguno. `DECISIÓN PROPUESTA`. El PDF sí exige versionar documentos y etiquetar cada iteración (apartado 11), lo que motiva versionar también el contrato.

## Contexto

Frontend y backend avanzan en paralelo y en horarios distintos. Un cambio incompatible publicado sin aviso rompe la pantalla de otro integrante sin que quede rastro de cuándo ocurrió.

El PDF establece que cada iteración produce una etiqueta que asocia código, documentos y reportes de prueba. El contrato de API necesita el mismo tratamiento.

## Alternativas consideradas

1. **Versión en la ruta:** `/api/v1/products`.
2. **Versión en cabecera:** `Accept: application/vnd.tiendalocal.v1+json`.
3. **Sin versión:** una sola API que evoluciona.

| Criterio | A1 ruta | A2 cabecera | A3 sin versión |
| --- | --- | --- | --- |
| Visibilidad para quien depura | Alta (se ve en la URL y en los registros) | Baja | — |
| Facilidad de prueba manual | Alta | Media | Alta |
| Convivencia de dos versiones | Sí | Sí | No |
| Complejidad de implementación | Baja | Media | Ninguna |
| Riesgo de romper al otro integrante | Bajo | Bajo | Alto |

## Decisión

- Toda ruta lleva el prefijo `/api/v1`.
- El documento del contrato se versiona aparte con `MAYOR.MENOR.PARCHE` (hoy 1.0.0) y su registro de cambios vive en [`../api/README.md`](../api/README.md).
- Cambios **compatibles** (campo opcional nuevo, campo nuevo en respuesta, valor nuevo de enumeración) suben la versión menor del documento y no cambian `v1`.
- Cambios **incompatibles** (renombrar o eliminar un campo, cambiar un tipo, cambiar el significado de un código de error) exigen `v2` o un cambio coordinado y explícito entre los tres integrantes.
- El frontend debe tolerar valores desconocidos en enumeraciones y campos nuevos que no conoce.

Dado el alcance de dieciséis semanas, **no se prevé mantener dos versiones simultáneas**: `v2` solo existiría si un cambio incompatible fuera inevitable antes de la entrega.

## Consecuencias

**Positivas**

- El prefijo hace evidente qué contrato se está consumiendo en cualquier registro o captura.
- El registro de cambios documenta cuándo cambió el contrato, lo que alimenta la trazabilidad exigida por OE-2.
- El procedimiento de cambio evita correcciones silenciosas en un solo lado (regla de la fuente única de verdad).

**Negativas / riesgos**

- El prefijo aparece en todas las rutas, incluso mientras exista una sola versión. Es un costo mínimo frente al beneficio.
- Versionar disciplina, no protege: un cambio incompatible aplicado sin subir versión sigue rompiendo. Se controla en la revisión cruzada.

## Verificación

- Todas las rutas de `../api/endpoints.md` llevan el prefijo.
- Las pruebas de API apuntan a rutas versionadas.
- La revisión de Pull Request comprueba que un cambio de contrato traiga su entrada en el registro de cambios.
