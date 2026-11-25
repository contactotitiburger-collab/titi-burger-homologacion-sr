# Lector 2 — Inventario y recetas (24-nov-2026)

## Qué se revisó
Tablas `insumos`, `almacen` en las 5 sucursales.

## Insumos
- Unión de insumos entre las 5: 121. Comunes a las 5: 93. Hay 28 insumos que no están en todas (mismo patrón que productos: la mayoría es por el menú distinto de Cine Curto — detalle completo en `comparacion_sucursales.json`).
- **Pendiente para el mapa de cocina:** estos insumos están identificados por `idinsumo` interno de Soft Restaurant (numérico), NO por los IDs de cocina `INS-###` que ya usamos (`cocina-catalogo-id-puente`). Falta el puente idinsumo↔INS-### para que el Editor pueda homologar con sentido — no se intentó hoy porque es trabajo de escritura/mapeo, no de solo lectura.

## Almacenes — divergencia real encontrada
Todas las sucursales tienen almacén `'9'=NO USAR` y `'1'`/`'2'` como cocina/carreta (ya documentado). Pero el almacén **`'10'` significa cosas distintas entre sucursales**:

| Sucursal | Almacén '10' |
|---|---|
| Montejano | TRAPASO A OTRA SUCURSAL |
| Hacienda del Río | TRAPASO A OTRA SUCURSAL |
| San Marcos | TRAPASO A OTRA SUCURSAL |
| Villas del Rey | TRAPASO A OTRA SUCURSAL |
| **Cine Curto** | **MERMAS** |

Esto es justo el tipo de cosa que un reporte de mermas mal armado podría confundir si se trata a Cine Curto igual que a las demás (ya hay un flag de esto en memoria: `sr-no-registra-movimientos-almacen`). **Candidato real para homologar mañana**, con decisión REVISAR CONMIGO (hay que entender por qué Cine Curto lo usa distinto antes de cambiarlo).

También noté el typo "TRAPASO" (debería ser "TRASPASO") repetido igual en las 4 — no es un error nuevo, es consistente, así que no es una prioridad de homologación, solo una curiosidad.
