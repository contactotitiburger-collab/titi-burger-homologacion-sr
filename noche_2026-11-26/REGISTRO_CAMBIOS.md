# Registro de cambios — noche 26→27 nov 2026

Regla de la noche: **cero escrituras en sucursales y en la base de Félix**. Todo lo de abajo es en el software propio (Z2).

| Hora (Z2) | Fase | Qué cambió | Dónde | Respaldo / cómo regresarlo |
|---|---|---|---|---|
| 23:25 | 1 | Verifiqué que el login `tito` es solo lectura en las 7 bases (writer 0, owner 0, UPDATE 0) | — | No cambia nada |
| 23:27 | 1 | Nuevo: `lib_lectura.py` (conexión solo SELECT), `extraer_todo.py`, `comparar_todo.py`, `generar_propuestas.py`, `verificar_hallazgos.py`, `ver_detalle*.py`, `explorar_esquema.py` | `tito-lector/noche_2026-11-26/` | Carpeta nueva; borrarla no afecta nada |
| 23:28 | 1 | Fotos de las 7 bases + `analisis_completo.json` + `propuestas.json` (1,530) + `FASE1_ANALISIS.md` | igual | Datos; no se suben a GitHub (.gitignore) |
| 23:34 | 2 | Nuevo: **Tito Editor** (`reglas.py`, `nucleo.py`, `conductores.py`, `editor.py`, `README.md`, 19 pruebas) + repo git propio | `workspace/tito-editor/` | Carpeta nueva, commit `765d784`. Escritura real APAGADA |
| 23:35 | 3 | Respaldo completo de tito-lector antes de tocar el plan | `~/.openclaw/backups/noche_2026-11-26/tito-lector_antes_fase3.tgz` | — |
| 23:35 | 3 | Commit de foto previa (cambios de la tarde que estaban sin guardar) | tito-lector git `7f53657` | `git checkout 7f53657 -- <archivo>` |
| 23:36 | 3 | Plan mejorado: `fases.json` (fase 3 con 9 pasos), `plan_fases.json`, `plan_contrato.json`, `objetivos.json`, frase del dueño en `generar_avance_v2.py`; página de avance regenerada (abre bien, 200) | tito-lector, commit `74b793b` | Cada archivo tiene `.bak_noche`; o `git revert 74b793b` |
| 23:37 | 3 | `.gitignore`: fuera de GitHub las fotos y el análisis (datos del negocio) | tito-lector | — |
| 23:40 | 4 | Reporte para Félix como documento privado ("Cómo vamos a dejar las sucursales iguales a la tuya") | claude.ai (privado, sin compartir) | Se edita o borra desde el documento |
| 23:45 | 5 | Investigación: Moltbook solo lectura (sin publicar) + 3 investigaciones en paralelo | `noche_2026-11-26/investigacion/` | — |
| 23:58 | 6 | Nuevo `salud_cajas.py` (solo lectura, sin mensajes): respaldo, ultimo ticket, reloj, tamano, cambios de catalogo | tito-lector `850ee68` | Archivo nuevo; borrarlo no afecta nada |
| 06:05 | 6 | Tito Editor: revisor SQL (sqlglot), huella de fila completa (`sellar`), ancla de bitacora, 7 pruebas nuevas (40 casos al azar). Prueba de mutacion: al romper 2 candados a proposito, las pruebas lo detectan | tito-editor `d1c5a15` | `git revert d1c5a15` |
| 06:07 | 6 | Lote de Villas sellado contra la sucursal REAL en solo lectura: 60/60 con huella, 0 saltados | tito-editor/lotes | — |
| 06:08 | 6 | `salud_cajas.py`: red Tailscale (en linea, dias para que venza la llave), estado de la base, version SQL | tito-lector `c169696` | `git revert c169696` |
| 06:09 | 4 | Reporte de Felix: nota de respaldos (Montejano y Villas sin respaldo registrado; Felix ultimo 25-ago) | documento privado | Se edita en el documento |
| 06:12 | 6 | Encontrados disparadores de SR en productos/productosdetalle/costos (las 7 bases). Regla nueva: esas tablas solo desde SR, nunca directo. 27 pruebas OK | tito-editor `d3e6db4` | `git revert d3e6db4` |
| 06:14 | 5 | `investigacion/FASE5_INVESTIGACION.md` | tito-lector | — |

**No se toco:** ninguna sucursal, la base de Felix, `health_check.py`, los avisos de WhatsApp, timers/crons, Tailscale. No se subio nada a GitHub (push pendiente de tu OK).
