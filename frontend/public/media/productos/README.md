# Fotografías de producto

Las rutas que el catálogo guarda en la base de datos apuntan aquí. Por ejemplo,
el producto sembrado como `camiseta-oversize-negra` espera encontrar:

    /media/productos/camiseta-oversize-negra-frente.webp

Vite copia esta carpeta tal cual al construir, y nginx la sirve con caché de
treinta días. En desarrollo funciona igual sin configurar nada.

## Mientras no existan

La interfaz no se rompe: muestra el bloque de color del producto y conserva la
descripción en `aria-label`, de modo que un lector de pantalla sigue
anunciándola. Eso es deliberado —ver el componente `Foto` en `src/App.tsx`—
porque una fotografía que falta es contenido pendiente, no un fallo del
sistema, y no debe parecerlo.

## Para añadirlas

Basta con dejar los archivos con el nombre exacto que la siembra registró. Para
ver qué nombres espera:

```sql
SELECT p.slug, i.url, i.alt
  FROM product p JOIN product_image i ON i.product_id = p.id
 ORDER BY p.slug;
```

Formato recomendado: WebP, lado mayor de 1200 px, calidad 80. El presupuesto de
peso de página (RNF-01) es de 1,5 MB y hoy la interfaz usa 90 KB, de modo que
hay margen amplio; aun así conviene no subir originales de cámara.
