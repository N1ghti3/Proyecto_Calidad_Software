# Matriz de trazabilidad

Relaciona objetivo → historia → requisito → regla de negocio → entidad → endpoint → pantalla → prueba → release.

Solo se registran relaciones justificables con el PDF o con un documento de este repositorio. Responde al criterio de aceptación de **OE-2**: «todo requisito tiene identificador, origen, prioridad y criterio de aceptación verificable».

## 1. Objetivo específico → requisitos

| Objetivo (PDF, apartado 7.2) | Requisitos | Iteración (PDF, Tabla 11) |
| --- | --- | --- |
| OE-1 Caracterizar el proceso actual y línea base | — (trabajo de campo, no software) | I-0, I-1 |
| OE-2 Diseñar modelo de datos, arquitectura y especificación | Todos (esta fase) | I-1, I-2 |
| OE-3 Construir y desplegar la plataforma | REQ-01 … REQ-08, RNF-06 | I-3 … I-5 |
| OE-4 Verificar criterios de aceptación | RNF-01 … RNF-05 | I-6, I-7 |

## 2. Requisito → historia → regla → entidad → endpoint → pantalla → prueba

| REQ | Historias | Reglas | Entidades | Endpoints | Pantallas | Pruebas | Release |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REQ-01 | HU-01, HU-02, HU-03, HU-04 | RN-01, RN-02, RN-03, RN-04 | PRODUCT, PRODUCT_VARIANT, CATEGORY, INVENTORY, PRODUCT_IMAGE | EP-01, EP-02, EP-03 | P-01, P-02 | CP-01 … CP-06 | I-3 |
| REQ-02 | HU-05, HU-06 | RN-05, RN-06, RN-07 | PRODUCT_VARIANT, INVENTORY | EP-04 | P-03 | CP-10 … CP-13 | I-4 |
| REQ-03 | HU-07, HU-11 | RN-08, RN-09, RN-10, RN-11, RN-28, RN-29 | ORDER_HEADER, ORDER_ITEM, INVENTORY, AUDIT_LOG | EP-05, EP-06 | P-04, P-05, P-06 | CP-20 … CP-25, CP-90 | I-4 |
| REQ-04 | HU-08 | RN-12 | ORDER_HEADER | EP-05, EP-06 | P-04, P-05 | CP-30, CP-31 | I-5 |
| REQ-05 | HU-10, HU-20 | RN-14, RN-15 | NOTIFICATION, ORDER_HEADER | EP-05, EP-20 | P-05, P-16 | CP-40, CP-41 | I-5 |
| REQ-06 | HU-13, HU-14, HU-15, HU-19 | RN-19, RN-21, RN-22, RN-23, RN-24, RN-25 | PRODUCT, PRODUCT_VARIANT, INVENTORY, PRODUCT_IMAGE, AUDIT_LOG | EP-12 … EP-16, EP-21, EP-22, EP-24, EP-19 | P-11, P-12, P-13, P-15 | CP-50 … CP-55, CP-24 | I-3 |
| REQ-07 | HU-16, HU-17, HU-18, HU-19 | RN-13, RN-26, RN-27 | ORDER_HEADER, AUDIT_LOG, INVENTORY | EP-17, EP-18, EP-23, EP-19 | P-14, P-15 | CP-60 … CP-62 | I-5 |
| REQ-08 | HU-09 | RN-16, RN-17 | ORDER_HEADER | EP-05 | P-04 | CP-70 … CP-73 | I-5 |

## 3. Requisito no funcional → trazabilidad

| RNF | Origen (PDF) | Reglas | Componentes | Endpoints / pantallas | Prueba | Indicador | Release |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RNF-01 | O-03 / Green IT | RN-22 | C1, C2, C5 | P-01, P-02, EP-16 | CP-80 | I-04 | I-5, I-6 |
| RNF-02 | C-01 / SP-1 | RN-08 … RN-11 | C3, C4, C6 | EP-05 | **CP-90** | I-02 | I-4 |
| RNF-03 | W3C 2023 / R-04 | RN-22 (texto alternativo) | C1 | P-01 … P-05 | CP-81 | I-08 | I-6 |
| RNF-04 | Ley 1581 de 2012 | RN-17, RN-18, RN-19, RN-20 | C2, C3, C4 | EP-10, EP-11, todos `/admin` | CP-82, CP-51 | — | I-3 … I-6 |
| RNF-05 | C-04 / OE-4 | RN-21 | C1 | P-12 | CP-83 | I-05 | I-6 |
| RNF-06 | Green IT / DevOps | — | Infraestructura | — | CP-84 | I-06, I-07 | I-1, I-3 |

## 4. Causa del problema → componente → requisito → evidencia

Recupera la Tabla 5 del PDF (causas) y la Tabla 8 (cadena problema–necesidad–capacidad–resultado).

| Causa (PDF 5.2) | Componente que la atiende | Requisito | Prueba / indicador |
| --- | --- | --- | --- |
| C-01 Ausencia de fuente única de verdad del inventario | C4 + C3 (validación transaccional) | REQ-03, RNF-02 | CP-90, I-02 |
| C-02 Catálogo disperso sin estructura ni vigencia | C1 (catálogo estructurado con estado de publicación) | REQ-01 | CP-01 … CP-06, I-01 |
| C-03 Costo y complejidad de plataformas comerciales | Arquitectura de bajo costo operativo | RNF-06 | CP-84, I-07 |
| C-04 Baja madurez digital del propietario | Interfaz de administración simplificada | RNF-05 | CP-83, I-05 |
| C-05 Sin proceso de actualización de existencias | Descuento automático al confirmar + auditoría | REQ-06, REQ-03 | CP-24, CP-50, I-03 |

## 5. Regla de negocio → requisito → prueba

Resumen; el detalle está en [`../arquitectura/reglas-negocio.md`](../arquitectura/reglas-negocio.md).

| Reglas | Requisitos | Pruebas |
| --- | --- | --- |
| RN-01 … RN-04 | REQ-01 | CP-01 … CP-06 |
| RN-05 … RN-07 | REQ-02 | CP-10 … CP-13 |
| RN-08 … RN-11, RN-28, RN-29 | REQ-03, RNF-02 | CP-20 … CP-25, CP-90 |
| RN-12 | REQ-04 | CP-30, CP-31 |
| RN-13, RN-26, RN-27 | REQ-07 | CP-60 … CP-62 |
| RN-14, RN-15 | REQ-05 | CP-40, CP-41 |
| RN-16, RN-17, RN-18 | REQ-08, RNF-04 | CP-70 … CP-73, CP-82 |
| RN-19 … RN-25 | REQ-06, RNF-04 | CP-50 … CP-55, CP-51, CP-82 |

## 6. Endpoint → requisito → prueba

| Endpoint | Requisito | Reglas | Pruebas |
| --- | --- | --- | --- |
| EP-01 | REQ-01 | RN-01 … RN-04 | CP-01, CP-02, CP-03, CP-04, CP-06 |
| EP-02 | REQ-01 | RN-04 | CP-02 |
| EP-03 | REQ-01 | RN-01, RN-02, RN-03 | CP-03, CP-05 |
| EP-04 | REQ-02 | RN-05, RN-06, RN-07 | CP-10, CP-11, CP-13 |
| EP-05 | REQ-03, REQ-04, REQ-05, REQ-08, RNF-02 | RN-08 … RN-12, RN-14, RN-16, RN-28, RN-29 | CP-20 … CP-25, CP-30, CP-70, CP-73, CP-90 |
| EP-06 | REQ-03, REQ-04 | RN-12, RN-18 | CP-22 |
| EP-10, EP-11 | RNF-04 | RN-19, RN-20 | CP-51, CP-82 |
| EP-12, EP-14, EP-21, EP-22 | REQ-06 | RN-05, RN-19, RN-21, RN-24 | CP-50, CP-51, CP-55 |
| EP-13 | REQ-06 | RN-01, RN-21, RN-23 | CP-52, CP-55 |
| EP-15, EP-24 | REQ-06 | RN-09, RN-24, RN-25 | CP-50, CP-53 |
| EP-16 | REQ-06, RNF-01, RNF-03 | RN-22 | CP-54, CP-80 |
| EP-17, EP-18, EP-23 | REQ-07 | RN-13, RN-26, RN-27 | CP-60, CP-61, CP-62 |
| EP-19 | REQ-06, REQ-07 | RN-24, RN-25, RN-27 | CP-24, CP-50, CP-60 |
| EP-20 | REQ-05 | RN-15 | CP-41 |

## 7. Decisiones técnicas → qué afectan

| ADR | Requisito afectado | Documentos | Verificación |
| --- | --- | --- | --- |
| ADR-001 Arquitectura | Todos | arquitectura.md, componentes.md | Revisión cruzada, CP-84 |
| ADR-002 Inventario por variante | REQ-01, REQ-03, REQ-06, RNF-02 | modelo-er.md, modelo-relacional.md | CP-02, CP-05, CP-90 |
| ADR-003 Convenciones | Todos | api/convenciones.md | API-T1 … API-T5 |
| ADR-004 Versionamiento | Todos | api/README.md | Revisión de Pull Request |
| ADR-005 Concurrencia | RNF-02, REQ-03 | modelo-relacional.md, pruebas-concurrencia.md | CP-90 y variantes |
| ADR-006 Autenticación (pendiente) | REQ-06, RNF-04 | api/contrato-api.md | CP-51, CP-82, CP-83 |
| ADR-007 Notificaciones (pendiente) | REQ-05 | reglas-negocio.md | CP-40, CP-41 |

## 8. Indicadores del PDF (apartado 14) → evidencia

| Indicador | Mide | Fuente de verificación | Requisito |
| --- | --- | --- | --- |
| I-01 | Consultas resueltas sin escribir al vendedor | Registro de eventos (C6) + prueba con usuarios | REQ-01 |
| I-02 | Órdenes confirmadas que exceden existencias (meta 0) | Reporte de CP-90 | RNF-02 |
| I-03 | Pedidos con registro estructurado completo | Consulta a la base y auditoría | REQ-03, REQ-06 |
| I-04 | Peso transferido y tiempo de render | Reporte de CP-80 | RNF-01 |
| I-05 | Tasa de éxito y tiempo del alta de producto | Registro de CP-83 | RNF-05 |
| I-06 | Despliegues sin intervención manual | Registro del canal automatizado | RNF-06 |
| I-07 | Tamaño de la imagen de contenedor | Salida de la construcción | RNF-06 |
| I-08 | Incumplimientos de accesibilidad | Reporte de CP-81 | RNF-03 |

## 9. Huecos declarados

| Hueco | Estado | Responsable |
| --- | --- | --- |
| Línea base de I-01, I-02 e I-03 | «Por establecer» en I-1 (declarado por el PDF) | Jhon / equipo |
| ADR-006 y ADR-007 | Pendientes con fecha límite | Hedixon / Jhon |
| Asignación nominal de roles del PDF (apartado 11) | Resuelta en este repositorio: ver [`../README.md`](../README.md) | Equipo |
| Rol diferenciado para el personal de apoyo | No se implementa; registrado como candidato a trabajo futuro | Equipo |
