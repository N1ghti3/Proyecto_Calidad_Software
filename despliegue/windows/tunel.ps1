# Publica la tienda por un tunel rapido de Cloudflare, sin abrir puertos.
#
# cloudflared abre una conexion SALIENTE hacia Cloudflare y recibe por ella
# el trafico de una direccion https://<aleatoria>.trycloudflare.com, que
# entrega a Caddy en http://127.0.0.1:8080. No hace falta tocar el grupo de
# seguridad de AWS ni el firewall de Windows.
#
# Limitaciones del tunel rapido (sin cuenta de Cloudflare):
#   - la direccion es aleatoria y CAMBIA cada vez que el servicio se reinicia;
#   - no tiene garantia de disponibilidad: sirve para demostraciones, no para
#     produccion. Para una direccion fija: tunel con nombre (cuenta gratuita
#     de Cloudflare + dominio propio) o abrir 80/443 (ver windows-ec2.md).
#
# Uso (PowerShell como Administrador):
#   .\tunel.ps1                 instala o reinicia el servicio y muestra la URL
#   .\tunel.ps1 -Quitar         elimina el servicio

param(
    [string]$Base = "C:\tiendalocal",
    [string]$Cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe",
    [switch]$Quitar
)

$ErrorActionPreference = "Stop"
$nssm = Join-Path $Base "bin\nssm.exe"
$servicio = "tiendalocal-tunel"
$log = Join-Path $Base "logs\tunel.log"
$urlArchivo = Join-Path $Base "URL-PUBLICA.txt"

if ($Quitar) {
    if (Get-Service $servicio -ErrorAction SilentlyContinue) {
        Stop-Service $servicio -Force
        & $nssm remove $servicio confirm | Out-Null
    }
    Remove-Item $urlArchivo -ErrorAction SilentlyContinue
    Write-Host "Tunel eliminado."
    exit 0
}

if (-not (Test-Path $Cloudflared)) { throw "No se encontro cloudflared. Instalelo con: winget install Cloudflare.cloudflared" }
Copy-Item $Cloudflared (Join-Path $Base "bin\cloudflared.exe") -Force
$exe = Join-Path $Base "bin\cloudflared.exe"

if (-not (Get-Service $servicio -ErrorAction SilentlyContinue)) {
    & $nssm install $servicio $exe | Out-Null
}
# --no-autoupdate: la version la fija quien administra el servidor (winget).
& $nssm set $servicio AppParameters "tunnel --no-autoupdate --url http://127.0.0.1:8080 --logfile `"$log`"" | Out-Null
& $nssm set $servicio AppDirectory $Base | Out-Null
& $nssm set $servicio Start SERVICE_AUTO_START | Out-Null
& $nssm set $servicio DependOnService tiendalocal-web | Out-Null
& $nssm set $servicio AppStdout (Join-Path $Base "logs\tunel-salida.log") | Out-Null
& $nssm set $servicio AppStderr (Join-Path $Base "logs\tunel-salida.log") | Out-Null

# El registro anterior se retira para no leer una URL vieja.
Remove-Item $log -ErrorAction SilentlyContinue
Restart-Service $servicio -Force

$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep 1
    if (Test-Path $log) {
        $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -Last 1
        if ($m) { $url = $m.Matches[0].Value }
    }
}
if (-not $url) { throw "cloudflared no informo la URL en 60 s. Revise $log" }

Set-Content -Path $urlArchivo -Value "$url  (tunel rapido de Cloudflare; cambia si el servicio se reinicia)" -Encoding ascii
Write-Host "`nTienda publicada en: $url" -ForegroundColor Green
Write-Host "Panel: $url/admin"
