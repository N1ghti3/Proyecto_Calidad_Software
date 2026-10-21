# Despliegue

| Documento | Contenido |
| --- | --- |
| [windows-ec2.md](windows-ec2.md) | Despliegue nativo en la instancia EC2 Windows del proyecto (sin Docker): Caddy con HTTPS, API como servicio, PostgreSQL propio, publicación por releases, respaldos y operación. **Es el despliegue en uso.** |
| [`docker-compose.yml`](../../docker-compose.yml) | Alternativa con contenedores para un servidor Linux con Docker. |

Pendiente: integración continua (el flujo de `.github/workflows` de esta rama aún es la plantilla de GitHub; `test/capa-de-datos` trae `pruebas.yml`) y un entorno de staging separado.
