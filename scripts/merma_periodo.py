#!/usr/bin/env python3
"""MERMA POR PERIODO (bloques de 3 días) — Titi Burger.

Entras hoy y te muestra la merma del último bloque cerrado de 3 días:
  Lunes–Miércoles  /  Jueves–Sábado.
La merma del bloque = foto de existencia del almacén de mermas al CIERRE del bloque
menos la foto del día ANTES de que empezara (el cajón de mermas es acumulado, así que
la diferencia entre dos fotos = lo que se mermó en ese periodo). Sin conteo físico.

Fuente: merma_hist.json (snapshot diario que guarda merma_reporte.py).
Filtro: solo la merma MÁS IMPORTANTE (proteínas, pan, papa, y platillos clave).
Escribe merma_periodo.html en la carpeta del link público. Colgar de refresh.sh.
"""
import json, datetime
from pathlib import Path

BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
HIST = BASE / "merma_hist.json"
OUT  = BASE / "merma_periodo.html"

# Qué cuenta como "lo más importante" (proteína / pan / papa / platillos caros)
IMPORTANTE = ("carne", "pan", "papa", "tocino", "queso", "pollo",
              "boneless", "slider", "aros", "dedos", "nachos", "bp")
TOP_N = 10  # máximo de renglones por sucursal

DIAS = {0:"lunes",1:"martes",2:"miércoles",3:"jueves",4:"viernes",5:"sábado",6:"domingo"}
MES  = {1:"ene",2:"feb",3:"mar",4:"abr",5:"may",6:"jun",7:"jul",8:"ago",9:"sep",10:"oct",11:"nov",12:"dic"}
def fmt(d): return f"{d.day}/{MES[d.month]}"

hist = json.loads(HIST.read_text()) if HIST.exists() else {}
fechas = sorted(hist.keys())   # 'YYYY-MM-DD'
def parse(s): return datetime.date.fromisoformat(s)

hoy = datetime.date.today()

def bloques(ref_lunes):
    return [("Lunes a Miércoles", ref_lunes, ref_lunes + datetime.timedelta(days=2)),
            ("Jueves a Sábado",   ref_lunes + datetime.timedelta(days=3), ref_lunes + datetime.timedelta(days=5))]

# Último bloque cuyo día de cierre ya pasó (end < hoy)
lunes_est = hoy - datetime.timedelta(days=hoy.weekday())
candidatos = bloques(lunes_est - datetime.timedelta(days=7)) + bloques(lunes_est)
cerrados = [b for b in candidatos if b[2] < hoy]
bloque = cerrados[-1] if cerrados else bloques(lunes_est)[0]
label, ini, fin = bloque

# Foto base = último snapshot en/antes del día ANTES de que empiece el bloque.
# Foto cierre = último snapshot en/antes del fin del bloque.
def snap_hasta(d):
    cand = [f for f in fechas if parse(f) <= d]
    return cand[-1] if cand else None

base_key  = snap_hasta(ini - datetime.timedelta(days=1))
cierre_key = snap_hasta(fin)
# ¿bloque calculable? necesito dos fotos distintas y que la de cierre sea >= fin-ish
aprox = False
if base_key is None and fechas:
    # arranqué a media semana: uso la foto más vieja que tengo como base (aprox)
    base_key = fechas[0]; aprox = True
calculable = bool(base_key and cierre_key and base_key != cierre_key)

# Cuándo estará listo el primer bloque real
def primer_bloque_listo():
    if not fechas: return None
    primera = parse(fechas[0])
    # el primer bloque cuyo INICIO sea >= primera_foto+1 (para tener base) ...
    for wk in range(0, 4):
        for lab, i, f in bloques(lunes_est + datetime.timedelta(days=7*wk)):
            if i - datetime.timedelta(days=1) >= primera:  # tengo base y el bloque es futuro-cerrable
                return (lab, i, f, f + datetime.timedelta(days=1))
    return None

def es_importante(desc):
    d = desc.lower()
    return any(k in d for k in IMPORTANTE)

def merma_periodo():
    """Devuelve dict suc -> lista de (desc, delta) de lo importante, delta>0."""
    if not calculable: return {}
    base = hist.get(base_key, {}); cierre = hist.get(cierre_key, {})
    out = {}
    sucs = set(base) | set(cierre)
    for suc in sucs:
        b = base.get(suc, {}); c = cierre.get(suc, {})
        rows = []
        for desc in set(b) | set(c):
            if not es_importante(desc): continue
            delta = round(c.get(desc, 0) - b.get(desc, 0), 2)
            if delta > 0:   # se mermó más en el periodo
                rows.append((desc, delta))
        rows.sort(key=lambda x: -x[1])
        if rows: out[suc] = rows[:TOP_N]
    return out

data = merma_periodo()

# --- HTML ---
def card(suc, rows):
    filas = "\n".join(f"""      <tr><td class="ins">{d}</td><td class="cant">{v:g}</td></tr>""" for d, v in rows)
    tot = sum(v for _, v in rows)
    return f"""    <div class="suc"><div class="suc-head"><h3>{suc}</h3>
      <span class="tag">{len(rows)} insumos · {tot:g} pzas</span></div>
      <table><thead><tr><th>Insumo</th><th>Merma en el periodo</th></tr></thead>
      <tbody>
{filas}
      </tbody></table></div>"""

listo = primer_bloque_listo()
if calculable and data:
    cuerpo = "\n".join(card(s, r) for s, r in sorted(data.items(), key=lambda kv: -sum(v for _, v in kv[1])))
    estado_html = ""
    if aprox:
        estado_html = '<div class="aviso warn">⚠️ Base aproximada: arranqué a media semana, así que este primer bloque puede quedar un poco corto. Los siguientes ya salen exactos.</div>'
else:
    cuerpo = ""
    listo_txt = ""
    if listo:
        lab, i, f, ready = listo
        listo_txt = f"El primer bloque real será <b>{lab} ({fmt(i)}–{fmt(f)})</b>, listo el <b>{DIAS[ready.weekday()]} {fmt(ready)}</b>."
    estado_html = f"""<div class="espera">
      <div class="ico">📸</div>
      <h2>Todavía estoy juntando las fotos</h2>
      <p>Para calcular la merma de <b>{label} ({fmt(ini)}–{fmt(fin)})</b> necesito la foto del
      {DIAS[(ini-datetime.timedelta(days=1)).weekday()]} y la del {DIAS[fin.weekday()]}, y apenas
      empecé a guardarlas hoy ({DIAS[hoy.weekday()]} {fmt(hoy)}).</p>
      <p>{listo_txt}</p>
      <p class="chico">De aquí en adelante se llena solo. No tienes que hacer nada.</p>
    </div>"""

HTML = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Merma por periodo · Titi Burger</title>
<style>
:root{{--bg:#0f1115;--card:#171a21;--line:#262b36;--txt:#e8eaed;--mut:#9aa2b1;
  --accent:#ff7a1a;--ok:#2ecc71;--warn:#ffb020;--bad:#ff4d4d;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;font-size:15px}}
header{{padding:16px}}
.title{{display:flex;align-items:center;gap:10px}} .title h1{{font-size:21px;margin:0}} .emoji{{font-size:24px}}
.hoy{{color:var(--mut);font-size:13px;margin-top:4px}}
.periodo{{margin:6px 16px 0;background:linear-gradient(135deg,#2a1c0e,#1a1206);
  border:1px solid #4a3418;border-radius:14px;padding:14px 16px}}
.periodo .lbl{{color:var(--accent);font-size:12px;text-transform:uppercase;letter-spacing:.4px;font-weight:800}}
.periodo .rng{{font-size:22px;font-weight:800;margin-top:3px}}
.aviso{{padding:10px 12px;border-radius:10px;font-size:12.5px;margin:12px 16px 0;line-height:1.45}}
.aviso.warn{{background:rgba(255,176,32,.1);border:1px solid #4a3418;color:#ffcf9e}}
.suc{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:14px 16px;overflow:hidden}}
.suc-head{{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid var(--line)}}
.suc-head h3{{margin:0;font-size:17px}}
.tag{{font-size:12.5px;font-weight:800;border-radius:999px;padding:3px 11px;background:rgba(255,122,26,.16);color:var(--accent)}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line)}}
th{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px}}
th:last-child,td.cant{{text-align:right}}
td.ins{{font-weight:600}}
td.cant{{font-variant-numeric:tabular-nums;font-weight:800;color:#ffd9b0}}
.espera{{margin:24px 16px;background:var(--card);border:1px dashed var(--line);border-radius:16px;padding:26px 20px;text-align:center}}
.espera .ico{{font-size:40px}}
.espera h2{{margin:10px 0 6px;font-size:19px}}
.espera p{{color:var(--mut);font-size:14px;line-height:1.5;max-width:460px;margin:6px auto}}
.espera .chico{{font-size:12.5px;opacity:.8}}
footer{{padding:22px 16px;color:var(--mut);font-size:12px;text-align:center;line-height:1.5}}
</style></head><body>
<header>
  <div class="title"><span class="emoji">🍔</span><h1>Merma por periodo</h1></div>
  <div class="hoy">Titi Burger · hoy es {DIAS[hoy.weekday()]} {fmt(hoy)}</div>
</header>
<div class="periodo">
  <div class="lbl">Merma del bloque</div>
  <div class="rng">{label} · {fmt(ini)} – {fmt(fin)}</div>
</div>
{estado_html}
{cuerpo}
<footer>
  Generado por Tito 🍔 · Solo la merma más importante (proteínas, pan, papa y platillos).<br>
  Se calcula solo restando la foto diaria del Almacén de Mermas de Soft Restaurant.
</footer>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
print(f"   bloque objetivo: {label} {fmt(ini)}-{fmt(fin)} | calculable={calculable} | fotos={len(fechas)}")
