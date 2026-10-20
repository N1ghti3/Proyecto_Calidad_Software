# Descarga fotografías de demostración para el catálogo sembrado.
#
# POR QUÉ EXISTE ESTE GUION
# La siembra registra rutas de imagen (/media/productos/…) pero no puede traer
# los archivos: el catálogo es de demostración y las fotografías de los
# productos reales las aporta el micronegocio. Mientras no existan, la interfaz
# muestra un bloque de color —ver el componente `Foto` en frontend/src/App.tsx—
# y no se rompe.
#
# Este guion llena ese hueco con fotografías de Unsplash, de licencia libre
# para uso comercial y sin atribución obligatoria. NO son los productos reales:
# son aproximaciones para poder revisar la interfaz con contenido verosímil.
# Antes de un uso real deben sustituirse por fotografías del propio negocio.
#
# Se usan las direcciones del CDN (images.unsplash.com) y no el endpoint
# /photos/<id>/download, que dejó de ser anónimo y responde 401 sin una clave
# de API. El CDN sí es público: es el mismo que la interfaz ya usa para el
# banner de portada.
#
# USO
#   .\database\seeds\descargar_fotos.ps1
#   docker compose up -d --build frontend
#
# El --build no es opcional: el Dockerfile copia public/ dentro de la imagen al
# construirla, de modo que descargar los archivos sin reconstruir no cambia
# nada en lo que sirve el contenedor.

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$destino = Join-Path $PSScriptRoot "..\..\frontend\public\media\productos"
New-Item -ItemType Directory -Force -Path $destino | Out-Null

# identificador del CDN  →  nombre de archivo que la siembra espera
#
# La tercera columna es lo que la fotografía muestra según su descripción en
# Unsplash. Se deja escrita para que quien revise pueda juzgar si la
# aproximación es aceptable sin tener que abrir doce enlaces.
$fotos = @(
  @{ id = "photo-1583743814966-8936f5b7be1a"; archivo = "camiseta-oversize-negra-frente";   muestra = "camiseta negra de cuello redondo" }
  @{ id = "photo-1778671394516-8270eac13c42"; archivo = "camiseta-basica-blanca-frente";    muestra = "camiseta blanca lisa en gancho de madera" }
  @{ id = "photo-1759572095384-1a7e646d0d4f"; archivo = "camiseta-estampada-nandu-frente";  muestra = "dos camisetas, negra y verde claro, con ramas de algodon" }
  @{ id = "photo-1780565595413-16c7bc95af74"; archivo = "camiseta-tie-dye-frente";          muestra = "camiseta tenida por anudado, fondo blanco" }
  @{ id = "photo-1591047139829-d91aecb6caea"; archivo = "chaqueta-bomber-cara-algodon";     muestra = "chaqueta bomber cafe en gancho blanco" }
  @{ id = "photo-1774897796159-b295bc2a587c"; archivo = "buzo-cuello-tortuga-frente";       muestra = "buzo negro de cuello tortuga" }
  @{ id = "photo-1680292783974-a9a336c10366"; archivo = "sudadera-capucha-grafiti-frente";  muestra = "sudadera negra con capucha y texto estampado" }
  @{ id = "photo-1770239647673-1a0eb5d05a25"; archivo = "mochila-wayuu-completa";           muestra = "bolsos tejidos de colores con correas de patrones" }
  @{ id = "photo-1718909603336-62fb533e6027"; archivo = "sombrero-vueltiao-superior";       muestra = "sombrero de paja" }
  @{ id = "photo-1567455231583-6a1b94181ef4"; archivo = "hamaca-san-jacinto-extendida";     muestra = "hamaca cafe" }
  @{ id = "photo-1618722060945-b87f7326995b"; archivo = "jarron-raquira-frente";            muestra = "jarron de ceramica cafe sobre mantel blanco" }
  @{ id = "photo-1624222247344-550fb60583dc"; archivo = "cinturon-cuero-repujado-detalle";  muestra = "cinturon de cuero cafe con hebilla plateada" }
)

Write-Host ""
Write-Host "Descargando $($fotos.Count) fotografias a frontend/public/media/productos/"
Write-Host ""

$ok = 0
$fallos = @()

foreach ($f in $fotos) {
    $salida = Join-Path $destino "$($f.archivo).jpg"
    $url = "https://images.unsplash.com/$($f.id)?auto=format&fit=crop&w=1200&q=80"
    try {
        Invoke-WebRequest -Uri $url -OutFile $salida -UseBasicParsing -TimeoutSec 40
        $kb = [math]::Round((Get-Item $salida).Length / 1KB)
        Write-Host ("  OK     {0,-38} {1,5} KB   {2}" -f $f.archivo, $kb, $f.muestra)
        $ok++
    }
    catch {
        Write-Host ("  FALLA  {0,-38} {1}" -f $f.archivo, $_.Exception.Message) -ForegroundColor Yellow
        if (Test-Path $salida) { Remove-Item $salida -Force }
        $fallos += $f.archivo
    }
}

Write-Host ""
Write-Host "$ok de $($fotos.Count) descargadas."

if ($fallos.Count -gt 0) {
    Write-Host ""
    Write-Host "No se pudieron descargar: $($fallos -join ', ')" -ForegroundColor Yellow
    Write-Host "Esos productos seguiran mostrando el bloque de color, que es el"
    Write-Host "comportamiento previsto cuando falta una fotografia."
}

# Cadena literal (@' … '@): dentro no se interpreta nada, de modo que las
# comillas del comando de SQL no necesitan escaparse. PowerShell no escapa con
# barra invertida sino con acento grave: una comilla escapada al estilo de C
# rompe el análisis del archivo entero antes de ejecutar una sola línea.
Write-Host @'

Sin fotografia adecuada encontrada, quedan con bloque de color:
  - chaleco-acolchado-frente
  - pulsera-hilo-encerado-conjunto

Siguiente paso:   docker compose up -d --build frontend

Si la base todavia apunta a .webp (solo hace falta la primera vez):
  docker compose exec -T postgres psql -U tiendalocal_owner -d tiendalocal -c "UPDATE product_image SET url = replace(url, '.webp', '.jpg');"

'@
