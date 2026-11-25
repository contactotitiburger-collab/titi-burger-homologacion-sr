#!/usr/bin/env python3
"""Genera un reporte diario (snapshot) para Felix y lo guarda en reportes/YYYY-MM-DD.html,
mas un indice reportes/index.html con el historial. Corre una vez al dia via systemd timer."""
import csv, json, markdown, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render_comun import pct, parse_min, render_timeline, TIMELINE_CSS

BASE = Path(__file__).resolve().parent
REPORTES = BASE / "avance" / "reportes"
REPORTES.mkdir(exist_ok=True)
NARRATIVAS = BASE / "narrativas"

entregables = json.loads((BASE / "entregables.json").read_text())

pct_lector = pct(entregables["lector"])
pct_editor = pct(entregables["editor"])

filas = list(csv.DictReader((BASE / "registro_actividad.csv").open()))
hoy = datetime.now().strftime("%Y-%m-%d")
filas_hoy = [f for f in filas if f["fecha"] == hoy]

minutos_hoy = sum(parse_min(f["duracion"]) for f in filas_hoy)
horas_hoy = round(minutos_hoy / 60, 1)

actividad_rows = "\n".join(
    f"<tr><td>{f['hora_inicio']}</td><td>{f['hora_fin']}</td><td>{f['duracion']}</td>"
    f"<td>{f['tarea']}</td><td>{f['resultado']}</td></tr>"
    for f in filas_hoy
) or "<tr><td colspan='5'>Sin actividad registrada hoy.</td></tr>"

# Orden de prioridad para el cuerpo del reporte de hoy:
# 1) linea de tiempo estructurada (parte N + minutos a la derecha) — formato pedido por Rafael
# 2) narrativa libre en markdown (plan -> como se hizo -> que hace cada pieza -> etc.)
# 3) tabla simple de actividad (si no se escribio nada especial hoy)
timeline_path = NARRATIVAS / f"{hoy}_timeline.json"
narrativa_path = NARRATIVAS / f"{hoy}.md"
if timeline_path.exists():
    pasos = json.loads(timeline_path.read_text(encoding="utf-8"))
    cuerpo = render_timeline(pasos)
elif narrativa_path.exists():
    cuerpo = markdown.markdown(narrativa_path.read_text(encoding="utf-8"), extensions=["tables"])
else:
    cuerpo = f"""<div class="card">
  <h3>Actividad de hoy</h3>
  <table>
    <tr><td><b>Inicio</b></td><td><b>Fin</b></td><td><b>Duración</b></td><td><b>Tarea</b></td><td><b>Resultado</b></td></tr>
    {actividad_rows}
  </table>
</div>"""

html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte {hoy} — Tito Lector</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0f1115; color:#e8e8e8; margin:0; padding:2rem; }}
.wrap {{ max-width: 860px; margin: 0 auto; }}
h1 {{ font-size: 1.3rem; }}
h2, h3 {{ color:#ffb347; }}
.card {{ background:#1a1d24; border-radius:14px; padding:1.2rem 1.5rem; margin-bottom:1.2rem; }}
table {{ width:100%; border-collapse:collapse; font-size:.85rem; margin:.6rem 0; }}
td, th {{ padding:.35rem .5rem; border-bottom:1px solid #2a2e37; vertical-align:top; text-align:left; }}
th {{ color:#ffb347; }}
a {{ color:#7fd4ff; }}
.pills {{ display:flex; gap:1.5rem; }}
.pills b {{ font-size:1.3rem; display:block; }}
code {{ background:#242832; padding:1px 5px; border-radius:4px; }}
{TIMELINE_CSS}
</style></head>
<body><div class="wrap">
<h1>Reporte diario — Homologación Soft Restaurant — {hoy}</h1>
<div class="card">
  <div class="pills">
    <div>Tito Lector<b>{pct_lector}%</b></div>
    <div>Tito Editor<b>{pct_editor}%</b></div>
    <div>Horas hoy<b>{horas_hoy} h</b></div>
  </div>
</div>
<div class="card">{cuerpo}</div>
<p><a href="index.html">← Historial de reportes</a> · <a href="../index.html">Página de avance</a></p>
</div></body></html>"""

(REPORTES / f"{hoy}.html").write_text(html, encoding="utf-8")

# Reconstruir el indice con todos los reportes guardados
dias = sorted((f.stem for f in REPORTES.glob("*.html") if f.stem != "index"), reverse=True)
filas_index = "\n".join(f'<li><a href="{d}.html">{d}</a></li>' for d in dias)
index_html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Historial de reportes — Tito Lector</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0f1115; color:#e8e8e8; margin:0; padding:2rem; }}
.wrap {{ max-width: 820px; margin: 0 auto; }}
li {{ margin-bottom:.4rem; font-size:1rem; }}
a {{ color:#7fd4ff; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
</style></head>
<body><div class="wrap">
<h1>Historial de reportes — Homologación Soft Restaurant</h1>
<ul>{filas_index}</ul>
<p><a href="../index.html">← Página de avance</a></p>
</div></body></html>"""
(REPORTES / "index.html").write_text(index_html, encoding="utf-8")
print(f"Reporte del {hoy} guardado. {len(dias)} reportes en el historial.")
