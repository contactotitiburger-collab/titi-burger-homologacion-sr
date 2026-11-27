#!/usr/bin/env python3
"""REPORTE DE MERMAS registradas en Soft Restaurant — Titi Burger.

Lee el "Almacén de Mermas" de cada sucursal (el cajón donde SR acumula lo que se
registra como merma) y arma un reporte web limpio. NO cuadra nada contra la carreta:
es solo lo que ya está capturado como merma en el sistema.

- Detecta el almacén de mermas por nombre (LIKE '%MERMA%').
- Solo Hacienda y Cine Curto lo tienen configurado hoy; los demás salen marcados.
- Sin fecha de movimiento en SR -> es un ACUMULADO. Guarda snapshot diario en
  merma_hist.json para poder sacar "merma cada 3 días" a futuro (diferencia de fotos).

Escribe merma_reporte.html en la carpeta del link público. Colgar de refresh.sh.
"""
import pymssql, socket, json, datetime
from pathlib import Path

BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
OUT  = BASE / "merma_reporte.html"
HIST = BASE / "merma_hist.json"

# Todas las sucursales; server=None => no conectada
SUCURSALES = [
    {"n": "Hacienda del Río", "server": "100.80.102.110"},
    {"n": "Villas del Rey",   "server": "100.66.22.9"},
    {"n": "San Marcos",       "server": "100.101.205.89"},
    {"n": "Cine Curto",       "server": "100.94.218.56"},
    {"n": "Montejano",        "server": None, "motivo": "cerrada por el incendio"},
    {"n": "Montecarlo",       "server": None, "motivo": "compu apagada"},
]
U, P, DB, TDS = "tito", os.environ.get("SR_SQL_PASS",""), "softrestaurant11", "7.0"

def puerto(host):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(6)
    try:
        s.sendto(b"\x02", (host, 1434)); d, _ = s.recvfrom(65535)
        p = d[3:].decode("ascii", "replace").split(";")
        for i, x in enumerate(p):
            if x == "tcp": return int(p[i + 1])
    finally:
        s.close()
    return None

def jalar_merma(host):
    """Devuelve (estado, items). items = lista de merma en el almacén de mermas."""
    pt = puerto(host)
    if not pt:
        return ("offline", [])
    c = pymssql.connect(server=host, port=pt, user=U, password=P, database=DB,
                        tds_version=TDS, timeout=18, login_timeout=12)
    cur = c.cursor()
    cur.execute("SELECT idalmacen, nombre FROM almacen WHERE UPPER(nombre) LIKE '%MERMA%'")
    row = cur.fetchone()
    if not row:
        c.close()
        return ("sin_alm", [])   # no tiene almacén de mermas configurado
    alm = str(row[0]).strip()
    cur.execute("""SELECT i.descripcion, i.unidad, a.existencia, g.descripcion
                   FROM acumuladoinsumos a JOIN insumos i ON i.idinsumo = a.idinsumo
                   LEFT JOIN gruposi g ON g.idgruposi = i.idgruposi
                   WHERE a.idalmacen = %s AND a.existencia <> 0""", (alm,))
    items = [{"desc": (d or "").strip().title(), "uni": (u or "").strip(),
              "cant": float(e or 0), "fam": (f or "Otros").strip().title()}
             for d, u, e, f in cur.fetchall()]
    c.close()
    return ("ok", items)

now = datetime.datetime.now()
hoy_iso = now.strftime("%Y-%m-%d")
gen_human = now.strftime("%d/%m/%Y %H:%M")

resultados = []
for s in SUCURSALES:
    if not s["server"]:
        resultados.append({**s, "estado": "offline", "items": []})
        continue
    try:
        est, items = jalar_merma(s["server"])
        resultados.append({**s, "estado": est, "items": items})
        print(f"{s['n']:18s} {est:8s} {len(items)} insumos con merma")
    except Exception as e:
        resultados.append({**s, "estado": "offline", "items": []})
        print(f"{s['n']:18s} ERROR {e}")

# --- snapshot histórico (para merma por periodo a futuro) ---
try:
    hist = json.loads(HIST.read_text())
except Exception:
    hist = {}
hist[hoy_iso] = {r["n"]: {it["desc"]: it["cant"] for it in r["items"]}
                 for r in resultados if r["estado"] == "ok"}
HIST.write_text(json.dumps(hist, ensure_ascii=False))

# --- HTML ---
def card(r):
    n = r["n"]
    if r["estado"] == "offline":
        return f"""    <div class="suc off"><div class="suc-head"><h3>{n}</h3>
      <span class="tag gris">⚪ sin conexión</span></div>
      <div class="vacio">No pude leer esta sucursal ({r.get('motivo','compu apagada')}).</div></div>"""
    if r["estado"] == "sin_alm":
        return f"""    <div class="suc off"><div class="suc-head"><h3>{n}</h3>
      <span class="tag gris">sin almacén de mermas</span></div>
      <div class="vacio">Esta sucursal <b>no registra merma en Soft Restaurant</b> (no tiene el cajón configurado).</div></div>"""
    pos = sorted([i for i in r["items"] if i["cant"] > 0], key=lambda x: -x["cant"])
    neg = sorted([i for i in r["items"] if i["cant"] < 0], key=lambda x: x["cant"])
    total = sum(i["cant"] for i in pos)
    filas = "\n".join(f"""      <tr><td class="ins">{i['desc']}</td><td class="fam">{i['fam']}</td>
        <td class="cant">{i['cant']:g} {i['uni']}</td></tr>""" for i in pos)
    negbox = ""
    if neg:
        negf = "\n".join(f"""      <tr><td class="ins">{i['desc']}</td><td class="fam">{i['fam']}</td>
          <td class="cant neg">{i['cant']:g} {i['uni']}</td></tr>""" for i in neg)
        negbox = f"""      <details class="revisar"><summary>⚠️ {len(neg)} capturados en negativo (revisar captura)</summary>
        <table><tbody>
{negf}
        </tbody></table></details>"""
    return f"""    <div class="suc"><div class="suc-head"><h3>{n}</h3>
      <span class="tag verde">{len(pos)} insumos con merma</span></div>
      <table><thead><tr><th>Insumo</th><th>Familia</th><th>Merma</th></tr></thead>
      <tbody>
{filas}
      </tbody></table>
{negbox}
    </div>"""

cards = "\n".join(card(r) for r in resultados)
con_merma = [r for r in resultados if r["estado"] == "ok"]
n_suc = len(con_merma)

HTML = f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte de Mermas · Titi Burger</title>
<style>
:root{{--bg:#0f1115;--card:#171a21;--line:#262b36;--txt:#e8eaed;--mut:#9aa2b1;
  --accent:#ff7a1a;--ok:#2ecc71;--warn:#ffb020;--bad:#ff4d4d;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;font-size:15px}}
header{{padding:16px}}
.title{{display:flex;align-items:center;gap:10px}}
.title h1{{font-size:21px;margin:0}} .emoji{{font-size:24px}}
.sub{{color:var(--mut);font-size:13px;margin-top:4px;line-height:1.45}}
.aviso{{background:#101c24;border:1px solid #1d3745;color:#a9d8ea;
  padding:10px 12px;border-radius:10px;font-size:12.5px;margin:8px 16px 0;line-height:1.45}}
.suc{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:14px 16px;overflow:hidden}}
.suc.off{{opacity:.75}}
.suc-head{{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid var(--line)}}
.suc-head h3{{margin:0;font-size:17px}}
.tag{{font-size:12.5px;font-weight:800;border-radius:999px;padding:3px 11px}}
.tag.verde{{background:rgba(255,122,26,.16);color:var(--accent)}}
.tag.gris{{background:#2a3140;color:var(--mut)}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line)}}
th{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px}}
td.ins{{font-weight:600}} td.fam{{color:var(--mut);font-size:12px}}
td.cant{{text-align:right;font-variant-numeric:tabular-nums;font-weight:800;color:#ffd9b0;white-space:nowrap}}
th:last-child{{text-align:right}}
td.cant.neg{{color:#ff9a9a}}
.vacio{{padding:12px 14px;color:var(--mut);font-size:13px}}
.revisar{{padding:8px 14px 12px}}
.revisar summary{{cursor:pointer;color:var(--warn);font-size:12.5px;font-weight:700}}
.revisar td{{padding:7px 0}}
footer{{padding:22px 16px;color:var(--mut);font-size:12px;text-align:center;line-height:1.5}}
@media (max-width:520px){{ td.fam,th:nth-child(2){{display:none}} }}
</style></head><body>
<header>
  <div class="title"><span class="emoji">🍔</span><h1>Reporte de Mermas</h1></div>
  <div class="sub">Titi Burger · lo registrado en el Almacén de Mermas de Soft Restaurant · al <b>{gen_human}</b></div>
</header>
<div class="aviso">
  📋 Esto es la merma <b>ya capturada en Soft Restaurant</b> (acumulada, no por día — SR no
  guarda la fecha). Solo <b>{n_suc}</b> sucursales tienen el cajón de mermas configurado.
  Los "en negativo" están mal capturados y van en una lista aparte para revisar.
</div>
{cards}
<footer>
  Generado por Tito 🍔 · Fuente: Almacén de Mermas en Soft Restaurant (existencia acumulada).<br>
  Guardo foto diaria: en unos días podré darte la merma por periodo (cada 3 días) automática.
</footer>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
