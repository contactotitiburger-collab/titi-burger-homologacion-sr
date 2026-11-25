# Lector 3 (Ventas y cortes) + Verificador — 24-nov-2026

## Qué se revisó
Tabla `cheques` (tickets) de las 5 sucursales — total y conteo de tickets pagados, no cancelados, del 23-nov-2026 — comparado contra el reporte de ventas que ya se mandó esa madrugada (`ventas_2026-11-23.json`, fuente: portal SR Admin en la nube).

## Resultado de la verificación

| Sucursal | Tickets reporte | Tickets SQL | Total reporte | Total SQL | Veredicto |
|---|---|---|---|---|---|
| Montejano | 47 | 49 | $16,162 | $14,681 | **NO VERIFICADO** |
| Hacienda del Río | 13 | 13 | $4,977 | $4,977 | VERIFICADO |
| San Marcos | 15 | 12 | $4,639 | $2,894 | **NO VERIFICADO** |
| Villas del Rey | 13 | 13 | $4,423 | $4,423 | VERIFICADO |
| Cine Curto | 0 | 0 | $0 | $0 | VERIFICADO |

## Por qué NO VERIFICADO en Montejano y San Marcos
Descarté lo obvio: no es un filtro de `cancelado`/`pagado` mal puesto (revisé desglosado por esas dos columnas y el número no cambia). La diferencia es real entre lo que el portal en la nube reporta y lo que dice la base SQL local para ese mismo día. Posibles causas (sin confirmar, no quise forzar más consultas hoy para no gastar de más):
- Desfase de reloj/zona horaria del servidor local vs. la nube (ya hay precedente de esto documentado en `reporte-ventas-dos-fuentes-nube-vs-sql`).
- La nube puede estar agregando datos que la base local de esa sucursal no tiene sincronizados todavía.

**Esto queda marcado como hallazgo para revisar contigo** — no es parte de la homologación de catálogo/precios, pero si la nube y el SQL local no cuadran en 2 de 5 sucursales, es información valiosa para el proyecto completo (y para confiar o no en los reportes de ventas que se mandan cada noche).
