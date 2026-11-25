# Lector 1 — Menú y precios (24-nov-2026)

## Qué se revisó
Tablas `productos`, `productosdetalle` (precio), `grupos` en las 5 sucursales conectadas, vía el MCP de solo lectura.

## Conteo
| Sucursal | Productos | Insumos |
|---|---|---|
| Montejano | 233 | 113 |
| Hacienda del Río | 233 | 113 |
| San Marcos | 233 | 113 |
| Villas del Rey | 233 | 113 |
| Cine Curto | 164 | 101 |

**Hallazgo principal:** Montejano, Hacienda del Río, San Marcos y Villas del Rey tienen el **mismo catálogo** (233 productos idénticos). **Cine Curto es distinto a propósito** — su ficha de credenciales ya lo anotaba: "menú propio (boneless, aros de cebolla, sliders, papas en gajo)". No es un descuadre, es una sucursal con oferta diferente (probablemente por estar en el cine).

## Productos que no están en las 5 (99 en total — detalle completo en `comparacion_sucursales.json`)
La enorme mayoría es exactamente ese patrón: existe en las 4 "carretas normales" pero no en Cine Curto, o viceversa. Ejemplos:
- Cine Curto únicos: `D..DEDOS DE QUESO`, `BONELESS MISTO MANGO A. BUFALO/BBQ`, `HAMBURGUSA SLIDE`, `ADEREZO DE LA CASA 2 ONZ`.
- Solo en las 4 normales (no en Cine Curto): combos tipo `TITI COMBO...`, promos de delivery (`...DIDI`, `...RAPPI`, `...UBER`).

## Precios distintos entre sucursales — 77 productos (detalle completo en el JSON)
Entre Montejano/Hacienda/San Marcos/Villas los precios son **idénticos en todo lo revisado** (no hay divergencia entre esas 4). Toda la divergencia de precio está concentrada en **Cine Curto**, que cobra distinto en ambas direcciones:
- Más caro en Cine Curto: Coca-Cola/Pepsi/Manzanita/Root Beer $50-60 vs $40 en las demás; Papas a la francesa $80 vs $55; Combo pareja $680 vs $480.
- Más barato o en $0 en Cine Curto: varios combos de delivery aparecen en $0 (ej. `BONELESS + MEDIA ORDEN DE PAPAS RAPPI`, `COMBO DOBLE QUESO + PAPAS + BEBIDA UBER`) — **esto sí parece un pendiente real**, no una decisión de negocio: productos de delivery con precio $0 en Cine Curto probablemente porque esa sucursal no vende por apps (no tiene sentido cobrar delivery en un cine), pero valdría la pena confirmarlo con Rafael antes de "corregirlo" mañana.

## Decisión sugerida (para la fase de mañana)
- Diferencia de menú/precio Cine Curto vs las demás → **DEJAR IGUAL** (hay razón de negocio: ubicación especial).
- Precios en $0 de combos delivery en Cine Curto → **REVISAR CONMIGO** antes de decidir si se homologan o se dejan así.
- Las 4 carretas normales ya están 100% alineadas entre sí en menú y precio — no hay nada que homologar ahí.
