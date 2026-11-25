# Reporte — Cómo se construyó el Tito Lector

## 1. El plan que se armó
Rafael trajo un plan de trabajo ("PLAN DE TRABAJO – REGULARIZACIÓN DE BASE DE DATOS") con dos días:
**Día 1 — Tito Lector** (solo lectura, comparar sucursales) y **Día 2 — Tito Editor** (editar, con respaldo,
sucursal por sucursal, solo con autorización). Hoy tocaba el Día 1: crear al Tito Lector, un equipo de
**5 especialistas de solo lectura** (4 lectores + 1 verificador), mandarlos a leer cada sucursal conectada,
comparar contra la referencia oficial (la base de Félix — todavía no disponible) y entregar un reporte
que sirva de mapa para cuándo empiece el Editor.

## 2. Cómo se hizo (con tiempos reales)
| Paso | Qué se hizo | Tiempo |
|---|---|---|
| Descubrimiento | Revisar por Tailscale qué sucursales responden (ping + puerto SQL) | 11 min |
| Acceso de solo lectura | Probar 2 candidatos de MCP para SQL Server; el primero (C#/.NET) no conectó con los SQL Server 2014 viejos de las sucursales — se descartó y se eligió el segundo (Python + pymssql), que sí conectó y ya tenía su propio filtro que bloquea todo lo que no sea `SELECT` | 2 + 3 + 2 = 7 min |
| Los 4 lectores + verificador | Correr las consultas de menú/precios, inventario/recetas, ventas/cortes y configuración en las 5 sucursales, y verificar un número real (ventas de un día) contra lo ya reportado | 4 × 16 min = 64 min |
| Mapa de la base | Documentar qué tabla guarda qué y cómo se relacionan | 5 min |
| Desarrollo real (scripts, debugging, página de avance, claude-office) | Trabajo de programación que no quedó capturado tarea por tarea | 180 min (3 h) |
| PDF de incongruencias | Armar el documento con las 5 incongruencias encontradas | 5 min |
| **Total del proyecto hasta ahora** | | **4.6 horas** |

## 3. Qué hace cada agente
- **Lector de Menú y Precios** — compara productos, grupos y precios entre sucursales.
- **Lector de Inventario y Recetas** — compara insumos y la configuración de almacenes.
- **Lector de Ventas y Cortes** — saca el total de ventas real de la base SQL de cada sucursal.
- **Lector de Configuración** — compara usuarios del sistema y nomenclatura.
- **Verificador** — no inventa nada nuevo: toma lo que reportaron los otros 4 y lo vuelve a consultar en la base para confirmar que cuadra con algo concreto (en este caso, el total de ventas de un día contra el reporte que ya se mandó esa noche).

## 4. ¿Se retroalimentan entre ellos?
Hoy, por cuidar tokens (no tenemos cuenta Max), **yo hice el trabajo de los 4 lectores directamente**,
uno por uno, en vez de lanzar 4 sub-agentes corriendo en paralelo — cada "lector" es una tanda de consultas
SQL de solo lectura enfocada en su área, no un proceso separado hablando con los otros.
El que sí tiene una retroalimentación real es el **Verificador**: toma los números que salieron del lector
de Ventas y los cruza contra el reporte que ya se había mandado, para decir si cuadra o no.
Si más adelante se necesita que corran en paralelo de verdad (por volumen o velocidad), se puede armar
como 4 sub-agentes reales — hoy no hizo falta.

## 5. Cómo funciona, por dentro (breve)
Cada sucursal tiene su SQL Server con un login `tito` que ya existía, con permiso de **solo lectura**
(`db_datareader` — no puede escribir nada). El puerto de conexión es dinámico (cambia si el servidor se
reinicia), así que antes de cada consulta se le pregunta al "SQL Browser" de esa sucursal cuál es el puerto
actual. Con eso, cada lector manda consultas `SELECT` normales — nunca `INSERT`/`UPDATE`/`DELETE` — y además
el programa que usamos (el MCP) tiene su propio candado que bloquea cualquier otra cosa aunque alguien
se equivocara al escribir una consulta.

## 6. Todo lo demás que se hizo
- Se borró el crontab completo (48 líneas, respaldadas) — nada se manda automático a nadie por ahora.
- Se construyó la página de avance (2 barras de progreso que se calculan solas, horas, actividad del día).
- Se instaló claude-office (3 pisos: Lectores, Finanzas, Editores) — Python 3.13 instalado sin sudo, vía `uv`.
- Se programó un reporte diario automático (11:50pm) que se guarda en un historial.
- Se armó el PDF con las 5 incongruencias encontradas.
