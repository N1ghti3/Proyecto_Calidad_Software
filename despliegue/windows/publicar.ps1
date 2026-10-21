# Publica una version de TiendaLocal en este servidor Windows (sin Docker).
#
# Construye una "release" inmutable en <Base>\releases\<commit> a partir de un
# commit del repositorio, aplica las migraciones y cambia el enlace
# <Base>\actual para que apunte a ella. Los servicios siempre corren desde
# <Base>\actual, de modo que volver a la version anterior es repuntar el
# enlace y reiniciar:  .\publicar.ps1 -Revertir <commit-anterior>
#
# Uso (PowerShell como Administrador):
#   .\publicar.ps1 -Repo C:\proyectos\wt-sistema -Commit HEAD
#
# Requiere que instalar.ps1 se haya ejecutado una vez (crea config\.env,
# la base y los servicios).

param(
    [string]$Repo = "C:\proyectos\wt-sistema",
    [string]$Commit = "HEAD",
    [string]$Base = "C:\tiendalocal",
    [string]$Python = "C:\Python312\python.exe",
    [string]$NodeDir = "C:\tools\node-v22.22.0-win-x64",
    [string]$Revertir = ""
)

$ErrorActionPreference = "Stop"

function Paso($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

# Ejecuta un programa nativo y decide el exito por su codigo de salida. En
# PowerShell 5.1, con ErrorActionPreference=Stop, cualquier linea en stderr
# (Alembic, npm y pip escriben ahi sus mensajes normales) se trata como error
# aunque el programa termine bien.
function Ejecutar([scriptblock]$Bloque, [string]$Fallo) {
    $previo = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Bloque 2>&1 | ForEach-Object { Write-Host "  $_" } }
    finally { $ErrorActionPreference = $previo }
    if ($LASTEXITCODE -ne 0) { throw "$Fallo (codigo $LASTEXITCODE)" }
}

function Cambiar-Enlace($destino) {
    $enlace = Join-Path $Base "actual"
    if (Test-Path $enlace) { cmd /c rmdir "$enlace" | Out-Null }
    cmd /c mklink /J "$enlace" "$destino" | Out-Null
}

function Reiniciar-Servicios {
    foreach ($s in "tiendalocal-api", "tiendalocal-web") {
        if (Get-Service $s -ErrorAction SilentlyContinue) {
            Restart-Service $s -Force
            Write-Host "  reiniciado $s"
        }
    }
}

function Esperar-Salud {
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $r = Invoke-RestMethod "http://127.0.0.1:8001/api/v1/health" -TimeoutSec 3
            if ($r.database -eq "ok") { Write-Host "  API sana: $($r | ConvertTo-Json -Compress)"; return }
        } catch { }
        Start-Sleep 1
    }
    throw "La API no respondio sana en 30 s. Revise $Base\logs\api-error.log"
}

if ($Revertir) {
    $destino = Join-Path $Base "releases\$Revertir"
    if (-not (Test-Path $destino)) { throw "No existe la release $Revertir en $Base\releases" }
    Paso "Revirtiendo a $Revertir (la base de datos NO se revierte)"
    Cambiar-Enlace $destino
    Reiniciar-Servicios
    if (Get-Service tiendalocal-api -ErrorAction SilentlyContinue) { Esperar-Salud }
    exit 0
}

$config = Join-Path $Base "config\.env"
if (-not (Test-Path $config)) { throw "Falta $config. Ejecute primero instalar.ps1." }

$sha = (git -C $Repo rev-parse --short=7 $Commit).Trim()
$destino = Join-Path $Base "releases\$sha"
Paso "Release $sha en $destino"

if (Test-Path $destino) {
    Write-Host "  ya existe: se reutiliza (borrela para reconstruirla)"
} else {
    $zip = Join-Path $env:TEMP "tiendalocal-$sha.zip"
    Ejecutar { git -C $Repo archive --format=zip -o $zip $sha } "git archive fallo"
    Expand-Archive $zip -DestinationPath $destino
    Remove-Item $zip

    # Las fotos de demostracion no se versionan (.gitignore); si el repositorio
    # de origen las tiene descargadas, viajan con la release.
    $fotos = Join-Path $Repo "frontend\public\media\productos"
    if (Test-Path $fotos) {
        $destinoFotos = Join-Path $destino "frontend\public\media\productos"
        New-Item -ItemType Directory -Force $destinoFotos | Out-Null
        Copy-Item (Join-Path $fotos "*") $destinoFotos -Force
    }

    Copy-Item $config (Join-Path $destino ".env")

    Paso "Dependencias del backend"
    Ejecutar { & $Python -m venv (Join-Path $destino "backend\.venv") } "no se pudo crear el entorno virtual"
    $py = Join-Path $destino "backend\.venv\Scripts\python.exe"
    Ejecutar { & $py -m pip install --quiet --disable-pip-version-check -r (Join-Path $destino "backend\requirements.txt") } "pip install fallo"

    Paso "Construccion del frontend"
    $env:Path = "$NodeDir;$env:Path"
    Push-Location (Join-Path $destino "frontend")
    try {
        Ejecutar { & "$NodeDir\npm.cmd" ci --no-audit --no-fund --loglevel=error } "npm ci fallo"
        Ejecutar { & "$NodeDir\npm.cmd" run build } "la construccion del frontend fallo"
    } finally { Pop-Location }
}

Paso "Migraciones"
Push-Location (Join-Path $destino "backend")
try {
    Ejecutar { & ".\.venv\Scripts\python.exe" -m alembic upgrade head } "alembic upgrade fallo"
} finally { Pop-Location }

Paso "Activando la release"
Cambiar-Enlace $destino
Set-Content -Path (Join-Path $Base "VERSION") -Value "$sha $(Get-Date -Format s)" -Encoding ascii
Reiniciar-Servicios
if (Get-Service tiendalocal-api -ErrorAction SilentlyContinue) { Esperar-Salud }
Write-Host "`nPublicada $sha." -ForegroundColor Green
