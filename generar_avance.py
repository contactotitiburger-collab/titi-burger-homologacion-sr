#!/usr/bin/env python3
"""Genera avance/index.html a partir de entregables.json + registro_actividad.csv.
Correr cada vez que algo cambie (o por cron mas adelante). Sin dependencias externas."""
import csv, json, sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render_comun import pct, parse_min, render_timeline, render_meter, TIMELINE_CSS, METER_CSS

COLOR_LECTOR = "#3987e5"  # azul — paleta categorica validada (slot 1, dark)
COLOR_EDITOR = "#d95926"  # naranja — paleta categorica validada (slot 6, dark)
# Validado: node scripts/validate_palette.js "#3987e5,#d95926" --mode dark --surface "#1a1d24"
# -> ALL CHECKS PASS (CVD 26.8, normal-vision 31.8). Blue+violeta se descarto: ΔE 1.9/9.8, FALLA.

BASE = Path(__file__).resolve().parent
OUT = BASE / "avance"
OUT.mkdir(exist_ok=True)
NARRATIVAS = BASE / "narrativas"

entregables = json.loads((BASE / "entregables.json").read_text())

pct_lector = pct(entregables["lector"])
pct_editor = pct(entregables["editor"])

filas = list(csv.DictReader((BASE / "registro_actividad.csv").open()))
hoy = datetime.now().strftime("%Y-%m-%d")
filas_hoy = [f for f in filas if f["fecha"] == hoy]

minutos_hoy = sum(parse_min(f["duracion"]) for f in filas_hoy)
horas_hoy = round(minutos_hoy / 60, 1)
minutos_total = sum(parse_min(f["duracion"]) for f in filas)
horas_total = round(minutos_total / 60, 1)

def filas_html(lista):
    out = []
    for e in lista:
        chk = "✅" if e["hecho"] else "⬜"
        out.append(f"<li>{chk} {e['nombre']}</li>")
    return "\n".join(out)

def actividad_html():
    out = []
    for f in filas_hoy:
        out.append(f"<tr><td>{f['hora_inicio']}</td><td>{f['hora_fin']}</td><td>{f['duracion']}</td>"
                    f"<td>{f['tarea']}</td><td>{f['resultado']}</td></tr>")
    return "\n".join(out)

timeline_path = NARRATIVAS / f"{hoy}_timeline.json"
if timeline_path.exists():
    seccion_hoy_titulo = "Cómo se hizo hoy"
    seccion_hoy_cuerpo = render_timeline(json.loads(timeline_path.read_text(encoding="utf-8")))
else:
    seccion_hoy_titulo = "Lo que se hizo hoy"
    seccion_hoy_cuerpo = f"""<table>
    <tr><td><b>Inicio</b></td><td><b>Fin</b></td><td><b>Duración</b></td><td><b>Tarea</b></td><td><b>Resultado</b></td></tr>
    {actividad_html()}
  </table>"""

html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Homologación Soft Restaurant — Titi Burger</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0f1115; color:#e8e8e8; margin:0; padding:2rem; }}
.wrap {{ max-width: 880px; margin: 0 auto; }}
h1 {{ font-size: 1.6rem; text-align:center; letter-spacing:.02em; margin-bottom:2rem; }}
.card {{ background:#1a1d24; border-radius:14px; padding:1.2rem 1.5rem; margin-bottom:1.4rem; }}
.card h2 {{ text-align:center; margin-top:0; }}
.lista-entregables {{ max-width:360px; margin:1rem auto 0; text-align:left; }}
{METER_CSS}
.stats {{ display:flex; gap:2rem; margin-bottom:1rem; }}
.stat b {{ font-size:1.4rem; display:block; }}
ul {{ padding-left: 1.2rem; }}
table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
td {{ padding:.35rem .5rem; border-bottom:1px solid #2a2e37; vertical-align:top; }}
a.office {{ display:inline-block; margin-top:.5rem; color:#7fd4ff; }}
footer {{ text-align:center; opacity:.5; font-size:.75rem; margin-top:2rem; }}
{TIMELINE_CSS}
</style></head>
<body><div class="wrap">
<h1>HOMOLOGACIÓN DE SOFT RESTAURANT — TITI BURGER</h1>

<div class="card">
  <h2>Avance del proyecto</h2>
  <div class="meters">
    {render_meter("Creación del Tito Lector", pct_lector, COLOR_LECTOR)}
    {render_meter("Creación del Tito Editor", pct_editor, COLOR_EDITOR)}
  </div>
</div>

<div class="card">
  <h3>Entregables — Tito Lector</h3>
  <ul class="lista-entregables">{filas_html(entregables['lector'])}</ul>
  <h3>Entregables — Tito Editor</h3>
  <ul class="lista-entregables">{filas_html(entregables['editor'])}</ul>
</div>

<div class="card">
  <div class="stats">
    <div class="stat">Horas hoy<b>{horas_hoy} h</b></div>
    <div class="stat">Horas totales del proyecto<b>{horas_total} h</b></div>
  </div>
  <h3>{seccion_hoy_titulo}</h3>
  {seccion_hoy_cuerpo}
</div>

<div class="card">
  <h3>Lo que sigue</h3>
  <ul>
    <li>Conectar la compu de Félix (base de referencia) y Montecarlo.</li>
    <li>Comparar cada sucursal contra la base de Félix.</li>
    <li>Análisis de brechas con prioridad y decisión sugerida, para tu aprobación.</li>
    <li>Crear al Tito Editor una vez aprobado el plan.</li>
  </ul>
  <a class="office" href="http://100.64.29.43:8101" target="_blank">→ Entrar a claude-office (piso de agentes)</a><br>
  <a class="office" href="reportes/index.html">→ Historial de reportes diarios</a><br>
  <a class="office" href="Analisis_Incongruencias_Tito_Lector.pdf" target="_blank">→ PDF: Análisis de incongruencias encontradas</a>
</div>

<footer>Generado automáticamente — {datetime.now():%Y-%m-%d %H:%M}</footer>
</div></body></html>"""

(OUT / "index.html").write_text(html, encoding="utf-8")
print("avance/index.html generado —", pct_lector, "% lector,", pct_editor, "% editor,", horas_hoy, "h hoy")
