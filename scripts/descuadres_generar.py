#!/usr/bin/env python3
"""Reporte de DESCUADRES por carreta — Titi Burger (opción A).

Lo único que Soft Restaurant delata SOLO, sin conteo físico: cuando la existencia
de la carreta sale en NEGATIVO = salió producto sin registrarse = posible merma o
falta capturar una compra. Este reporte lista esos descuadres por sucursal, en rojo,
ordenado por el más grave. NO pide que nadie cuente.

Lee inv_data.json (mismo del tablero, se refresca cada 15 min).
Escribe descuadres.html en la carpeta que sirve el link público.
"""
import json, datetime
from pathlib import Path

BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
DATA = BASE / "inv_data.json"
OUT  = BASE / "descuadres.html"

data = json.loads(DATA.read_text())
gen_human = data.get("generated_human", "")

def estado(suc):
    if suc.get("stale"): return ("cache", f"última info {suc.get('last_human','')}", "🟡")
    if suc.get("live"):  return ("live", "en vivo", "🟢")
    return ("off", "sin conexión", "⚪")

# --- armar por sucursal: solo negativos, peor primero ---
sucs = []
tot_desc = 0
tot_pz = 0.0
sucs_afectadas = 0
for s in data["sucursales"]:
    est, est_txt, badge = estado(s)
    negs = sorted([it for it in s.get("items", []) if it["exist"] < 0],
                  key=lambda it: it["exist"])   # más negativo primero
    if negs:
        sucs_afectadas += 1
        tot_desc += len(negs)
        tot_pz += sum(abs(it["exist"]) for it in negs)
    sucs.append({"n": s["n"], "est": est, "est_txt": est_txt, "badge": badge,
                 "negs": negs, "conectada": bool(s.get("items"))})

# sucursales con más descuadres arriba
sucs.sort(key=lambda x: (-len(x["negs"]), x["est"] != "live"))

def card(s):
    n = s["n"]
    if not s["conectada"]:
        return f"""    <div class="suc off">
      <div class="suc-head"><h3>{n}</h3><span class="cnt cero">{s['badge']} sin conexión</span></div>
      <div class="vacio">Esta carreta no está conectada ahora (no puedo leerla). {'Cerrada por el incendio.' if n=='Montejano' else 'Compu apagada.'}</div>
    </div>"""
    if not s["negs"]:
        return f"""    <div class="suc ok">
      <div class="suc-head"><h3>{n}</h3><span class="cnt verde">✅ 0 descuadres</span></div>
      <div class="vacio">La carreta cuadra: ningún insumo en negativo. {s['badge']} {s['est_txt']}</div>
    </div>"""
    filas = []
    for it in s["negs"]:
        falta = abs(it["exist"])
        filas.append(f"""      <tr>
        <td class="ins">{it['desc'].title()}</td>
        <td class="fam">{it.get('fam','').title()}</td>
        <td class="sys">{it['exist']:g}</td>
        <td class="falta">faltan {falta:g}</td>
      </tr>""")
    nota = ""
    if s["est"] == "cache":
        nota = f'<div class="notacache">⚠️ Última lectura: {s["est_txt"]} (la compu está apagada hoy).</div>'
    return f"""    <div class="suc bad">
      <div class="suc-head"><h3>{n}</h3><span class="cnt rojo">🔴 {len(s['negs'])} descuadres</span></div>
      {nota}
      <table>
        <thead><tr><th>Insumo</th><th>Familia</th><th>Sistema</th><th>Descuadre</th></tr></thead>
        <tbody>
{chr(10).join(filas)}
        </tbody>
      </table>
    </div>"""

cards = "\n".join(card(s) for s in sucs)

HTML = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Descuadres por carreta · Titi Burger</title>
<style>
:root{{--bg:#0f1115;--card:#171a21;--line:#262b36;--txt:#e8eaed;--mut:#9aa2b1;
  --accent:#ff7a1a;--ok:#2ecc71;--warn:#ffb020;--bad:#ff4d4d;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;font-size:15px}}
header{{padding:16px}}
.title{{display:flex;align-items:center;gap:10px}}
.title h1{{font-size:21px;margin:0}}
.emoji{{font-size:24px}}
.sub{{color:var(--mut);font-size:13px;margin-top:4px;line-height:1.45}}
.resumen{{display:flex;gap:10px;flex-wrap:wrap;padding:0 16px}}
.rz{{flex:1;min-width:110px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}}
.rz .big{{font-size:26px;font-weight:800;line-height:1}}
.rz.bad .big{{color:var(--bad)}} .rz.warn .big{{color:var(--warn)}}
.rz .lbl{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px;margin-top:5px}}
.aviso{{background:#241a10;border:1px solid #4a3418;color:#ffcf9e;
  padding:10px 12px;border-radius:10px;font-size:12.5px;margin:12px 16px 0;line-height:1.45}}
.suc{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:14px 16px;overflow:hidden}}
.suc.bad{{border-color:var(--bad)}}
.suc.bad .suc-head{{background:rgba(255,77,77,.12)}}
.suc.ok .suc-head{{background:rgba(46,204,113,.08)}}
.suc-head{{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid var(--line)}}
.suc-head h3{{margin:0;font-size:17px}}
.cnt{{font-size:13px;font-weight:800;border-radius:999px;padding:3px 11px}}
.cnt.rojo{{background:var(--bad);color:#fff}}
.cnt.verde{{background:rgba(46,204,113,.18);color:var(--ok)}}
.cnt.cero{{background:#2a3140;color:var(--mut)}}
.vacio{{padding:12px 14px;color:var(--mut);font-size:13px}}
.notacache{{padding:8px 14px;color:#ffcf9e;font-size:12px;background:rgba(255,176,32,.06)}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line)}}
th{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px}}
td.ins{{font-weight:700}}
td.fam{{color:var(--mut);font-size:12px}}
td.sys{{text-align:right;font-variant-numeric:tabular-nums;color:#ff9a9a;font-weight:700}}
th:nth-child(3),th:nth-child(4){{text-align:right}}
td.falta{{text-align:right;font-weight:800;color:#fff;white-space:nowrap}}
td.falta{{color:var(--bad)}}
footer{{padding:22px 16px;color:var(--mut);font-size:12px;text-align:center;line-height:1.5}}
@media (max-width:520px){{ td.fam,th:nth-child(2){{display:none}} }}
</style>
</head>
<body>
<header>
  <div class="title"><span class="emoji">🍔</span><h1>Descuadres por carreta</h1></div>
  <div class="sub">Titi Burger · lectura de Soft Restaurant al <b>{gen_human}</b> · se actualiza solo cada 15 min</div>
</header>

<div class="resumen">
  <div class="rz bad"><div class="big">{tot_desc}</div><div class="lbl">Insumos descuadrados</div></div>
  <div class="rz bad"><div class="big">{sucs_afectadas}</div><div class="lbl">Carretas con bronca</div></div>
  <div class="rz warn"><div class="big">{tot_pz:g}</div><div class="lbl">Piezas sin cuadrar</div></div>
</div>

<div class="aviso">
  🔴 Un insumo en <b>negativo</b> = el sistema vendió/gastó más de lo que tenía cargado.
  Eso es <b>posible merma o fuga</b>, o que falta capturar una compra. Es lo único que Soft
  Restaurant delata solo, sin ir a contar. Donde veas rojo, ahí hay que revisar.
</div>

{cards}

<footer>
  Generado por Tito 🍔 · Fuente: existencia de carreta en Soft Restaurant.<br>
  Soft Restaurant no guarda merma con fecha; esto muestra el descuadre actual acumulado.
</footer>
</body>
</html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
print(f"   total descuadres={tot_desc}  carretas afectadas={sucs_afectadas}  piezas={tot_pz:g}")
for s in sucs:
    print(f"   {s['n']:18s} {len(s['negs'])} negativos  [{s['est']}]")
