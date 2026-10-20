# Despliegue en Windows Server (EC2) sin Docker

Guía del despliegue que corre en la instancia EC2 del proyecto (Windows Server 2025, t3.large, us-east-1). Esa máquina no admite virtualización anidada, de modo que Docker no está disponible y el sistema corre de forma nativa. La alternativa con contenedores (`docker-compose.yml`) sigue siendo válida para cualquier servidor Linux.

## Arquitectura

```
Internet ──443/80──► Caddy (tiendalocal-web)
                       ├─ /            → frontend\dist (archivos estáticos)
                       ├─ /api/*       → 127.0.0.1:8001  FastAPI (tiendalocal-api)
                       └─ /media/cargas/* → 127.0.0.1:8001
                                              │
                                              ▼
                                   PostgreSQL 16 (tiendalocal-postgres)
                                   127.0.0.1:5433, colación ICU es-CO
```

| Servicio de Windows | Qué es | Escucha en |
|---|---|---|
| `tiendalocal-web` | Caddy 2: HTTPS automático con Let's Encrypt, compresión, encabezados de seguridad (HSTS, CSP) | 0.0.0.0:80 y :443 |
| `tiendalocal-api` | FastAPI + uvicorn, ejecutado con NSSM | 127.0.0.1:8001 |
| `tiendalocal-postgres` | PostgreSQL 16 propio de producción | 127.0.0.1:5433 |

Los tres arrancan solos con el sistema. La base de producción es **un clúster aparte** del PostgreSQL de desarrollo (puerto 5432): los roles de PostgreSQL son del clúster y la migración inicial fija la contraseña de `tiendalocal_app`, de modo que compartirlo obligaría a usar las mismas credenciales en desarrollo y en producción.

Dirección pública: `https://34-229-102-235.sslip.io`. sslip.io es un DNS gratuito que resuelve ese nombre a la IP 34.229.102.235; con él Let's Encrypt puede emitir el certificado sin comprar un dominio. Para usar un dominio propio basta crear su registro A hacia la IP y reemplazar el nombre en `C:\tiendalocal\caddy\Caddyfile` y `CORS_ORIGENES` en `C:\tiendalocal\config\.env`.

## Carpetas

```
C:\tiendalocal\
  actual\        enlace a la release activa (los servicios corren desde aquí)
  releases\<commit>\   una carpeta inmutable por versión publicada
  config\.env    secretos de producción (solo Administradores y SYSTEM)
  CREDENCIALES.txt     clave inicial del panel (bórrese tras cambiarla)
  pgdata\        datos de PostgreSQL
  media\         imágenes cargadas desde el panel
  respaldos\     pg_dump diario + zip de media (14 días)
  logs\          registros de los tres servicios y de Caddy
  caddy\         Caddyfile y certificados
  scripts\       instalar.ps1, publicar.ps1, respaldo.ps1
  bin\           caddy.exe, nssm.exe
```

## Instalación (una vez)

Requisitos: PostgreSQL 16 (binarios en `C:\Program Files\PostgreSQL\16\bin`), Python 3.12 en `C:\Python312`, Node 22 en `C:\tools\node-v22.22.0-win-x64` y, con winget, `CaddyServer.Caddy` y `NSSM.NSSM`.

```powershell
cd C:\proyectos\wt-sistema\despliegue\windows
.\instalar.ps1 -Dominio 34-229-102-235.sslip.io
```

El guion genera los secretos, inicializa el clúster, crea la base, publica la versión actual del repositorio, registra los servicios y programa el respaldo diario. Es repetible: si `config\.env` ya existe, conserva los secretos.

### Pasos que quedan a cargo de quien administra el servidor

Son configuración de seguridad y no los hace ningún guion:

1. **Grupo de seguridad de AWS** (`launch-wizard-6`): permitir entrada TCP 80 y 443 desde `0.0.0.0/0`. Conviene restringir 3389 (RDP) a la IP de quien administra y **no** abrir 5432 ni 5433.
2. **Firewall de Windows**, en PowerShell como Administrador:
   ```powershell
   New-NetFirewallRule -DisplayName "TiendaLocal HTTP"  -Direction Inbound -Protocol TCP -LocalPort 80  -Action Allow
   New-NetFirewallRule -DisplayName "TiendaLocal HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
   ```
3. Con los puertos abiertos, Caddy obtiene el certificado solo en el siguiente minuto. Se comprueba en `C:\tiendalocal\logs\caddy.log` («certificate obtained successfully»).

## Publicar una versión nueva

```powershell
cd C:\tiendalocal\scripts
.\publicar.ps1 -Repo C:\proyectos\wt-sistema -Commit <rama-o-commit>
```

Construye `releases\<commit>` (dependencias, frontend y `.env`), aplica las migraciones, mueve el enlace `actual` y reinicia la API y Caddy. La tienda queda fuera de servicio solo los segundos del reinicio.

**Revertir** a la versión anterior (la base de datos no se revierte; si la versión nueva traía una migración, hay que bajarla antes con `alembic downgrade`):

```powershell
.\publicar.ps1 -Revertir <commit-anterior>
```

## Operación

| Tarea | Comando |
|---|---|
| Estado | `Get-Service tiendalocal-*` |
| Reiniciar | `Restart-Service tiendalocal-api, tiendalocal-web` |
| Salud de la API | `Invoke-RestMethod http://127.0.0.1:8001/api/v1/health` |
| Versión activa | `Get-Content C:\tiendalocal\VERSION` |
| Registros | `C:\tiendalocal\logs\` (rotan a los 10 MB) |
| Respaldo manual | `C:\tiendalocal\scripts\respaldo.ps1` |
| Restaurar | `pg_restore -h 127.0.0.1 -p 5433 -U tiendalocal_owner -d tiendalocal --clean <archivo.dump>` |

Los respaldos quedan en el mismo disco: protegen de un error humano o de una migración fallida, no de perder la instancia. Para eso conviene programar instantáneas del volumen EBS (AWS Backup o Data Lifecycle Manager) o copiar `respaldos\` a S3.

## Seguridad

- HTTPS con certificado de Let's Encrypt renovado automáticamente por Caddy; HSTS de un año.
- Content-Security-Policy: solo el propio origen, más las imágenes de Unsplash y las fuentes de Google.
- La API y PostgreSQL escuchan solo en localhost; lo único expuesto son 80 y 443.
- La IP real del cliente llega a la API (Caddy reescribe `X-Forwarded-For`; uvicorn solo confía en 127.0.0.1), de modo que el límite de intentos de inicio de sesión funciona por IP.
- Secretos generados al instalar, en `config\.env` con permisos restringidos; nunca en el repositorio.

## Limitaciones conocidas

- Una sola instancia: sin balanceador ni réplica. Si la máquina cae, la tienda cae.
- El límite de intentos de inicio de sesión vive en memoria del proceso (un solo trabajador de uvicorn).
- Las notificaciones por correo quedan pendientes (DT-01): no hay proveedor SMTP configurado.
