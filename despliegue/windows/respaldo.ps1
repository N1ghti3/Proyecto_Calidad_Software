# Respaldo diario de TiendaLocal: base de datos (pg_dump) e imagenes cargadas.
#
# instalar.ps1 lo programa como tarea diaria a las 03:00. Conserva los
# ultimos $Dias respaldos. Restaurar la base:
#   pg_restore -h 127.0.0.1 -p 5433 -U tiendalocal_owner -d tiendalocal --clean <archivo.dump>
#
# Estos respaldos viven en el mismo disco que la base: protegen de un error
# humano o de una migracion fallida, no de perder el servidor. Para eso hay
# que copiarlos fuera (S3, otro equipo) o usar instantaneas del volumen EBS.

param(
    [string]$Base = "C:\tiendalocal",
    [string]$PgBin = "C:\Program Files\PostgreSQL\16\bin",
    [int]$Dias = 14
)

$ErrorActionPreference = "Stop"
$destino = Join-Path $Base "respaldos"
New-Item -ItemType Directory -Force $destino | Out-Null
$marca = Get-Date -Format "yyyyMMdd-HHmmss"

# Credenciales del propietario, leidas del .env de produccion.
$url = (Select-String -Path (Join-Path $Base "config\.env") -Pattern '^DATABASE_MIGRATION_URL=(.*)$').Matches[0].Groups[1].Value
if ($url -notmatch '://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$') { throw "DATABASE_MIGRATION_URL con formato inesperado" }
$env:PGPASSWORD = $Matches[2]
try {
    & "$PgBin\pg_dump.exe" -h $Matches[3] -p $Matches[4] -U $Matches[1] -d $Matches[5] -Fc -f (Join-Path $destino "tiendalocal-$marca.dump")
    if ($LASTEXITCODE -ne 0) { throw "pg_dump fallo con codigo $LASTEXITCODE" }
} finally { Remove-Item Env:PGPASSWORD }

$media = Join-Path $Base "media"
if ((Test-Path $media) -and (Get-ChildItem $media -Recurse -File | Select-Object -First 1)) {
    Compress-Archive -Path "$media\*" -DestinationPath (Join-Path $destino "media-$marca.zip")
}

Get-ChildItem $destino -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$Dias) } | Remove-Item
Write-Host "Respaldo $marca listo en $destino"
