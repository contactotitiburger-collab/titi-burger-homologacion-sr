# Lector 4 — Configuración (24-nov-2026)

## Qué se revisó
Tablas `usuarios` y `almacen` en las 5 sucursales (impuestos quedó pendiente — ver abajo).

## Usuarios — muy desparejo entre sucursales

| Sucursal | Usuarios | Notas |
|---|---|---|
| Montejano | 8 | Incluye un usuario "MONTECARLO" (raro — Montecarlo es otra sucursal, no debería tener login aquí) |
| Hacienda del Río | 7 | — |
| San Marcos | 5 | — |
| Villas del Rey | 4 | El más flaco: solo ADMIN, BACKUP, un cajero genérico y LIZ |
| Cine Curto | 4 | Solo un "USUARIO 1" genérico para todos los cajeros |

Todas comparten el login `ADMIN` = **FELIX** (coincide con que su base es la referencia oficial del proyecto) y `LIZ` (con pequeñas variaciones de nombre completo: "LIZ" vs "ELIZABETH CAMPOS" vs "ELIZABETH").

**Hallazgos para la fase de homologación:**
1. El usuario `MONTECARLO` dentro de la base de Montejano no tiene lógica clara — posible residuo de alguna prueba o mala captura. **REVISAR CONMIGO.**
2. Nomenclatura de cajeros es inconsistente: `CAJERO1` (sin espacio) en Montejano vs `CAJERO 1` (con espacio) en Hacienda del Río y San Marcos vs un solo `CAJERO` genérico en Villas y un `USUARIO 1` en Cine Curto. Esto es exactamente el tipo de cosa que la base de Félix como referencia debería resolver mañana.

## Almacenes
Ver hallazgo del almacén `'10'` (TRAPASO A OTRA SUCURSAL vs MERMAS en Cine Curto) en el reporte de inventario — es tanto un tema de inventario como de configuración.

## Pendiente (no se alcanzó hoy)
No revisé `impuestos`, `comandosimpresion` (impresoras) ni `areasrestaurant`/`mesas` a fondo — quedó priorizado usuarios y almacenes por ser lo más visible. Se completa cuando se compare contra la base de Félix mañana.
