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
# USO
#   .\database\seeds\descargar_fotos.ps1
#   docker compose exec -T postgres psql -U tiendalocal_owner -d tiendalocal `
#       -c "UPDATE product_image SET url = replace(url, '.webp', '.jpg');"
#   docker compose up -d --build frontend
#
# El UPDATE es necesario porque Unsplash entrega JPEG y la siembra registró
# .webp. Renombrar a .webp un archivo JPEG haría que nginx declarara un tipo de
# contenido que no corresponde, así que se ajusta la ruta en lugar del archivo.

$ErrorActionPreference = "Stop"

$destino = Join-Path $PSScriptRoot "..\..\frontend\public\media\productos"
New-Item -ItemType Directory -Force -Path $destino | Out-Null

# slug de Unsplash  →  nombre de archivo que la siembra espera (sin extensión)
#
# La tercera columna es lo que la fotografía muestra según su descripción en
# Unsplash. Se deja escrita para que quien revise pueda juzgar si la
# aproximación es aceptable sin tener que abrir cada enlace.
$fotos = @(
  @{ id = "Wr0TpKqf26s"; archivo = "camiseta-oversize-negra-frente";      muestra = "camiseta negra de cuello redondo" }
  @{ id = "8ACmRoleM24"; archivo = "camiseta-basica-blanca-frente";       muestra = "camiseta blanca lisa colgada de un gancho de madera" }
  @{ id = "EFCpLBQbxIU"; archivo = "camiseta-estampada-nandu-frente";     muestra = "dos camisetas, negra y verde claro, con ramas de algodón" }
  @{ id = "y8JrDRdwO0M"; archivo = "camiseta-tie-dye-frente";             muestra = "persona con camiseta teñida por anudado sobre fondo blanco" }
  @{ id = "Fg15LdqpWrs"; archivo = "chaqueta-bomber-cara-algodon";        muestra = "chaqueta bomber café sostenida en un gancho blanco" }
  @{ id = "2a4NiXPIG9I"; archivo = "buzo-cuello-tortuga-frente";          muestra = "buzo negro de cuello tortuga" }
  @{ id = "SXpun7pdECU"; archivo = "sudadera-capucha-grafiti-frente";     muestra = "sudadera negra con capucha y texto estampado" }
  @{ id = "J4U6Q-8vt-c"; archivo = "mochila-wayuu-completa";              muestra = "bolsos tejidos de colores con correas de patrones" }
  @{ id = "6Tiy9BBCRKM"; archivo = "sombrero-vueltiao-superior";          muestra = "sombrero de paja" }
  @{ id = "wpeNVgR-tcA"; archivo = "hamaca-san-jacinto-extendida";        muestra = "hamaca café" }
  @{ id = "7JqR7Vdv8aQ"; archivo = "jarron-raquira-frente";               muestra = "jarrón de cerámica café sobre mantel blanco" }
  @{ id = "KAx7H0jxo28"; archivo = "cinturon-cuero-repujado-detalle";     muestra = "cinturón de cuero café con hebilla plateada" }
)

Write-Host "Descargando $($fotos.Count) fotografías a frontend/public/media/productos/`n"

$ok = 0
$fallos = @()

foreach ($f in $fotos) {
    $salida = Join-Path $destino "$($f.archivo).jpg"
    $url = "https://unsplash.com/photos/$($f.id)/download?force=true&w=1200"
    try {
        Invoke-WebRequest -Uri $url -OutFile $salida -UseBasicParsing -MaximumRedirection 5
        $kb = [math]::Round((Get-Item $salida).Length / 1KB)
        Write-Host ("  OK   {0,-40} {1,5} KB   {2}" -f $f.archivo, $kb, $f.muestra)
        $ok++
    }
    catch {
        Write-Host ("  FALLA {0,-40} {1}" -f $f.archivo, $_.Exception.Message) -ForegroundColor Yellow
        $fallos += $f.archivo
    }
}

Write-Host "`n$ok de $($fotos.Count) descargadas."

if ($fallos.Count -gt 0) {
    Write-Host "`nNo se pudieron descargar: $($fallos -join ', ')" -ForegroundColor Yellow
    Write-Host "Esos productos seguirán mostrando el bloque de color, que es el"
    Write-Host "comportamiento previsto cuando falta una fotografía."
}

Write-Host @"

Faltan por cubrir, sin fotografía adecuada encontrada:
  · chaleco-acolchado-reversible
  · pulsera-en-hilo-encerado

Siguientes pasos:

  docker compose exec -T postgres psql -U tiendalocal_owner -d tiendalocal ``
      -c "UPDATE product_image SET url = replace(url, '.webp', '.jpg');"

  docker compose up -d --build frontend

"@
