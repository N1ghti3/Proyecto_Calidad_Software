# Instalacion inicial de TiendaLocal en un servidor Windows (EC2) sin Docker.
#
# Deja tres servicios de Windows, todos con inicio automatico:
#   tiendalocal-postgres  PostgreSQL 16 propio, puerto 5433, solo localhost,
#                         colacion ICU es-CO (ADR-011). Separado del PostgreSQL
#                         de desarrollo: los roles son del cluster y la
#                         migracion fija la contrasena de tiendalocal_app.
#   tiendalocal-api       FastAPI con uvicorn en 127.0.0.1:8001 (via NSSM).
#   tiendalocal-web       Caddy en 80/443: tienda, proxy de la API y HTTPS
#                         automatico con Let's Encrypt.
# y una tarea programada de respaldo diario (respaldo.ps1).
#
# Genera los secretos en <Base>\config\.env y deja las credenciales iniciales
# en <Base>\CREDENCIALES.txt, ambos legibles solo por Administradores y SYSTEM.
#
# NO abre puertos: el firewall de Windows y el grupo de seguridad de AWS son
# configuracion de seguridad y se dejan a quien administra el servidor (ver
# docs/despliegue/windows-ec2.md).
#
# Uso (PowerShell como Administrador), desde esta carpeta:
#   .\instalar.ps1 -Dominio 34-229-102-235.sslip.io

param(
    [Parameter(Mandatory = $true)][string]$Dominio,
    [string]$Repo = "C:\proyectos\wt-sistema",
    [string]$Commit = "HEAD",
    [string]$Base = "C:\tiendalocal",
    [string]$PgBin = "C:\Program Files\PostgreSQL\16\bin",
    [int]$PuertoPg = 5433,
    [string]$Caddy = "",
    [string]$Nssm = ""
)

$ErrorActionPreference = "Stop"
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
function Paso($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

function Secreto([int]$bytes = 24) {
    # Solo hexadecimal: va dentro de URLs de conexion y no necesita escaparse.
    $b = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    ($b | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Solo-Administradores($ruta) {
    icacls $ruta /inheritance:r /grant:r "*S-1-5-32-544:F" "*S-1-5-18:F" | Out-Null
}

function Ruta-Real($nombre, $dado) {
    if ($dado) { return $dado }
    $cmd = Get-Command $nombre -ErrorAction SilentlyContinue
    if (-not $cmd) { throw "No se encontro $nombre. Instalelo con winget (CaddyServer.Caddy / NSSM.NSSM)." }
    $item = Get-Item $cmd.Source
    if ($item.Target) { return [string]$item.Target }
    return $cmd.Source
}

# ------------------------------------------------------------ carpetas
Paso "Carpetas en $Base"
foreach ($d in "config", "releases", "media", "logs", "respaldos", "bin", "caddy\data") {
    New-Item -ItemType Directory -Force (Join-Path $Base $d) | Out-Null
}
# Los binarios se copian a <Base>\bin: los servicios no deben depender de
# rutas dentro del perfil de un usuario.
Copy-Item (Ruta-Real "caddy" $Caddy) (Join-Path $Base "bin\caddy.exe") -Force
Copy-Item (Ruta-Real "nssm" $Nssm) (Join-Path $Base "bin\nssm.exe") -Force
$nssmExe = Join-Path $Base "bin\nssm.exe"
# Los guiones viven junto a la instalacion: la tarea de respaldo y las
# publicaciones futuras no deben depender de la carpeta del repositorio.
New-Item -ItemType Directory -Force (Join-Path $Base "scripts") | Out-Null
Copy-Item (Join-Path $aqui "*") (Join-Path $Base "scripts") -Force
$aqui = Join-Path $Base "scripts"

# ------------------------------------------------------------- secretos
$envFile = Join-Path $Base "config\.env"
if (Test-Path $envFile) {
    Paso "config\.env ya existe: se conservan los secretos"
    $pwOwner = ((Select-String -Path $envFile -Pattern '^POSTGRES_PASSWORD=(.*)$').Matches[0].Groups[1].Value)
} else {
    Paso "Generando secretos"
    $pwOwner = Secreto; $pwApp = Secreto; $jwt = Secreto 48; $pwAdmin = Secreto 12
    @"
# TiendaLocal - produccion. Generado por instalar.ps1 el $(Get-Date -Format s).
# No versionar ni copiar fuera de este servidor.
POSTGRES_DB=tiendalocal
POSTGRES_USER=tiendalocal_owner
POSTGRES_PASSWORD=$pwOwner
DATABASE_URL=postgresql+psycopg://tiendalocal_app:$pwApp@127.0.0.1:$PuertoPg/tiendalocal
DATABASE_MIGRATION_URL=postgresql+psycopg://tiendalocal_owner:$pwOwner@127.0.0.1:$PuertoPg/tiendalocal
APP_DB_PASSWORD=$pwApp
JWT_SECRET=$jwt
ADMIN_SEED_PASSWORD=$pwAdmin
CORS_ORIGENES=https://$Dominio
MEDIA_DIR=$Base\media
"@ | Set-Content -Path $envFile -Encoding ascii
    Solo-Administradores $envFile

    $cred = Join-Path $Base "CREDENCIALES.txt"
    @"
TiendaLocal - credenciales iniciales de produccion ($(Get-Date -Format s))

Tienda:  https://$Dominio
Panel:   https://$Dominio/admin
Usuario: admin@example.com
Clave:   $pwAdmin

Cambie esta clave tras el primer ingreso y borre este archivo.
Base de datos (superusuario tiendalocal_owner, puerto $PuertoPg): $pwOwner
"@ | Set-Content -Path $cred -Encoding ascii
    Solo-Administradores $cred
}

# ------------------------------------------------------------ PostgreSQL
$datos = Join-Path $Base "pgdata"
if (-not (Test-Path (Join-Path $datos "PG_VERSION"))) {
    Paso "Inicializando el cluster de produccion (ICU es-CO, ADR-011)"
    $pwfile = Join-Path $env:TEMP "tl-pw-$(Secreto 4).txt"
    Set-Content -Path $pwfile -Value $pwOwner -Encoding ascii -NoNewline
    try {
        & "$PgBin\initdb.exe" -D $datos -U tiendalocal_owner --pwfile=$pwfile --auth=scram-sha-256 `
            --locale-provider=icu --icu-locale=es-CO --locale=C --encoding=UTF8
        if ($LASTEXITCODE -ne 0) { throw "initdb fallo" }
    } finally { Remove-Item $pwfile -Force }

    Add-Content (Join-Path $datos "postgresql.conf") @"

# --- TiendaLocal (instalar.ps1)
port = $PuertoPg
listen_addresses = 'localhost'
"@
    # El servicio corre como NetworkService: necesita acceso a su carpeta.
    icacls $datos /grant "*S-1-5-20:(OI)(CI)F" /T | Out-Null
}
if (-not (Get-Service tiendalocal-postgres -ErrorAction SilentlyContinue)) {
    Paso "Servicio tiendalocal-postgres"
    & "$PgBin\pg_ctl.exe" register -N tiendalocal-postgres -D $datos -S auto
}
Start-Service tiendalocal-postgres
$env:PGPASSWORD = $pwOwner
try {
    for ($i = 0; $i -lt 20; $i++) { & "$PgBin\pg_isready.exe" -h 127.0.0.1 -p $PuertoPg | Out-Null; if ($LASTEXITCODE -eq 0) { break }; Start-Sleep 1 }
    $existe = & "$PgBin\psql.exe" -h 127.0.0.1 -p $PuertoPg -U tiendalocal_owner -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'tiendalocal'"
    if (-not $existe) {
        & "$PgBin\psql.exe" -h 127.0.0.1 -p $PuertoPg -U tiendalocal_owner -d postgres -c "CREATE DATABASE tiendalocal"
    }
} finally { Remove-Item Env:PGPASSWORD }

# -------------------------------------------------------------- release
Paso "Primera publicacion"
& (Join-Path $aqui "publicar.ps1") -Repo $Repo -Commit $Commit -Base $Base
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) { throw "publicar.ps1 fallo" }

# --------------------------------------------------------------- Caddy
Paso "Configuracion de Caddy"
$baseBarras = $Base -replace '\\', '/'
(Get-Content (Join-Path $aqui "Caddyfile.plantilla") -Raw -Encoding utf8) `
    -replace '\{\{DOMINIO\}\}', $Dominio -replace '\{\{BASE\}\}', $baseBarras |
    Set-Content -Path (Join-Path $Base "caddy\Caddyfile") -Encoding utf8
& (Join-Path $Base "bin\caddy.exe") validate --config (Join-Path $Base "caddy\Caddyfile") --adapter caddyfile
if ($LASTEXITCODE -ne 0) { throw "Caddyfile invalido" }

# ------------------------------------------------------------- servicios
function Servicio($nombre, $exe, $argumentos, $directorio, $entorno, $depende) {
    if (-not (Get-Service $nombre -ErrorAction SilentlyContinue)) {
        & $nssmExe install $nombre $exe | Out-Null
    }
    & $nssmExe set $nombre Application $exe | Out-Null
    & $nssmExe set $nombre AppParameters $argumentos | Out-Null
    & $nssmExe set $nombre AppDirectory $directorio | Out-Null
    & $nssmExe set $nombre AppStdout (Join-Path $Base "logs\$nombre.log") | Out-Null
    & $nssmExe set $nombre AppStderr (Join-Path $Base "logs\$nombre-error.log") | Out-Null
    & $nssmExe set $nombre AppRotateFiles 1 | Out-Null
    & $nssmExe set $nombre AppRotateBytes 10485760 | Out-Null
    & $nssmExe set $nombre Start SERVICE_AUTO_START | Out-Null
    if ($entorno) { & $nssmExe set $nombre AppEnvironmentExtra $entorno | Out-Null }
    if ($depende) { & $nssmExe set $nombre DependOnService $depende | Out-Null }
}

Paso "Servicio tiendalocal-api"
Servicio "tiendalocal-api" (Join-Path $Base "actual\backend\.venv\Scripts\python.exe") `
    "-m uvicorn app.main:app --host 127.0.0.1 --port 8001 --proxy-headers --forwarded-allow-ips 127.0.0.1" `
    (Join-Path $Base "actual\backend") $null "tiendalocal-postgres"

Paso "Servicio tiendalocal-web"
# Caddy guarda certificados y su cuenta ACME en %AppData%\Caddy.
Servicio "tiendalocal-web" (Join-Path $Base "bin\caddy.exe") `
    "run --config `"$Base\caddy\Caddyfile`" --adapter caddyfile" `
    (Join-Path $Base "caddy") "AppData=$Base\caddy\data" "tiendalocal-api"

Restart-Service tiendalocal-api
Restart-Service tiendalocal-web

# --------------------------------------------------------------- respaldos
Paso "Tarea de respaldo diario (03:00)"
$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$aqui\respaldo.ps1`" -Base `"$Base`" -PgBin `"$PgBin`""
$disparador = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "TiendaLocal - respaldo diario" -Action $accion -Trigger $disparador `
    -User "SYSTEM" -RunLevel Highest -Force | Out-Null

Write-Host "`nInstalacion completa." -ForegroundColor Green
Write-Host "Credenciales iniciales: $Base\CREDENCIALES.txt"
Write-Host "Falta abrir 80 y 443 en el firewall de Windows y en el grupo de seguridad de AWS."
