# `docs/api/` — Fuente oficial del contrato de integración

Esta carpeta es la **única fuente de verdad** del contrato entre frontend y backend. Si el código y esta documentación difieren, no se corrige en silencio ninguna de las dos partes: se aplica el [control de cambios](#control-de-cambios).

## Documentos

| Documento | Contenido | Léelo si… |
| --- | --- | --- |
| [contrato-api.md](contrato-api.md) | Reglas generales: transporte, autenticación, límites, compatibilidad y flujo completo de compra | Necesitas el panorama antes de implementar |
| [endpoints.md](endpoints.md) | EP-01 … EP-24 con parámetros, respuestas, errores y trazabilidad | Vas a implementar o consumir un endpoint |
| [modelos.md](modelos.md) | DTO con tipos, obligatoriedad, nulabilidad y ejemplos | Necesitas los campos exactos |
| [errores.md](errores.md) | Estructura de error y catálogo de códigos estables | Vas a manejar o devolver un error |
| [convenciones.md](convenciones.md) | Nombres, fechas, dinero, enumeraciones, paginación, filtros y orden | Dudas sobre cómo se llama o se formatea algo |
| [frontend-backend-contract.md](frontend-backend-contract.md) | Pantalla por pantalla: qué se envía, qué se recibe, qué errores y qué estados | Implementas una pantalla o pruebas la integración |

## Cómo usarlo cada rol

**Brandon (frontend)**
1. `frontend-backend-contract.md` — la pantalla que vas a construir.
2. `modelos.md` — los tipos que convertirás en interfaces TypeScript.
3. `errores.md` — qué hacer ante cada código.
No necesitas conocer la implementación del backend ni el esquema de la base de datos.

**Hedixon (backend)**
1. `endpoints.md` — rutas, validaciones y códigos que debes devolver.
2. `modelos.md` — esquemas de petición y respuesta (Pydantic).
3. `../arquitectura/reglas-negocio.md` — las reglas que debes hacer cumplir.
No necesitas saber cómo se pinta la pantalla, pero sí qué estados espera (`frontend-backend-contract.md`).

**Jhon (calidad y DevOps)**
1. `endpoints.md` + `errores.md` — base de las pruebas de API.
2. `frontend-backend-contract.md` — estados a verificar en E2E.
3. `../pruebas/` — estrategia y casos.

## Estado del contrato

| Aspecto | Valor |
| --- | --- |
| Versión del contrato | **1.0.0** (propuesta, sin implementación) |
| Versión de la API | `v1` |
| Fecha | 2026-09-25 |
| Base | `ProyectoTiendaLocalCUN.pdf` v1.0 |
| Endpoints definidos | 21 (numerados EP-01 … EP-24, con huecos reservados entre EP-06 y EP-10) |
| DTO definidos | 27, en 25 secciones |
| Códigos de error | 14 |

Versionado del documento: `MAYOR.MENOR.PARCHE`. Mayor = cambio incompatible; menor = adición compatible; parche = corrección de redacción.

## Control de cambios

Cuando el código y el contrato no coincidan, o cuando haga falta modificar el contrato:

1. **Identificar el cambio.** Qué campo, endpoint o código cambia y por qué.
2. **Determinar si es incompatible.** Ver la tabla de compatibilidad en [contrato-api.md](contrato-api.md#compatibilidad-y-versiones). Renombrar o eliminar un campo, cambiar un tipo o el significado de un código **es incompatible**.
3. **Actualizar el contrato** en esta carpeta, subiendo la versión.
4. **Actualizar el frontend.**
5. **Actualizar el backend.**
6. **Actualizar las pruebas** (`../pruebas/`).
7. **Registrar un ADR** en `../decisiones/` si el cambio afecta una decisión estructural.

Reglas del procedimiento:

- Ningún cambio incompatible entra sin acuerdo de los tres integrantes (revisión cruzada, PDF apartado 11).
- El alcance está congelado al cierre de I-2 (riesgo R-04): toda solicitud nueva se registra como candidata a trabajo futuro y requiere aprobación explícita del equipo completo.
- Un cambio aplicado solo en el código sin pasar por aquí es un defecto de proceso, aunque funcione.

## Registro de cambios

| Versión | Fecha | Cambio | Autor |
| --- | --- | --- | --- |
| 1.0.0 | 2026-09-25 | Contrato inicial derivado del PDF: 21 endpoints, 27 DTO, 14 códigos de error | Equipo TiendaLocal |

## Qué no está en esta carpeta

- Código de implementación (no existe en esta fase).
- Requisitos y criterios de aceptación → `../requisitos/`.
- Reglas de negocio, modelo de datos y arquitectura → `../arquitectura/`.
- Estrategia y casos de prueba → `../pruebas/`.
- Decisiones técnicas → `../decisiones/`.
