# ADR-002 — El inventario pertenece a la variante (SKU), no al producto

- **Estado:** Aceptada
- **Fecha:** 2026-09-25
- **Decide:** Hedixon Cardozo (backend), con acuerdo del equipo
- **Respaldo en el PDF:** parcial. El PDF exige filtro por **talla** (REQ-01) y menciona un «modelo de datos de producto con atributos, variantes y estado de publicación» (Tabla 8), pero **no declara dónde residen las existencias**: `DECISIÓN PROPUESTA`.

## Contexto

El proyecto vende moda urbana y artesanías. El catálogo debe permitir filtrar por talla y mostrar «la disponibilidad actual» de cada producto (criterio CA-01-0). La propiedad central del proyecto (RNF-02) se enuncia sobre «un producto con 10 unidades».

La pregunta es qué representa esa cifra: ¿10 unidades del producto, o 10 de una talla concreta?

Si las existencias colgaran del producto:

- no podría responderse «quedan 2 en M y 0 en L»;
- un comprador podría confirmar una talla agotada mientras el producto aún tiene unidades en otra;
- el filtro por talla mostraría disponibilidad que no corresponde a lo que se compra;
- la prueba de concurrencia verificaría un número que no es el que se descuenta en la vida real.

## Alternativas consideradas

1. **Existencias por producto** (`product.stock_quantity`).
2. **Existencias por variante** (`inventory.stock_quantity` con relación 1:1 a `product_variant`).
3. **Existencias por producto con reparto lógico por talla** (una tabla de tallas sin inventario propio, repartiendo el total).

| Criterio | A1 producto | A2 variante | A3 reparto |
| --- | --- | --- | --- |
| Soporta filtro y disponibilidad por talla (REQ-01) | No | Sí | Parcial |
| Permite verificar RNF-02 sobre lo que se compra | No | Sí | No |
| Complejidad del modelo | Baja | Media | Alta |
| Riesgo de inconsistencia | Alto | Bajo | Alto |
| Compatible con productos artesanales de pieza única | Sí | Sí (una variante «única») | Sí |

## Decisión

Las existencias se almacenan **por variante**:

- `product_variant` es la unidad vendible; la distingue la talla.
- `inventory` tiene relación 1:1 con la variante y su clave primaria es `variant_id`.
- La disponibilidad de un producto (`availableUnits`) es una **suma derivada** de sus variantes activas; nunca se almacena en `product`.
- Toda línea de carrito y de orden referencia `variantId`, no `productId` (RN-05).
- Los productos sin tallas (artesanías de pieza única) se modelan con **una sola variante**, por ejemplo `size = "ÚNICA"`, para no crear dos caminos distintos en el código.

## Consecuencias

**Positivas**

- REQ-01 (filtro por talla con disponibilidad real) queda soportado sin cálculos artificiales.
- RNF-02 se verifica sobre la misma fila que se descuenta al comprar.
- El bloqueo de RN-10 opera sobre filas pequeñas y específicas, reduciendo la contención entre productos distintos.
- La auditoría de existencias (REQ-06.3) identifica exactamente qué talla cambió.

**Negativas / riesgos**

- El alta de un producto exige declarar al menos una variante, lo que añade un paso al formulario del propietario (RNF-05). Se mitiga con un valor por defecto `ÚNICA` cuando el producto no maneja tallas.
- La API expone dos identificadores (`productId` y `variantId`) y el frontend debe usar el correcto al comprar. Se mitiga documentando en `modelos.md` que `ProductVariantResponse.id` es «el identificador que se usa para comprar».
- Una orden con varias tallas del mismo producto bloquea varias filas: el orden determinista de RN-10 evita interbloqueos.

## Verificación

- CP-05: el detalle muestra disponibilidad por talla.
- CP-02: el filtro por talla devuelve lo esperado.
- CP-90: la prueba de concurrencia opera sobre una variante con 10 unidades.
- CP-50: la auditoría registra el cambio de una talla concreta.
