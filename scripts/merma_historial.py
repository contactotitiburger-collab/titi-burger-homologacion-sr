#!/usr/bin/env python3
"""HISTORIAL DE MERMAS con fecha — Titi Burger.

Soft Restaurant SÍ guarda historial de merma: son los INVENTARIOS FÍSICOS (tabla
invfisico). Cada uno = una fecha en que contaron físico contra lo teórico del sistema;
la diferencia (en pesos) es la merma real de ese conteo. El detalle por insumo está en
invfisicomovtos (teórico vs físico vs diferencia, con costo).

Este reporte arma la línea de tiempo de mermas por sucursal + el detalle de faltantes
de cada conteo. Es lo que YA existe registrado (no cada 3 días: cuando hicieron conteo).

Escribe merma_historial.html en la carpeta del link público.
"""
import pymssql, socket, datetime
from pathlib import Path

BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
OUT  = BASE / "merma_historial.html"
SUC  = [("Hacienda del Río", "100.80.102.110"), ("Cine Curto", "100.94.218.56")]
U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"

# Descarta renglones basura (cargas iniciales del sistema, no merma real)
def basura(teo, dif):
    return abs(teo) > 60000 or teo < -2000 or abs(dif) > 60000

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
def fmt(d): return f"{d.day}/{MES[d.month]}/{d.year}"

def jalar(host):
    pt = puerto(host)
    if not pt: return None
    c = pymssql.connect(server=host, port=pt, user=U, password=P, database=DB,
                        tds_version=TDS, timeout=25, login_timeout=15)
    cur = c.cursor()
    cur.execute("""SELECT folio, fecha, inventarioteorico1, inventariofisico1, diferenciafisico1
                   FROM invfisico WHERE cancelado=0 AND fecha>='2025-01-01' ORDER BY fecha DESC""")
    conteos = []
    for f, fe, t, fi, di in cur.fetchall():
        t, fi, di = float(t or 0), float(fi or 0), float(di or 0)
        if basura(t, di): continue
        # detalle: top faltantes (diferencia negativa) con pesos
        cur.execute("""SELECT TOP 8 i.descripcion, m.diferenciaalmacen1, m.costo
                       FROM invfisicomovtos m JOIN insumos i ON i.idinsumo=m.idinsumo
                       WHERE m.folio=%s AND m.diferenciaalmacen1<0
                       ORDER BY (m.diferenciaalmacen1*m.costo)""", (int(f),))
        det = [(d.strip().title(), float(dd or 0), float(co or 0)) for d, dd, co in cur.fetchall()]
        conteos.append({"folio": int(f), "fecha": fe, "teo": t, "fis": fi, "dif": di, "det": det})
    c.close()
    return conteos

datos = []
for nombre, host in SUC:
    try:
        cs = jalar(host)
        datos.append((nombre, cs))
        print(f"{nombre:18s} {'OFFLINE' if cs is None else str(len(cs))+' conteos'}")
    except Exception as e:
        datos.append((nombre, None)); print(f"{nombre:18s} ERROR {e}")

def card(nombre, cs):
    if cs is None:
        return f"""    <div class="suc off"><div class="suc-head"><h3>{nombre}</h3><span class="tag gris">sin conexión</span></div></div>"""
    if not cs:
        return f"""    <div class="suc off"><div class="suc-head"><h3>{nombre}</h3><span class="tag gris">sin conteos</span></div>
      <div class="vacio">No hay inventarios físicos registrados en el rango.</div></div>"""
    ult = cs[0]
    merma_neg = sum(x["dif"] for x in cs if x["dif"] < 0)
    filas = []
    for x in cs:
        dif = x["dif"]
        cls = "neg" if dif < 0 else ("pos" if dif > 0 else "")
        signo = "merma" if dif < 0 else ("sobrante" if dif > 0 else "cuadró")
        det = ""
        if x["det"]:
            items = "".join(f"<li>{d}: <b>{dd:g} pz</b> (${abs(dd)*co:,.0f})</li>" for d, dd, co in x["det"])
            det = f'<details><summary>ver faltantes</summary><ul>{items}</ul></details>'
        filas.append(f"""      <tr class="{cls}">
        <td class="fe">{fmt(x['fecha'])}</td>
        <td class="num">${x['teo']:,.0f}</td>
        <td class="num">${x['fis']:,.0f}</td>
        <td class="num dif">${dif:,.0f}<span class="lbl2">{signo}</span></td>
        <td class="det">{det}</td>
      </tr>""")
    return f"""    <div class="suc"><div class="suc-head"><h3>{nombre}</h3>
      <span class="tag">{len(cs)} conteos · último {fmt(ult['fecha'])}</span></div>
      <table><thead><tr><th>Fecha</th><th>Teórico</th><th>Físico</th><th>Diferencia</th><th></th></tr></thead>
      <tbody>
{chr(10).join(filas)}
      </tbody></table>
      <div class="pie">Merma acumulada de estos conteos (solo faltantes): <b>${merma_neg:,.0f}</b></div>
    </div>"""

cards = "\n".join(card(n, cs) for n, cs in datos)
now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

HTML = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Historial de Mermas · Titi Burger</title>
<style>
:root{{--bg:#0f1115;--card:#171a21;--line:#262b36;--txt:#e8eaed;--mut:#9aa2b1;
  --accent:#ff7a1a;--ok:#2ecc71;--warn:#ffb020;--bad:#ff4d4d;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;font-size:15px}}
header{{padding:16px}}
.title{{display:flex;align-items:center;gap:10px}} .title h1{{font-size:21px;margin:0}} .emoji{{font-size:24px}}
.sub{{color:var(--mut);font-size:13px;margin-top:4px;line-height:1.45}}
.aviso{{background:#0f1c14;border:1px solid #1d3d2a;color:#a9e5c0;
  padding:10px 12px;border-radius:10px;font-size:12.5px;margin:8px 16px 0;line-height:1.45}}
.suc{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:14px 16px;overflow:hidden}}
.suc.off{{opacity:.7}}
.suc-head{{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid var(--line)}}
.suc-head h3{{margin:0;font-size:17px}}
.tag{{font-size:12px;font-weight:800;border-radius:999px;padding:3px 11px;background:rgba(255,122,26,.16);color:var(--accent)}}
.tag.gris{{background:#2a3140;color:var(--mut)}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px}}
th:nth-child(2),th:nth-child(3),th:nth-child(4),td.num{{text-align:right}}
td.num{{font-variant-numeric:tabular-nums}}
td.dif{{font-weight:800;white-space:nowrap}}
tr.neg td.dif{{color:var(--bad)}} tr.pos td.dif{{color:var(--ok)}}
.lbl2{{display:block;font-size:10px;font-weight:700;color:var(--mut);text-transform:uppercase}}
td.fe{{font-weight:700;white-space:nowrap}}
details summary{{cursor:pointer;color:var(--accent);font-size:12px}}
details ul{{margin:6px 0 0;padding-left:16px;color:var(--mut);font-size:12.5px;line-height:1.6}}
.pie{{padding:10px 14px;color:var(--mut);font-size:13px;border-top:1px solid var(--line);background:rgba(255,77,77,.05)}}
.vacio{{padding:12px 14px;color:var(--mut);font-size:13px}}
footer{{padding:22px 16px;color:var(--mut);font-size:12px;text-align:center;line-height:1.5}}
</style></head><body>
<header>
  <div class="title"><span class="emoji">🍔</span><h1>Historial de Mermas</h1></div>
  <div class="sub">Titi Burger · inventarios físicos registrados en Soft Restaurant · consultado {now}</div>
</header>
<div class="aviso">
  ✅ Esto SÍ es merma real con fecha: cada renglón es un <b>inventario físico</b> que hicieron
  (contaron a mano) contra lo teórico del sistema. La <b>diferencia en rojo = merma en pesos</b>.
  No es cada 3 días — es cuando decidieron contar. Cine Curto cuenta seguido; Hacienda dejó de contar.
</div>
{cards}
<footer>
  Generado por Tito 🍔 · Fuente: inventarios físicos (invfisico) de Soft Restaurant.<br>
  Los conteos muy viejos con cifras imposibles (cargas iniciales) se filtraron.
</footer>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
