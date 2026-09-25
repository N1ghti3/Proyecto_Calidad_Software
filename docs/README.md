# Documentación de TiendaLocal

Especificación técnica derivada de `ProyectoTiendaLocalCUN.pdf` (v1.0), que es la **fuente principal de verdad** del alcance, los objetivos, los requisitos y los criterios de aceptación.

Toda propuesta del equipo que el PDF no respalde explícitamente está marcada `DECISIÓN PROPUESTA` en el punto donde se aplica y, si es estructural, registrada como ADR.

> **Estado:** fase de ingeniería y contrato. **No hay código de aplicación**: ni frontend, ni API, ni migraciones, ni pipelines.

## Mapa de documentos

### Requisitos — [`requisitos/`](requisitos/)

| Documento | Contenido |
| --- | --- |
| [requisitos-funcionales.md](requisitos/requisitos-funcionales.md) | REQ-01 … REQ-08 con origen, prioridad, criterio y desglose |
| [requisitos-no-funcionales.md](requisitos/requisitos-no-funcionales.md) | RNF-01 … RNF-06 clasificados por ISO/IEC 25010:2023 |
| [criterios-aceptacion.md](requisitos/criterios-aceptacion.md) | Criterios Dado/Cuando/Entonces con su prueba |
| [historias-usuario.md](requisitos/historias-usuario.md) | HU-01 … HU-20 por actor |
| [trazabilidad.md](requisitos/trazabilidad.md) | Objetivo → historia → requisito → regla → entidad → endpoint → pantalla → prueba |

### Arquitectura y dominio — [`arquitectura/`](arquitectura/)

| Documento | Contenido |
| --- | --- |
| [arquitectura.md](arquitectura/arquitectura.md) | Vista de contexto, capas, flujo crítico, dónde vive cada regla |
| [componentes.md](arquitectura/componentes.md) | Fichas de C1–C6 y sistemas externos |
| [reglas-negocio.md](arquitectura/reglas-negocio.md) | RN-01 … RN-29 con condición, comportamiento y trazabilidad |
| [modelo-dominio.md](arquitectura/modelo-dominio.md) | Conceptos, actores y los cuatro planos de nombres |
| [modelo-er.md](arquitectura/modelo-er.md) | Diagrama entidad-relación y entidades descartadas |
| [modelo-relacional.md](arquitectura/modelo-relacional.md) | Tablas, campos, tipos, restricciones e índices |

### Contrato de integración — [`api/`](api/README.md) — **fuente oficial**

| Documento | Contenido |
| --- | --- |
| [README.md](api/README.md) | Cómo usar el contrato y control de cambios |
| [contrato-api.md](api/contrato-api.md) | Reglas generales y flujo completo de compra |
| [endpoints.md](api/endpoints.md) | EP-01 … EP-24 |
| [modelos.md](api/modelos.md) | DTO con tipos y ejemplos |
| [errores.md](api/errores.md) | Estructura y catálogo de códigos |
| [convenciones.md](api/convenciones.md) | Nombres, fechas, dinero, enumeraciones, paginación |
| [frontend-backend-contract.md](api/frontend-backend-contract.md) | Pantalla por pantalla: envío, recepción, errores y estados |

### Pruebas — [`pruebas/`](pruebas/)

| Documento | Contenido |
| --- | --- |
| [estrategia-pruebas.md](pruebas/estrategia-pruebas.md) | Niveles, campañas, criterios de salida, defectos |
| [casos-prueba.md](pruebas/casos-prueba.md) | CP-01 … CP-90 |
| [pruebas-api.md](pruebas/pruebas-api.md) | Verificación del contrato endpoint por endpoint |
| [pruebas-concurrencia.md](pruebas/pruebas-concurrencia.md) | CP-90: 50 solicitudes sobre 10 unidades |

### Decisiones — [`decisiones/`](decisiones/README.md)

ADR-001 arquitectura · ADR-002 inventario por variante · ADR-003 convenciones · ADR-004 versionamiento · ADR-005 concurrencia · ADR-006 autenticación (pendiente) · ADR-007 notificaciones (pendiente).

### Despliegue — [`despliegue/`](despliegue/)

Pendiente: Docker, AWS, entornos y CI/CD (responsable: Jhon Ortiz).

### Informe de auditoría

[VALIDATION-REPORT.md](VALIDATION-REPORT.md) — inventario de artefactos, inconsistencias detectadas y pendientes.

---

## Responsabilidades por integrante

La asignación nominal de roles que el PDF deja pendiente (apartado 11) queda registrada aquí. Cada integrante tiene una **responsabilidad principal** y una **secundaria**, para evitar puntos únicos de conocimiento (riesgo R-05).

### Brandon Soto — Frontend

Documentos de trabajo principales:

- [`api/frontend-backend-contract.md`](api/frontend-backend-contract.md) — su documento de cabecera: qué envía, qué recibe, qué errores y qué estados por pantalla
- [`api/modelos.md`](api/modelos.md) y [`api/errores.md`](api/errores.md)
- [`requisitos/historias-usuario.md`](requisitos/historias-usuario.md)
- `frontend/` (cuando comience la implementación)

Responsable de: aplicación frontend, catálogo, búsqueda, filtros, detalle, carrito, checkout, confirmación, panel administrativo, diseño responsive, accesibilidad (RNF-03), rendimiento del cliente (RNF-01) y operabilidad (RNF-05).
Secundario en: definición de criterios de aceptación de interfaz.

### Hedixon Cardozo — Backend y base de datos

Documentos de trabajo principales:

- [`api/endpoints.md`](api/endpoints.md) y [`api/modelos.md`](api/modelos.md)
- [`arquitectura/`](arquitectura/) completo, en especial [reglas-negocio.md](arquitectura/reglas-negocio.md) y [modelo-relacional.md](arquitectura/modelo-relacional.md)
- [`requisitos/`](requisitos/)
- `backend/` y `database/` (cuando comience la implementación)

Responsable de: API REST, lógica de negocio, autenticación, productos, inventario, órdenes, checkout, auditoría, PostgreSQL, control transaccional y concurrencia (RNF-02, ADR-005).
Secundario en: pruebas de integración.

### Jhon Ortiz — DevOps, calidad y pruebas

Documentos de trabajo principales:

- [`pruebas/`](pruebas/) completo
- [`requisitos/`](requisitos/) y [`requisitos/trazabilidad.md`](requisitos/trazabilidad.md)
- [`api/`](api/README.md) (como base de las pruebas de contrato)
- [`arquitectura/`](arquitectura/) y [`decisiones/`](decisiones/README.md)
- `tests/`, `nginx/`, `.github/`, `docs/despliegue/`

Responsable de: Docker, Docker Compose, Nginx, GitHub Actions, CI/CD, AWS, despliegue, automatización, testing, pruebas de integración, pruebas de concurrencia (CP-90), rendimiento, seguridad, evidencias técnicas y documentación de despliegue.
Secundario en: revisión de requisitos y criterios de aceptación.

> El proyecto es **colaborativo**: estas áreas indican responsabilidad, no propiedad exclusiva. Cualquier integrante puede modificar otras áreas cuando sea necesario, respetando la revisión cruzada y el control de cambios del contrato.

## Reglas de trabajo derivadas del PDF

1. **`docs/api/` es la fuente única de verdad** del contrato. Las discrepancias entre código y contrato se resuelven con el procedimiento de [api/README.md](api/README.md#control-de-cambios), nunca en silencio.
2. **La prueba de concurrencia se escribe antes** de implementar la funcionalidad (riesgo R-03).
3. **Rama principal protegida**, ramas por funcionalidad y revisión cruzada antes de integrar (PDF, apartado 11).
4. **Alcance congelado al cierre de I-2** (riesgo R-04): toda solicitud nueva requiere aprobación explícita del equipo completo.
5. **Sin datos personales reales** en documentos, capturas ni repositorios (compromiso ético del PDF, apartado 12.4).
6. **Sin secretos en el repositorio** (riesgo R-07).

## Orden de lectura sugerido

1. `README.md` del repositorio — contexto general.
2. [requisitos/requisitos-funcionales.md](requisitos/requisitos-funcionales.md) y [requisitos-no-funcionales.md](requisitos/requisitos-no-funcionales.md).
3. [arquitectura/reglas-negocio.md](arquitectura/reglas-negocio.md).
4. [arquitectura/modelo-er.md](arquitectura/modelo-er.md).
5. [api/README.md](api/README.md) y el documento propio de tu rol.
6. [pruebas/estrategia-pruebas.md](pruebas/estrategia-pruebas.md).
