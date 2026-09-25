# ADR-001 — Arquitectura en capas sobre los componentes C1–C6

- **Estado:** Aceptada
- **Fecha:** 2026-09-25
- **Decide:** Equipo completo
- **Respaldo en el PDF:** apartado 9.3 (componentes C1–C6, actores y flujos) y apartado 10 (Tabla 2: motor relacional autoalojado en contenedor). La **estructura interna del backend** no está en el PDF: `DECISIÓN PROPUESTA`.

## Contexto

El PDF fija los componentes desplegables (C1 frontend, C2 proxy inverso, C3 API REST, C4 base de datos relacional, C5 imágenes, C6 auditoría), los actores y el flujo crítico de confirmación de orden. No define cómo se organiza internamente C3 ni dónde vive cada tipo de validación.

Sin esa definición, tres personas trabajando en horarios distintos colocarían las reglas de negocio en lugares diferentes (rutas, modelos, base de datos), y la propiedad de RNF-02 quedaría repartida y no verificable.

Restricciones: presupuesto nulo (R-03), tres integrantes a tiempo parcial durante dieciséis semanas (R-05), el negocio no administra infraestructura (R-01) y debe poderse migrar de proveedor en menos de dos días (riesgo R-01).

## Alternativas consideradas

1. **Monolito modular en capas (interfaz → servicios → repositorios → base de datos)**, desplegado en contenedores.
2. **Rutas con acceso directo a la base de datos**, sin capa de servicios.
3. **Microservicios** (catálogo, órdenes, inventario) con comunicación por red.

| Criterio | A1 capas | A2 directo | A3 microservicios |
| --- | --- | --- | --- |
| Esfuerzo en 16 semanas (R-05) | Medio | Bajo | Alto |
| Costo operativo (R-03) | Bajo | Bajo | Alto |
| Control de la transacción (RNF-02) | Alto: una sola transacción local | Medio: la regla se dispersa | Bajo: transacción distribuida |
| Verificabilidad de las reglas | Alta: servicios probables sin HTTP | Baja | Media |
| Portabilidad entre proveedores | Alta | Alta | Media |

## Decisión

Monolito modular desplegado en contenedores, con C3 dividido en cuatro subcapas:

| Subcapa | Responsabilidad | Prohibido |
| --- | --- | --- |
| Interfaz (routers) | Rutas, validación de formato, autenticación, códigos HTTP, serialización | Contener reglas de negocio |
| Servicios | RN-01 … RN-29, transacciones, orquestación | Conocer HTTP |
| Repositorios | Consultas parametrizadas, bloqueos, acceso a C4 | Decidir reglas |
| Esquemas | Contratos de petición y respuesta | Duplicar nombres fuera del contrato |

Complementos: la lógica de negocio no vive en procedimientos almacenados (una sola ubicación por regla), y el sistema no depende de servicios propietarios de AWS.

## Consecuencias

**Positivas**

- La transacción crítica ocurre en un solo proceso y una sola base de datos: RNF-02 es demostrable.
- Las reglas se prueban sin levantar HTTP (campaña unitaria) y el contrato se prueba sin conocer la implementación (campaña de API).
- Migración de proveedor sin cambios de arquitectura (mitiga R-01).
- Cada integrante tiene un límite claro: Brandon consume el contrato, Hedixon implementa servicios y repositorios, Jhon prueba y despliega.

**Negativas / riesgos**

- Un monolito escala de forma menos granular; irrelevante para el volumen de un micronegocio y fuera de los requisitos.
- La disciplina de capas depende de la revisión cruzada: si una regla se cuela en un router, el diseño se degrada. Se controla en la revisión obligatoria de Pull Request.

## Verificación

- Revisión cruzada de cada Pull Request que toque C3.
- Las pruebas unitarias de reglas no pueden importar componentes HTTP: si lo necesitan, la regla está mal ubicada.
- CP-90 y CP-84 verifican el comportamiento y el despliegue resultantes.
