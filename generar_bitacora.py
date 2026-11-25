#!/usr/bin/env python3
"""Genera la bitacora de trabajo (estilo 'Keep a Changelog'): solo objetivos/hitos reales,
nunca cada tarea chica. Se actualiza a mano agregando entradas a bitacora.json -- no se
autogenera de registro_actividad.csv a proposito (si un dia no hubo cambio real, no entra)."""
import json, sys
from pathlib import Path
from datetime import date

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
TOKEN = (BASE / ".token_avance").read_text().strip()
OUT = BASE / "avance" / TOKEN

MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto",
          "septiembre","octubre","noviembre","diciembre"]

def fmt_fecha_es(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month-1]}"

TIPO_LABEL = {"agregado": "Agregado", "cambiado": "Cambiado", "arreglado": "Arreglado", "seguridad": "Seguridad"}
TIPO_COLOR = {"agregado": "#22C55E", "cambiado": "#1E90F0", "arreglado": "#F5B83D", "seguridad": "#7C4DFF"}

entradas = json.loads((BASE / "bitacora.json").read_text(encoding="utf-8"))
entradas = sorted(entradas, key=lambda e: e["fecha"], reverse=True)

def render_entrada(e):
    filas = "".join(
        f'<div class="cambio"><span class="tag" style="background:{TIPO_COLOR[c["tipo"]]}">{TIPO_LABEL[c["tipo"]]}</span>'
        f'<span class="cambio-texto">{c["texto"]}</span></div>'
        for c in e["cambios"]
    )
    return f"""<div class="entrada">
      <div class="entrada-fecha">{fmt_fecha_es(e['fecha'])}</div>
      <h3>{e['titulo']}</h3>
      {filas}
    </div>"""

html = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bitácora — Titi Burger</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{ --bg:#EEF7FC; --bg-top:#D6EEFA; --card:#FFFFFF; --border:#E6EEF5; --ink:#12324A; --ink2:#5B7488; --blue:#1E90F0; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:"Poppins",system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }}
  .topbar {{ height:100px; background:linear-gradient(180deg,var(--bg-top),var(--bg)); }}
  .wrap {{ max-width:720px; margin:-70px auto 0; padding:0 16px 32px; }}
  @media (min-width:700px) {{ .wrap {{ padding:0 24px 40px; }} }}
  h1 {{ font-size:22px; font-weight:600; margin:0 0 4px; }}
  @media (min-width:700px) {{ h1 {{ font-size:28px; }} }}
  .sub {{ color:var(--ink2); font-size:14px; margin:0 0 20px; }}
  .entrada {{ background:var(--card); border:1px solid var(--border); border-radius:20px;
    box-shadow:0 4px 16px rgba(20,60,100,0.06); padding:20px; margin-bottom:16px; }}
  .entrada-fecha {{ font-size:13px; color:var(--ink2); margin-bottom:2px; }}
  .entrada h3 {{ font-size:17px; font-weight:600; margin:0 0 12px; }}
  .cambio {{ display:flex; align-items:flex-start; gap:10px; margin-bottom:8px; font-size:14px; }}
  .tag {{ color:#fff; font-size:11px; font-weight:600; padding:3px 9px; border-radius:999px; flex:0 0 auto; white-space:nowrap; }}
  .cambio-texto {{ padding-top:2px; }}
  footer {{ text-align:center; color:var(--ink2); font-size:13px; padding:8px 0 24px; }}
  a.volver {{ color:var(--blue); text-decoration:none; font-weight:600; font-size:14px; }}
</style></head>
<body>
<div class="topbar"></div>
<div class="wrap">
  <a class="volver" href="../index.html">← Página de avance</a>
  <h1 style="margin-top:14px;">Bitácora — Titi Burger</h1>
  <p class="sub">Solo lo que realmente cambió, no una tarea por tarea.</p>
  {''.join(render_entrada(e) for e in entradas)}
  <footer>Generado automáticamente por Tito</footer>
</div>
</body></html>"""

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "bitacora.html").write_text(html, encoding="utf-8")
print("bitacora.html generada,", len(entradas), "entradas")
