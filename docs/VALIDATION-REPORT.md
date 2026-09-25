# Informe de validación de la fase de ingeniería

- **Fecha:** 2026-09-25
- **Alcance auditado:** toda la carpeta `docs/` de la rama `docs/requirements-and-api-contract`
- **Fuente contrastada:** `ProyectoTiendaLocalCUN.pdf` v1.0 (texto completo)
- **Criterio aplicado:** criterio de aceptación de **OE-2** — «todo requisito tiene identificador, origen, prioridad y criterio de aceptación verificable; el modelo soporta los casos de uso del alcance»

---

## 1. Inventario de artefactos

| Artefacto | Cantidad | Documento |
| --- | --- | --- |
| Requisitos funcionales | 8 (REQ-01 … REQ-08) + 36 sub-requisitos | `requisitos/requisitos-funcionales.md` |
| Requisitos no funcionales | 6 (RNF-01 … RNF-06) | `requisitos/requisitos-no-funcionales.md` |
| Criterios de aceptación | 36 (22 funcionales del PDF y derivados, 6 no funcionales, 4 de objetivos, 4 de historias) | `requisitos/criterios-aceptacion.md` |
| Historias de usuario | 20 (HU-01 … HU-20) | `requisitos/historias-usuario.md` |
| Reglas de negocio | 29 (RN-01 … RN-29) | `arquitectura/reglas-negocio.md` |
| Entidades de datos | 10 tablas + 7 entidades descartadas con justificación | `arquitectura/modelo-er.md`, `modelo-relacional.md` |
| Componentes | 6 internos (C1–C6) + 3 sistemas externos | `arquitectura/componentes.md` |
| Endpoints | 21 (numerados EP-01 … EP-24) | `api/endpoints.md` |
| DTO | 27, en 25 secciones | `api/modelos.md` |
| Códigos de error | 14 | `api/errores.md` |
| Pantallas con contrato de estados | 13 (P-01 … P-16) | `api/frontend-backend-contract.md` |
| Casos de prueba | 48 (CP-01 … CP-90, con 6 variantes de concurrencia) | `pruebas/casos-prueba.md` |
| Decisiones (ADR) | 7 (5 aceptadas, 2 pendientes) | `decisiones/` |
| Marcas `DECISIÓN PROPUESTA` | 62 | Toda la documentación |

## 2. Verificación de consistencia

### 2.1 Comprobaciones automáticas ejecutadas

| Comprobación | Resultado |
| --- | --- |
| Todo `CP-xx` referenciado existe en `casos-prueba.md` | ✅ Sin huérfanos |
| Todo `EP-xx` referenciado existe en `endpoints.md` | ✅ Sin huérfanos |
| Todo `RN-xx` referenciado existe en `reglas-negocio.md` | ✅ Sin huérfanos |
| Todo `HU-xx` referenciado existe en `historias-usuario.md` | ✅ Sin huérfanos |
| Todo `CA-xx` referenciado existe en `criterios-aceptacion.md` | ✅ Sin huérfanos |
| Todos los enlaces relativos `.md` apuntan a archivos existentes | ✅ Sin enlaces rotos |

### 2.2 Revisión por dimensión (checklist del encargo)

| Dimensión | Exigencia | Resultado |
| --- | --- | --- |
| **Requisitos** | Cada uno con historia o justificación, criterio de aceptación y trazabilidad | ✅ 8/8 funcionales y 6/6 no funcionales |
| **Historias** | Cada una con requisito y criterio | ✅ 20/20 |
| **Reglas** | Cada una con requisito y entidad o proceso | ✅ 29/29 |
| **Modelo** | Cada entidad con propósito, relaciones y restricciones | ✅ 10/10 |
| **API** | Cada endpoint con request, response, errores y requisitos | ✅ 21/21 |
| **DTO** | Cada uno con campos, tipos, obligatoriedad y ejemplos | ✅ 27/27 |
| **Frontend** | Cada pantalla con endpoint, request, response, estados y errores | ✅ 13/13 |
| **Backend** | Cada endpoint con validación, regla, entidades, respuesta, errores y pruebas | ✅ 21/21 |
| **Testing** | Cada requisito crítico con al menos una prueba | ✅ 14/14 (REQ-01…08, RNF-01…06) |

### 2.3 Cobertura cruzada

| Relación | Cobertura |
| --- | --- |
| Requisitos con al menos una historia | 8/8 (RNF-04 y RNF-05 cubiertos por HU-12 y HU-13) |
| Requisitos con al menos un caso de prueba | 14/14 |
| Reglas con al menos un caso de prueba | 29/29 |
| Endpoints con al menos un caso de prueba | 21/21 |
| Causas del problema (C-01 … C-05) con componente y requisito | 5/5 |
| Indicadores del PDF (I-01 … I-08) con fuente de verificación | 8/8 |

## 3. Hallazgos

Clasificación: **CRITICAL** (impide avanzar) · **HIGH** (debe resolverse antes de construir) · **MEDIUM** (resolver durante la construcción) · **LOW** (mejora).

| ID | Severidad | Hallazgo | Estado |
| --- | --- | --- | --- |
| H-01 | **HIGH** | ADR-006 (autenticación) tiene dos puntos abiertos: función de derivación de clave concreta y comportamiento de sesión al recargar el panel | **Abierto** — fecha límite: antes de I-3 |
| H-02 | **HIGH** | ADR-007 (notificaciones) depende de confirmar proveedor de correo gratuito, remitente verificado y qué ocurre si la cuota resulta insuficiente para REQ-05 | **Abierto** — fecha límite: antes de I-5 |
| H-03 | **MEDIUM** | La Tabla 10 del PDF se extrae con las filas de RNF desalineadas respecto de sus identificadores. La asignación usada aquí (RNF-01 desempeño, RNF-02 fiabilidad, RNF-03 accesibilidad, RNF-04 seguridad, RNF-05 operabilidad, RNF-06 instalación) se dedujo del contenido y concuerda con las menciones cruzadas del propio documento (apartados 3.3, 12.1 y 14) | **Abierto** — confirmar con el docente en la primera retroalimentación |
| H-04 | **MEDIUM** | El `README.md` del repositorio describe «Fase 0 — Inicialización» y su árbol no incluye `docs/api/`, `docs/arquitectura/*` ni los nuevos documentos | **Abierto** — actualizar al integrar esta rama |
| H-05 | **MEDIUM** | El PDF no indica si el precio puede variar por talla. El modelo lo fija en el producto | **Abierto** — validar con el propietario en la sesión de I-1; cambiarlo después sería un cambio incompatible de contrato |
| H-06 | **MEDIUM** | El PDF identifica al «personal de apoyo» como actor, pero el sistema no define un rol propio con permisos diferenciados | **Aceptado conscientemente** — registrado como candidato a trabajo futuro (nota 2 de `historias-usuario.md`) |
| H-07 | **LOW** | El límite de frecuencia de creación de órdenes (10/min por IP) debe ampliarse en el ambiente de pruebas para no enmascarar CP-90 | **Documentado** en `pruebas-concurrencia.md` |
| H-08 | **LOW** | Las líneas base de los indicadores I-01, I-02 e I-03 están «por establecer» | **Esperado** — el propio PDF lo declara; se levantan en I-1 |
| H-09 | **LOW** | `docs/despliegue/` sigue siendo un marcador de posición | **Abierto** — corresponde a la fase de construcción (Jhon Ortiz) |

No se detectó ningún hallazgo **CRITICAL**.

## 4. Correcciones realizadas durante la auditoría

| # | Problema detectado | Corrección |
| --- | --- | --- |
| C-01 | `api/README.md` declaraba «24 endpoints» y «25 DTO»; el conteo real es 21 y 27 | Corregidos el estado del contrato y el registro de cambios |
| C-02 | `requisitos/README.md`, `arquitectura/README.md` y `pruebas/README.md` seguían diciendo «pendiente, aún no hay contenido» | Reescritos como índices de sus carpetas |
| C-03 | `decisiones/README.md` era un marcador de posición sin índice ni plantilla | Reescrito con índice de ADR, estados, convenciones y plantilla |
| C-04 | El escenario de RNF-02 aparecía descrito con distinto nivel de detalle en varios documentos | Unificado: la fuente es `pruebas-concurrencia.md`; los demás enlazan a ella |

## 5. Vacíos del PDF resueltos como `DECISIÓN PROPUESTA`

Los más relevantes; el resto está marcado en cada documento.

| Vacío del PDF | Decisión | Dónde |
| --- | --- | --- |
| No dice dónde residen las existencias | Inventario por variante (SKU) | ADR-002 |
| No define convenciones de nombres | `snake_case` en base de datos, `camelCase` en API y TypeScript | ADR-003 |
| No define versionado de API | Versión en la ruta `/api/v1` | ADR-004 |
| Nombra el bloqueo de fila pero no el detalle | Bloqueo pesimista ordenado por `variant_id` + `CHECK (stock_quantity >= 0)` | ADR-005 |
| No define mecanismo de sesión | Token de portador, 8 h, sin refresco | ADR-006 (pendiente) |
| No modela la notificación como entidad | Entidad `notification` con estado y reintentos | ADR-007 (pendiente) |
| No define ciclo de estados completo de la orden | `CONFIRMADA → PREPARADA → ENTREGADA`, más `CANCELADA` con devolución de unidades | RN-13, REQ-07.4 |
| No define cómo consulta el comprador su orden | Número de orden + correo, con respuesta 404 si no coinciden | RN-18 |
| No reparte el presupuesto de 1,5 MB | Reparto por tipo de recurso | RNF-01 |
| No fija límites de la API | Paginación, líneas, unidades, tamaño de imagen, frecuencia | `contrato-api.md` |

Ninguna de estas decisiones contradice el PDF: todas cubren un silencio del documento. No se modificó ningún objetivo, alcance, identificador, requisito, criterio, restricción, actor ni término del original.

## 6. Verificación del criterio final del encargo

| Condición | Evidencia |
| --- | --- |
| «Un desarrollador frontend que no conoce el backend debe poder leer `docs/api/` y saber exactamente cómo consumir la API» | `frontend-backend-contract.md` define, por pantalla, campos enviados con tipo y restricción, campos recibidos, tabla de errores con comportamiento esperado y los ocho estados obligatorios; `modelos.md` da tipos convertibles a TypeScript sin interpretación |
| «Un desarrollador backend que no conoce el frontend debe poder leer `docs/api/` y saber exactamente qué implementar» | `endpoints.md` define, por endpoint, parámetros, cuerpo, respuesta, orden de validación, estados HTTP, errores, reglas y pruebas; `reglas-negocio.md` fija el comportamiento y `modelo-relacional.md` la transacción |
| «Un responsable de calidad debe poder saber cómo verificar el comportamiento» | `estrategia-pruebas.md` (niveles y criterios de salida), `casos-prueba.md` (48 casos), `pruebas-api.md` (matriz por endpoint), `pruebas-concurrencia.md` (10 aserciones de CP-90) y `trazabilidad.md` |

## 7. Pendientes antes de iniciar la construcción

| # | Pendiente | Responsable | Fecha límite |
| --- | --- | --- | --- |
| 1 | Cerrar ADR-006 (autenticación) | Hedixon, Brandon | Antes de I-3 |
| 2 | Cerrar ADR-007 (notificaciones) | Jhon, Hedixon | Antes de I-5 |
| 3 | Confirmar la lectura de los RNF de la Tabla 10 con el docente (H-03) | Equipo | Primera retroalimentación |
| 4 | Validar con el propietario que el precio no varía por talla (H-05) | Brandon | I-1 |
| 5 | Actualizar el `README.md` del repositorio al integrar esta rama (H-04) | Equipo | Al abrir el Pull Request |
| 6 | Verificar supuestos S-01, S-02 y S-03 del PDF | Jhon (S-02), equipo (S-01, S-03) | S-02 semana 2; S-01 semana 4 |
| 7 | Levantar la línea base de I-01, I-02 e I-03 | Jhon | I-1 |

## 8. Conclusión

La documentación cumple el criterio de aceptación de OE-2: **los 14 requisitos tienen identificador, origen, prioridad, criterio de aceptación verificable y trazabilidad completa hasta una prueba**, y el modelo de datos soporta todos los casos de uso del alcance, incluido el crítico de consistencia bajo concurrencia.

Los dos hallazgos **HIGH** son decisiones pendientes con fecha límite y responsable asignado, no vacíos de especificación: ninguno bloquea el trabajo de las iteraciones I-1 e I-2.

No existe código de aplicación, y esta fase no lo requiere.
