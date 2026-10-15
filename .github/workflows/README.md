# GitHub Actions

| Workflow | Cuándo corre | Qué hace |
| --- | --- | --- |
| [`pruebas.yml`](pruebas.yml) | Cada push y cada Pull Request hacia `main` | Levanta PostgreSQL 16 con la colación del proyecto, aplica las migraciones desde cero y ejecuta toda la suite de `tests/`. Publica el reporte como artefacto. Falla si falla una prueba (criterio de OE-3). |

Pendientes, cuando exista el código correspondiente:

- build de las imágenes de contenedor y control del tamaño (RNF-06, < 250 MB);
- despliegue por SSH a la instancia (dependencia crítica D-01);
- auditorías de rendimiento y accesibilidad al cierre de iteración (RNF-01, RNF-03).
