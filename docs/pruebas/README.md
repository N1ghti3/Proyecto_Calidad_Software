# Pruebas

Corresponde a las cuatro campañas de verificación del apartado 11 del PDF. Responsable principal: Jhon Ortiz.

| Documento | Contenido |
| --- | --- |
| [estrategia-pruebas.md](estrategia-pruebas.md) | Niveles (unit, integration, API, E2E, concurrencia, rendimiento, accesibilidad, seguridad), criterios de entrada y salida, cobertura y gestión de defectos |
| [casos-prueba.md](casos-prueba.md) | CP-01 … CP-90 con precondición, acción, resultado esperado y criterio asociado |
| [pruebas-api.md](pruebas-api.md) | Verificación del contrato de `docs/api/` endpoint por endpoint |
| [pruebas-concurrencia.md](pruebas-concurrencia.md) | CP-90: 50 solicitudes simultáneas sobre 10 unidades (RNF-02) |

Pendiente hasta la fase de construcción: los resultados de ejecución de cada campaña, que se archivarán como evidencia de los indicadores I-02, I-04, I-05, I-06, I-07 e I-08.

> Regla del proyecto: la prueba de concurrencia se escribe **antes** de implementar la funcionalidad (riesgo R-03).
