#!/usr/bin/env python3
"""MERMA VISUAL POR CARRETA — Titi Burger.

Tabla de un vistazo: insumos clave (carne, queso, pan, tocino, pollo, papa) contra
cada carreta. Celda en ROJO con la cantidad si hubo merma; 0 apagado si no hubo.
Pestañas por mes (junio, julio, agosto + Todo). Solo MERMA REAL (excluye ajustes
de captura tipo "ERROR BUBU"). En piezas, sin dinero.

Fuente: movsinv (ETA al almacén de mermas + SPM/SPD), motivo desde traspasosalmacen.
Escribe merma_carretas.html en la carpeta del link público. Colgar de refresh.sh.
"""
import pymssql, socket, datetime
from collections import defaultdict
from pathlib import Path

BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
OUT  = BASE / "merma_carretas.html"
DESDE = "2026-06-01"
# carretas que registran merma. (nombre, host, almacén destino de merma, dedicado)
#   dedicado=True  -> el almacén es SOLO de mermas (cuenta todo, salvo ajustes)
#   dedicado=False -> almacén compartido (ej. cocina); cuenta SOLO traspasos con nota de merma
SUC = [
    ("Hacienda del Río", "100.80.102.110", "1",  True),
    ("Cine Curto",       "100.94.218.56",  "10", True),
    ("Villas del Rey",   "100.66.22.9",    "1",  False),
]
SIN_MERMA = ["San Marcos", "Montecarlo", "Montejano"]
# notas que NO son merma (ajustes de captura, transferencias, facturas)
EXC_NOTA = ("ERROR", "AJUSTE", "TRANSFER", "TRANFER", "TRAPAS", "TRASPAS", "FAC")
U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"

# Sucursales que se van sumando solas (ej. cuando prende San Marcos). Ver sanmarcos_watch.py
import json as _json
_EXTRA = BASE / "merma_suc_extra.json"
if _EXTRA.exists():
    try:
        for e in _json.loads(_EXTRA.read_text()):
            if e["nombre"] not in [s[0] for s in SUC]:
                SUC.append((e["nombre"], e["host"], e["alm"], e["dedicado"]))
            if e["nombre"] in SIN_MERMA:
                SIN_MERMA.remove(e["nombre"])
    except Exception as _e:
        print("extra config error:", _e)

# Insumos clave y las palabras con que se detectan (agrupa variantes)
CATS = [
    ("Carne",  "🥩", ["carne", "slider", "bp"]),
    ("Queso",  "🧀", ["queso"]),
    ("Pan",    "🍞", ["pan"]),
    ("Tocino", "🥓", ["tocino"]),
    ("Pollo",  "🍗", ["pollo"]),
    ("Papa",   "🍟", ["papa"]),
]
MES = {6:"Junio",7:"Julio",8:"Agosto"}
MESES = [6, 7, 8]

def cat_de(desc):
    d = desc.lower()
    for nombre, _, kws in CATS:
        if any(k in d for k in kws):
            return nombre
    return None

def puerto(h):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(6)
    try:
        s.sendto(b"\x02", (h, 1434)); d, _ = s.recvfrom(65535)
        p = d[3:].decode("ascii", "replace").split(";")
        for i, x in enumerate(p):
            if x == "tcp": return int(p[i + 1])
    finally:
        s.close()
    return None

def jalar(host, almmerma, dedicado):
    pt = puerto(host)
    if not pt: return None
    c = pymssql.connect(server=host, port=pt, user=U, password=P, database=DB,
                        tds_version=TDS, timeout=30, login_timeout=15)
    cur = c.cursor()
    cur.execute("""SELECT m.fecha, i.descripcion, m.cantidad, t.nota
                   FROM movsinv m JOIN insumos i ON i.idinsumo = m.idinsumo
                   LEFT JOIN traspasosalmacen t ON t.folio = m.traspaso
                   WHERE ((m.idconcepto='ETA' AND m.idalmacen=%s) OR m.idconcepto IN ('SPM','SPD'))
                     AND m.fecha >= %s""", (almmerma, DESDE))
    # agg[mes][cat] = piezas de merma real
    agg = defaultdict(lambda: defaultdict(float))
    for fe, desc, cant, nota in cur.fetchall():
        up = (nota or "").strip().upper()
        if any(x in up for x in EXC_NOTA):     # ajuste/transferencia, NO merma
            continue
        if not dedicado and up == "":          # almacén compartido: sin nota = no cuenta
            continue
        cat = cat_de(desc)
        if not cat: continue
        agg[fe.month][cat] += abs(float(cant or 0))
    c.close()
    return agg

datos = {}
for nombre, host, alm, dedicado in SUC:
    try:
        datos[nombre] = jalar(host, alm, dedicado)
        print(f"{nombre:18s} {'OFFLINE' if datos[nombre] is None else 'OK'}")
    except Exception as e:
        datos[nombre] = None; print(f"{nombre:18s} ERROR {e}")

carretas = [n for n, _, _, _ in SUC]

def celda(v):
    if v is None:
        return '<td class="c nd">n/d</td>'
    if v <= 0:
        return '<td class="c cero">0</td>'
    return f'<td class="c hay">{v:g}</td>'

def tabla(meses_sel, tid, activo):
    # suma de los meses seleccionados
    filas = []
    tot_por_carreta = {n: 0.0 for n in carretas}
    for nombre_cat, emoji, _ in CATS:
        celdas = []
        for car in carretas:
            agg = datos.get(car)
            if agg is None:
                celdas.append(celda(None)); continue
            v = sum(agg[m][nombre_cat] for m in meses_sel)
            tot_por_carreta[car] += v
            celdas.append(celda(v))
        filas.append(f"""        <tr><td class="ins">{emoji} {nombre_cat}</td>{''.join(celdas)}</tr>""")
    totcels = "".join(
        (f'<td class="c tot">{tot_por_carreta[n]:g}</td>' if datos.get(n) is not None else '<td class="c nd">n/d</td>')
        for n in carretas)
    ths = "".join(f"<th>{n}</th>" for n in carretas)
    return f"""    <div class="panel {'on' if activo else ''}" id="{tid}">
      <table class="matriz">
        <thead><tr><th class="e">Insumo</th>{ths}</tr></thead>
        <tbody>
{chr(10).join(filas)}
          <tr class="totrow"><td class="ins">TOTAL</td>{totcels}</tr>
        </tbody>
      </table>
    </div>"""

# pestañas: Todo + cada mes con datos
tabs_def = [("todo", "Jun–Ago", MESES)] + [(f"m{m}", MES[m], [m]) for m in MESES]
tabs_btns = "".join(
    f'<button class="tab {"active" if i==0 else ""}" data-go="{tid}">{lbl}</button>'
    for i, (tid, lbl, _) in enumerate(tabs_def))
paneles = "\n".join(tabla(meses, tid, i == 0) for i, (tid, _, meses) in enumerate(tabs_def))
now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
nota_sin = ", ".join(SIN_MERMA)

HTML = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Merma por carreta · Titi Burger</title>
<style>
:root{{--bg:#0f1115;--card:#171a21;--line:#262b36;--txt:#e8eaed;--mut:#9aa2b1;
  --accent:#ff7a1a;--ok:#2ecc71;--warn:#ffb020;--bad:#ff4d4d;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;font-size:15px}}
header{{padding:16px 16px 4px}}
.title{{display:flex;align-items:center;gap:10px}} .title h1{{font-size:21px;margin:0}} .emoji{{font-size:24px}}
.sub{{color:var(--mut);font-size:13px;margin-top:4px;line-height:1.4}}
.tabs{{display:flex;gap:8px;padding:12px 16px 6px;flex-wrap:wrap}}
.tab{{background:var(--card);border:1px solid var(--line);color:var(--txt);padding:8px 15px;
  border-radius:999px;font-size:14px;font-weight:700;cursor:pointer}}
.tab.active{{background:var(--accent);border-color:var(--accent);color:#111}}
.panel{{display:none;padding:6px 12px 8px}} .panel.on{{display:block}}
.wrap{{overflow-x:auto}}
table.matriz{{width:100%;border-collapse:separate;border-spacing:6px;min-width:340px}}
.matriz th{{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px;padding:6px 4px;text-align:center}}
.matriz th.e{{text-align:left}}
.matriz td.ins{{font-weight:800;font-size:15px;white-space:nowrap;padding-right:8px}}
td.c{{text-align:center;font-weight:800;font-size:22px;border-radius:12px;padding:16px 8px;min-width:78px}}
td.c.cero{{background:#161a20;color:#3d4453;border:1px solid var(--line)}}
td.c.hay{{background:var(--bad);color:#fff;box-shadow:0 0 0 1px rgba(255,77,77,.4)}}
td.c.nd{{background:#12151b;color:#3d4453;font-size:13px;font-weight:600}}
td.c.tot{{background:rgba(255,122,26,.15);color:var(--accent)}}
tr.totrow td.ins{{color:var(--accent)}}
.leyenda{{padding:2px 16px 0;color:var(--mut);font-size:12px;display:flex;gap:14px;flex-wrap:wrap;align-items:center}}
.dot{{display:inline-block;width:12px;height:12px;border-radius:4px;vertical-align:middle;margin-right:5px}}
.dot.r{{background:var(--bad)}} .dot.g{{background:#161a20;border:1px solid var(--line)}}
.pie{{padding:14px 16px;color:var(--mut);font-size:12px;line-height:1.5}}
footer{{padding:10px 16px 24px;color:var(--mut);font-size:12px;text-align:center;line-height:1.5}}
</style></head><body>
<header>
  <div class="title"><span class="emoji">🍔</span><h1>Merma por carreta</h1></div>
  <div class="sub">Titi Burger · piezas mermadas de los insumos clave · consultado {now}</div>
</header>
<div class="tabs">{tabs_btns}</div>
<div class="leyenda"><span><span class="dot r"></span>hay merma</span><span><span class="dot g"></span>sin merma (0)</span></div>
<div class="wrap">
{paneles}
</div>
<div class="pie">
  Solo <b>merma real</b> (quité los ajustes de captura tipo "ERROR BUBU"). En piezas.<br>
  <b>{nota_sin}</b> no registran merma en el sistema todavía (por eso no salen aquí).
</div>
<footer>Generado por Tito 🍔 · Fuente: movimientos de merma de Soft Restaurant.</footer>
<script>
document.querySelector('.tabs').addEventListener('click',e=>{{
  const b=e.target.closest('.tab'); if(!b)return;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));
  b.classList.add('active');
  document.getElementById(b.dataset.go).classList.add('on');
}});
</script>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
for n in carretas:
    if datos.get(n) is not None:
        tot = sum(datos[n][m][c] for m in MESES for c,_,_ in [(x[0],0,0) for x in CATS])
        print(f"   {n}: {tot:g} pz de insumos clave (jun-ago)")
