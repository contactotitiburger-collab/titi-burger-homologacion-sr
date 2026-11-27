#!/usr/bin/env python3
"""TODAS LAS MERMAS por fecha — Titi Burger.

Soft Restaurant SÍ guarda las mermas con fecha: están en la tabla `movsinv`
(la tabla real de movimientos de inventario; `movtosalmacen` está vacía en esta
versión). La merma se registra como ENTRADA por traspaso (ETA) al almacén de mermas,
o como Salida Por Merma (SPM) / Salida Por Desperdicio (SPD).

Este reporte lista TODAS las mermas registradas, agrupadas por fecha, por sucursal,
con cantidad y valor en pesos. NO cuadra nada — es la lista tal cual de lo capturado.

Escribe merma_todas.html en la carpeta del link público.
"""
import pymssql, socket, datetime
from collections import defaultdict
from pathlib import Path

BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
OUT  = BASE / "merma_todas.html"
DESDE = "2026-06-01"   # rango a mostrar (últimos meses: jun, jul, ago)
# (nombre, host, almacén de mermas)
SUC = [("Hacienda del Río", "100.80.102.110", "1"), ("Cine Curto", "100.94.218.56", "10")]
U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"

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

MES = {1:"ene",2:"feb",3:"mar",4:"abr",5:"may",6:"jun",7:"jul",8:"ago",9:"sep",10:"oct",11:"nov",12:"dic"}
MESLARGO = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
DIA = {0:"lun",1:"mar",2:"mié",3:"jue",4:"vie",5:"sáb",6:"dom"}
def fday(d): return f"{DIA[d.weekday()]} {d.day}/{MES[d.month]}/{d.year}"

def jalar(host, almmerma):
    pt = puerto(host)
    if not pt: return None
    c = pymssql.connect(server=host, port=pt, user=U, password=P, database=DB,
                        tds_version=TDS, timeout=30, login_timeout=15)
    cur = c.cursor()
    cur.execute("""SELECT m.fecha, m.idconcepto, i.descripcion, i.unidad, m.cantidad, m.costo, t.nota
                   FROM movsinv m
                   JOIN insumos i ON i.idinsumo = m.idinsumo
                   LEFT JOIN traspasosalmacen t ON t.folio = m.traspaso
                   WHERE ((m.idconcepto='ETA' AND m.idalmacen=%s) OR m.idconcepto IN ('SPM','SPD'))
                     AND m.fecha >= %s
                   ORDER BY m.fecha DESC""", (almmerma, DESDE))
    filas = []
    for fe, con, d, u, cant, co, nota in cur.fetchall():
        nota = (nota or "").strip()
        up = nota.upper()
        # "ERROR" o "AJUSTE" en la nota = corrección de captura, NO merma real
        es_ajuste = ("ERROR" in up) or ("AJUSTE" in up)
        filas.append({"fecha": fe, "concepto": str(con).strip(), "desc": d.strip().title(),
                      "uni": (u or "").strip(), "cant": abs(float(cant or 0)),
                      "val": abs(float(cant or 0))*float(co or 0),
                      "motivo": nota, "es_ajuste": es_ajuste})
    c.close()
    return filas

datos = []
for nombre, host, alm in SUC:
    try:
        filas = jalar(host, alm)
        datos.append((nombre, filas))
        print(f"{nombre:18s} {'OFFLINE' if filas is None else str(len(filas))+' movimientos de merma'}")
    except Exception as e:
        datos.append((nombre, None)); print(f"{nombre:18s} ERROR {e}")

def card(nombre, filas):
    if filas is None:
        return f"""    <div class="suc off"><div class="suc-head"><h3>{nombre}</h3><span class="tag gris">sin conexión</span></div></div>"""
    if not filas:
        return f"""    <div class="suc off"><div class="suc-head"><h3>{nombre}</h3><span class="tag gris">sin mermas en el rango</span></div></div>"""
    reales  = [f for f in filas if not f["es_ajuste"]]
    ajustes = [f for f in filas if f["es_ajuste"]]
    total_real = sum(f["cant"] for f in reales)
    total_aj   = sum(f["cant"] for f in ajustes)

    def dias_html(mfilas):
        porfecha = defaultdict(list)
        for f in mfilas:
            porfecha[f["fecha"].date()].append(f)
        out = []
        for fe in sorted(porfecha, reverse=True):
            items = porfecha[fe]
            sub = sum(x["cant"] for x in items)
            motivos = sorted({x["motivo"] for x in items if x["motivo"]})
            mtag = f'<span class="motivo">{" · ".join(motivos)}</span>' if motivos else ""
            lis = "".join(
                f"""<tr><td class="ins">{x['desc']}</td><td class="cant">{x['cant']:g} {x['uni']}</td></tr>"""
                for x in sorted(items, key=lambda z: -z["cant"]))
            out.append(f"""        <div class="dia">
          <div class="dia-head"><span class="fe">{fday(fe)}{mtag}</span><span class="subd">{len(items)} insumos</span></div>
          <table><tbody>{lis}</tbody></table>
        </div>""")
        return "\n".join(out)

    # meses de la MERMA REAL
    pormes = defaultdict(list)
    for f in reales:
        pormes[(f["fecha"].year, f["fecha"].month)].append(f)
    chips = "".join(
        f"""<div class="chip"><div class="cm">{MES[m]}</div><div class="cv">{sum(x['cant'] for x in pormes[(y,m)]):g}</div>
        <div class="cp">piezas</div></div>"""
        for (y, m) in sorted(pormes, reverse=True)) or '<div class="chip"><div class="cm">—</div><div class="cv">0</div><div class="cp">piezas</div></div>'
    meses_html = []
    for (y, m) in sorted(pormes, reverse=True):
        mfilas = pormes[(y, m)]
        mpz = sum(x["cant"] for x in mfilas); n = len(mfilas)
        abierto = "open" if pormes and (y, m) == max(pormes) else ""
        meses_html.append(f"""      <details class="mes" {abierto}>
        <summary><span class="mtit">{MESLARGO[m]} {y}</span><span class="mtot">{mpz:g} pz · {n} mermas</span></summary>
{dias_html(mfilas)}
      </details>""")

    # caja de AJUSTES (no es merma real), separada
    aj_html = ""
    if ajustes:
        aj_html = f"""      <details class="ajustes">
        <summary>⚙️ Ajustes y correcciones de captura (NO es merma) — {total_aj:g} pz</summary>
{dias_html(ajustes)}
      </details>"""

    return f"""    <div class="suc"><div class="suc-head"><h3>{nombre}</h3>
      <span class="tag">merma real: {total_real:g} pz</span></div>
      <div class="chips">{chips}</div>
      <div class="cuerpo">
{chr(10).join(meses_html)}
{aj_html}
      </div>
    </div>"""

cards = "\n".join(card(n, f) for n, f in datos)
now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

HTML = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Todas las Mermas · Titi Burger</title>
<style>
:root{{--bg:#0f1115;--card:#171a21;--line:#262b36;--txt:#e8eaed;--mut:#9aa2b1;
  --accent:#ff7a1a;--ok:#2ecc71;--warn:#ffb020;--bad:#ff4d4d;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;font-size:15px}}
header{{padding:16px}}
.title{{display:flex;align-items:center;gap:10px}} .title h1{{font-size:21px;margin:0}} .emoji{{font-size:24px}}
.sub{{color:var(--mut);font-size:13px;margin-top:4px;line-height:1.45}}
.aviso{{background:#101c24;border:1px solid #1d3745;color:#a9d8ea;
  padding:10px 12px;border-radius:10px;font-size:12.5px;margin:8px 16px 0;line-height:1.45}}
.suc{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:14px 16px;overflow:hidden}}
.suc.off{{opacity:.7}}
.suc-head{{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid var(--line);gap:8px}}
.suc-head h3{{margin:0;font-size:17px}}
.tag{{font-size:12px;font-weight:800;border-radius:999px;padding:3px 11px;background:rgba(255,122,26,.16);color:var(--accent);white-space:nowrap}}
.tag.gris{{background:#2a3140;color:var(--mut)}}
.chips{{display:flex;gap:8px;flex-wrap:wrap;padding:12px 14px;border-bottom:1px solid var(--line)}}
.chip{{background:#0c0e12;border:1px solid var(--line);border-radius:10px;padding:8px 12px;min-width:78px}}
.chip .cm{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.4px;font-weight:800}}
.chip .cv{{font-size:17px;font-weight:800;color:#ffd9b0;margin-top:2px}}
.chip .cp{{font-size:11px;color:var(--mut)}}
.cuerpo{{padding:2px 0}}
.mes{{border-bottom:1px solid var(--line)}}
.mes>summary{{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;
  padding:12px 14px;background:rgba(255,122,26,.05)}}
.mes>summary::-webkit-details-marker{{display:none}}
.mes>summary::before{{content:"▸";color:var(--accent);margin-right:8px;font-size:12px}}
.mes[open]>summary::before{{content:"▾"}}
.mtit{{font-weight:800;font-size:15px;flex:1}}
.mtot{{color:var(--bad);font-weight:800;font-size:13px}}
.dia{{border-top:1px solid var(--line)}}
.dia-head{{display:flex;justify-content:space-between;align-items:center;padding:9px 14px 5px 26px}}
.dia-head .fe{{font-weight:700;font-size:13px}}
.dia-head .subd{{color:var(--bad);font-size:12px;font-weight:700}}
.dia td{{padding-left:26px}}
.motivo{{display:inline-block;margin-left:8px;font-size:10.5px;font-weight:700;color:#a9d8ea;
  background:rgba(41,120,150,.18);border-radius:5px;padding:1px 6px;vertical-align:middle}}
.ajustes{{border-top:2px solid var(--line);background:rgba(154,162,177,.05)}}
.ajustes>summary{{list-style:none;cursor:pointer;padding:12px 14px;color:var(--mut);font-weight:700;font-size:13px}}
.ajustes>summary::-webkit-details-marker{{display:none}}
.ajustes>summary::before{{content:"▸";margin-right:8px}}
.ajustes[open]>summary::before{{content:"▾"}}
table{{width:100%;border-collapse:collapse}}
td{{padding:5px 14px;font-size:13.5px;border:0}}
td.ins{{color:var(--txt)}}
td.cant{{text-align:right;color:var(--mut);white-space:nowrap;font-variant-numeric:tabular-nums}}
td.val{{text-align:right;font-weight:700;color:#ffd9b0;white-space:nowrap;width:74px;font-variant-numeric:tabular-nums}}
footer{{padding:22px 16px;color:var(--mut);font-size:12px;text-align:center;line-height:1.5}}
</style></head><body>
<header>
  <div class="title"><span class="emoji">🍔</span><h1>Todas las Mermas</h1></div>
  <div class="sub">Titi Burger · mermas registradas en Soft Restaurant · por mes, en piezas (desde junio 2026) · consultado {now}</div>
</header>
<div class="aviso">
  📋 Mermas capturadas en Soft Restaurant, <b>por mes y en cantidades (piezas)</b> — toca un mes para
  el detalle por día. <b>Separé la merma real de los ajustes/errores de captura</b> (ej. "ERROR BUBU" =
  corrección de inventario, NO producto tirado): esos van hasta abajo en su propia caja. El total de
  arriba es solo <b>merma real</b>.
</div>
{cards}
<footer>
  Generado por Tito 🍔 · Fuente: movimientos de merma (movsinv: ETA a almacén de mermas, SPM, SPD).
</footer>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
