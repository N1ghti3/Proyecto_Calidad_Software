# Estrategia de pruebas

Base: PDF, apartado 11 — «la verificación se ejecuta en cuatro campañas de prueba, no como una fase final sino integradas al canal automatizado». Responsable principal: **Jhon Ortiz** (calidad y DevOps), con revisión cruzada de los tres integrantes.

## Principio rector

> La prueba de concurrencia de RNF-02 **se escribe antes** de implementar la funcionalidad y se ejecuta en cada integración (riesgo R-03 del PDF).

## Niveles de prueba

| Nivel | Qué verifica | Dónde vive | Cuándo se ejecuta | Responsable |
| --- | --- | --- | --- | --- |
| **Unit** | Reglas de negocio aisladas (RN-01 … RN-29), cálculos y validaciones | `tests/unit/` y junto al código | En cada cambio (CI) | Hedixon / Brandon |
| **Integration** | API + base de datos real: transacciones, auditoría, restricciones | `tests/integration/` | En cada cambio (CI) | Hedixon / Jhon |
| **API** | El contrato de `docs/api/` se cumple: campos, códigos, errores | `tests/integration/api/` | En cada cambio (CI) | Jhon |
| **E2E** | Flujo completo de compra y de administración en navegador | `tests/e2e/` | Al cierre de cada iteración | Brandon / Jhon |
| **Concurrency** | RNF-02: 50 solicitudes sobre 10 unidades | `tests/concurrency/` | En cada cambio que toque órdenes o inventario, y en cada iteración | Jhon |
| **Performance** | RNF-01: peso ≤ 1,5 MB y render < 3 s | `tests/performance/` | Al cierre de cada iteración | Jhon / Brandon |
| **Accessibility** | RNF-03: WCAG 2.2 AA en las cuatro pautas | `tests/e2e/a11y/` | Al cierre de cada iteración | Brandon |
| **Security** | RNF-04: TLS, credenciales, inyección, secretos | Revisión + comprobaciones automatizadas | Al cierre de cada iteración y antes de cada etiqueta | Jhon |

El canal de integración continua ejecuta **unit, integration y API en cada cambio** y detiene el despliegue si alguna falla (PDF, apartado 11 y criterio de OE-3). E2E, rendimiento y accesibilidad se ejecutan al cierre de cada iteración.

## Las cuatro campañas del PDF

| Campaña | Contenido | Requisito | Documento |
| --- | --- | --- | --- |
| 1. Pruebas unitarias sobre las reglas de negocio | RN-01 … RN-29 | Todos | Este documento |
| 2. Pruebas de integración sobre la API | EP-01 … EP-24 | REQ-01 … REQ-08 | [pruebas-api.md](pruebas-api.md) |
| 3. Prueba de concurrencia | Escenario 50/10 | RNF-02 | [pruebas-concurrencia.md](pruebas-concurrencia.md) |
| 4. Auditorías de rendimiento y accesibilidad | Peso, render, WCAG | RNF-01, RNF-03 | [casos-prueba.md](casos-prueba.md) (CP-80, CP-81) |

Complementan: prueba de usabilidad con cinco participantes (RNF-05) y revisión de seguridad (RNF-04).

## Criterios de entrada y salida

**Entrada a una campaña:** el requisito tiene criterio de aceptación escrito; el endpoint está definido en el contrato; existe ambiente con base de datos real (no simulada) para integración y concurrencia.

**Salida:**

| Nivel | Criterio de salida |
| --- | --- |
| Unit | Todas las reglas críticas (RN-08 … RN-11, RN-13, RN-16) cubiertas y en verde |
| Integration / API | Todos los endpoints con al menos un caso correcto y uno de error; contrato verificado |
| Concurrency | CP-90 en verde de forma reproducible (tres ejecuciones consecutivas) |
| Performance | Promedio de tres ejecuciones dentro de los umbrales de RNF-01 |
| Accessibility | Cero incumplimientos A/AA en las cuatro pautas del flujo principal |
| E2E | Flujo de compra y de administración completos sin intervención manual |

Si un criterio no se cumple, el PDF admite documentar la desviación con su causa y su plan de corrección (criterio de OE-4), pero **no** para RNF-02: es el núcleo no negociable.

## Cobertura mínima exigida

| Ámbito | Meta | Justificación |
| --- | --- | --- |
| Reglas de negocio (servicios del backend) | 90 % de líneas y todas las ramas de decisión de RN-08 … RN-11 | Es donde vive la propiedad que el proyecto debe demostrar |
| Resto del backend | 70 % | Equilibrio con el tiempo disponible (R-05) |
| Frontend | Pruebas de los componentes con lógica de estado (carrito, checkout, formulario de producto) | El resto se cubre con E2E |

La cobertura es un indicador, no un objetivo: un requisito crítico sin prueba es un fallo aunque la cobertura sea alta.

## Datos de prueba

- Catálogo de prueba **anonimizado** como contingencia del supuesto S-01 (riesgo R-02): el proyecto no depende de datos reales del micronegocio para probar.
- Ningún dato personal real en repositorios, capturas ni reportes (compromiso ético del PDF, apartado 12.4).
- Cada prueba de integración crea y limpia sus propios datos; ninguna depende del orden de ejecución.
- Escenario base de concurrencia: un producto, una variante, `stock_quantity = 10`.

## Trazabilidad requisito → prueba

| Requisito | Nivel principal | Casos |
| --- | --- | --- |
| REQ-01 | API + E2E | CP-01 … CP-06 |
| REQ-02 | Unit + API | CP-10 … CP-13 |
| REQ-03 | Integration + Concurrency | CP-20 … CP-25, CP-90 |
| REQ-04 | API + E2E | CP-30, CP-31 |
| REQ-05 | Integration | CP-40, CP-41 |
| REQ-06 | Integration + E2E | CP-50 … CP-55 |
| REQ-07 | Integration | CP-60 … CP-62 |
| REQ-08 | API + E2E | CP-70 … CP-73 |
| RNF-01 | Performance | CP-80 |
| RNF-02 | Concurrency | CP-90 |
| RNF-03 | Accessibility | CP-81 |
| RNF-04 | Security | CP-82 |
| RNF-05 | Usabilidad | CP-83 |
| RNF-06 | Canal automatizado | CP-84 |

La matriz completa está en [`../requisitos/trazabilidad.md`](../requisitos/trazabilidad.md).

## Gestión de defectos

| Severidad | Definición | Acción |
| --- | --- | --- |
| **Crítica** | Incumple RNF-02 o permite inventario negativo, sobreventa o pérdida de órdenes | Detiene la iteración; se corrige antes de cualquier otra tarea |
| **Alta** | Incumple un requisito del núcleo no negociable (REQ-01…04, REQ-06, REQ-08) | Se corrige dentro de la iteración |
| **Media** | Afecta REQ-05, REQ-07 o RNF-03 | Puede diferirse con acuerdo del equipo |
| **Baja** | Cosmético o de redacción | Backlog |

Todo defecto crítico se acompaña de una prueba de regresión que falle antes de la corrección.

## Herramientas previstas

Pytest para unit e integration; cliente HTTP de pruebas para API; herramienta de carga para concurrencia; auditoría de rendimiento (Lighthouse) y auditoría automatizada de accesibilidad más revisión manual. Se declaran como previstas: **no se instalan en esta fase**.

## Riesgos de la estrategia

| Riesgo | Mitigación |
| --- | --- |
| R-03 — concurrencia mal implementada | Prueba escrita antes del código; revisión cruzada obligatoria del código de la transacción |
| R-01 — ambiente de despliegue no disponible | Las pruebas deben poder ejecutarse en local con contenedores, sin depender de AWS |
| R-05 — disponibilidad reducida de un integrante | Responsabilidad secundaria por frente; nadie es único conocedor de las pruebas críticas |
| Falsos verdes por simulaciones | Integración y concurrencia se ejecutan contra PostgreSQL real, nunca contra una base simulada |
