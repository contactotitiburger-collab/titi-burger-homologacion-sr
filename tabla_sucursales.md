# Paso 1 — Descubrimiento de sucursales (24-nov-2026)

| Sucursal | Equipo Tailscale | En línea | SQL responde | Base | Notas |
|---|---|---|---|---|---|
| Montejano | tbfovi-servidor (100.68.233.59) | Sí | Sí | softrestaurant12 | Única en SR 12.0 (las demás en 11.0). Login `tito` SOLO LECTURA db_datareader. |
| Hacienda del Río | tbhrio-servidor (100.80.102.110) | Sí | Sí | softrestaurant11 | Login `tito` SOLO LECTURA db_datareader. |
| San Marcos | tbsm-servidor (100.101.205.89) | Sí | Sí | softrestaurant11 | Login `tito` SOLO LECTURA db_datareader. |
| Villas del Rey | tbvir-servidor (100.66.22.9) | Sí | Sí | softrestaurant11 | Login `tito` SOLO LECTURA db_datareader. |
| Cine Curto | tbcurt-servidor (100.94.218.56) | Sí | Sí | softrestaurant11 | Login `tito` SOLO LECTURA db_datareader. |
| Montecarlo | — no existe nodo en el tailnet | No | No | — | Falta conectar. Se conecta después. |
| Félix (referencia) | — no existe nodo en el tailnet | No | No | — | Se conecta MAÑANA — será la base de referencia. |

## Hallazgo clave de hoy
Ya existe un login SQL `tito` con permiso `db_datareader` (solo lectura) en las 5 sucursales conectadas — se creó entre agosto y septiembre y ya lo usan varios scripts en producción (mermas, formas de pago). **No hace falta crear nada nuevo para leer hoy**: el Paso 2 (acceso seguro de solo lectura) ya está resuelto de raíz para estas 5 — cero riesgo, cero escritura.

Puerto SQL Server en todas es DINÁMICO (instancia con nombre `NATIONALSOFT`) — se resuelve vía SQL Browser (UDP 1434) antes de cada conexión, no es el 1433 estándar.
