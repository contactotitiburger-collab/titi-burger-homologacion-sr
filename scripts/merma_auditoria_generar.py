#!/usr/bin/env python3
"""Hoja de AUDITORÍA DE MERMAS (conteo físico) por sucursal — Titi Burger.

Lee la existencia que dice Soft Restaurant (inv_data.json del tablero) y arma una
página web imprimible/llenable con: lo que dice el sistema + conteo físico (en blanco)
+ diferencia (auto). Solo CARNE + los pesados (carne, pan, tocino, queso, pollo, papa).

OJO: Soft Restaurant NO registra mermas (tabla movtosalmacen vacía). Lo que ves como
"Sistema" es la EXISTENCIA TEÓRICA (foto viva). La MERMA REAL sale de la diferencia
contra el conteo físico que hagan en piso.

Uso: python3 merma_auditoria_generar.py
     -> escribe ~/.openclaw/workspace/titi-inventario-demo/auditoria_mermas.html
"""
import json, datetime
from pathlib import Path

BASE = Path.home() / ".openclaw/workspace/titi-inventario-demo"
DATA = BASE / "inv_data.json"
OUT  = BASE / "auditoria_mermas.html"

# --- Filtro: carne + los pesados (lo que el usuario pidió) ---
PESADOS = ("carne", "pan", "tocino", "queso", "pollo", "papa", "slider")
EXCLUIR_DESC = ("plato",)  # "platos para papas" = desechable, no es pesado

def es_pesado(desc, fam):
    d = desc.lower()
    if any(x in d for x in EXCLUIR_DESC):
        return False
    if "desechable" in (fam or "").lower():
        return False
    return any(k in d for k in PESADOS)

# Plantilla para sucursales sin conexión (Montejano, Montecarlo): que igual auditen a mano
PLANTILLA_OFFLINE = [
    ("Carne para hamburguesa", "PZA"),
    ("Pan parrillero",         "PZA"),
    ("Queso",                  "PZA"),
    ("Queso amarillo",         "PZA"),
    ("Tocino",                 "PZA"),
    ("Pollo",                  "PZA"),
    ("Papas a la francesa",    "PZA"),
]

data = json.loads(DATA.read_text())
gen_human = data.get("generated_human", "")

# --- Semana actual y los dos cortes de 3 días ---
hoy = datetime.date.today()
lunes = hoy - datetime.timedelta(days=hoy.weekday())        # lunes de esta semana
mie   = lunes + datetime.timedelta(days=2)
jue   = lunes + datetime.timedelta(days=3)
sab   = lunes + datetime.timedelta(days=5)
def f(d): return d.strftime("%d/%b").lower()
iso = hoy.isocalendar()[1]

CORTES = [
    {"id": "c1", "label": "Corte 1 · Lunes a Miércoles", "rango": f"{f(lunes)} – {f(mie)}"},
    {"id": "c2", "label": "Corte 2 · Jueves a Sábado",   "rango": f"{f(jue)} – {f(sab)}"},
]

def rows_de_sucursal(suc):
    """Devuelve lista de (desc, unidad, sr_existencia|None)."""
    if suc.get("items"):
        out = []
        for it in suc["items"]:
            if es_pesado(it["desc"], it.get("fam", "")):
                out.append((it["desc"].title(), it["unidad"], it["exist"]))
        # ordenar: carne primero, luego pan, luego el resto alfabético
        def rank(r):
            d = r[0].lower()
            if "carne" in d or "slider" in d: return (0, d)
            if "pan"  in d: return (1, d)
            if "pollo" in d: return (2, d)
            if "tocino" in d: return (3, d)
            if "queso" in d: return (4, d)
            if "papa" in d: return (5, d)
            return (6, d)
        return sorted(out, key=rank)
    # sin datos -> plantilla en blanco
    return [(d, u, None) for d, u in PLANTILLA_OFFLINE]

def estado_suc(suc):
    if suc.get("stale"):
        return ("cache", f"última info {suc.get('last_human','')}")
    if suc.get("live"):
        return ("live", "en vivo")
    return ("off", "sin conexión — capturar a mano")

# --- Construir tabla por sucursal x corte ---
def tabla_html(suc, corte_id):
    rows = rows_de_sucursal(suc)
    n = suc["n"]
    trs = []
    for i, (desc, uni, sr) in enumerate(rows):
        sr_txt = "—" if sr is None else (f"{sr:g}")
        sr_attr = "" if sr is None else f'data-sr="{sr}"'
        # llave ESTABLE por descripción (no por índice) para que lo capturado no se
        # despegue aunque el orden/estado de una sucursal cambie al regenerar.
        slug = desc.lower().replace(" ", "_").replace("|", "")
        key = f"{corte_id}|{n}|{slug}"
        neg = (sr is not None and sr < 0)
        row_cls = ' class="r-negsr"' if neg else ''
        negtag = ' <span class="negsr-tag">SISTEMA EN NEGATIVO</span>' if neg else ''
        trs.append(f"""      <tr{row_cls} data-suc="{n}" data-corte="{corte_id}">
        <td class="ins">{desc}{negtag}</td>
        <td class="uni">{uni}</td>
        <td class="sr" {sr_attr}>{sr_txt}</td>
        <td class="fis"><input type="text" inputmode="decimal" data-key="{key}" class="fisico" placeholder=""></td>
        <td class="dif"><span class="difval" data-key="{key}">—</span></td>
        <td class="mot"><input type="text" data-key="{key}m" class="motivo" placeholder=""></td>
      </tr>""")
    est, est_txt = estado_suc(suc)
    badge = {"live": "🟢", "cache": "🟡", "off": "⚪"}[est]
    return f"""    <div class="suc" data-sucname="{n}" data-corte="{corte_id}">
      <div class="suc-head">
        <h3>{n} <span class="cnt-merma cero" data-suc="{n}" data-corte="{corte_id}">sin contar</span></h3>
        <span class="badge {est}">{badge} {est_txt}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th class="ins">Insumo</th>
            <th class="uni">Un.</th>
            <th class="sr">Sistema<br><small>(SR dice)</small></th>
            <th class="fis">Conteo<br>físico</th>
            <th class="dif">Diferencia</th>
            <th class="mot">Motivo / nota</th>
          </tr>
        </thead>
        <tbody>
{chr(10).join(trs)}
        </tbody>
      </table>
    </div>"""

# --- Secciones por corte ---
secciones = []
for c in CORTES:
    sucs_html = "\n".join(tabla_html(s, c["id"]) for s in data["sucursales"])
    secciones.append(f"""  <section class="corte" id="{c['id']}" data-corte="{c['id']}">
    <div class="corte-head">
      <div>
        <h2>{c['label']}</h2>
        <div class="rango">{c['rango']}</div>
      </div>
      <label class="fecha-conteo">Fecha del conteo físico:
        <input type="text" data-key="fecha|{c['id']}" class="fechaconteo" placeholder="__ / __ / ____">
      </label>
    </div>
    <div class="resumen" data-corte="{c['id']}">
      <div class="rz bad"><div class="big" data-rz="ins">0</div><div class="lbl">Insumos con merma</div></div>
      <div class="rz bad"><div class="big" data-rz="suc">0</div><div class="lbl">Sucursales con bronca</div></div>
      <div class="rz warn"><div class="big" data-rz="pzs">0</div><div class="lbl">Piezas faltantes</div></div>
    </div>
{sucs_html}
  </section>""")

HTML = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auditoría de Mermas · Titi Burger</title>
<style>
:root{{
  --bg:#0f1115; --card:#171a21; --line:#262b36; --txt:#e8eaed; --mut:#9aa2b1;
  --accent:#ff7a1a; --ok:#2ecc71; --warn:#ffb020; --bad:#ff4d4d;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  font-size:15px;-webkit-text-size-adjust:100%}}
header{{padding:16px 16px 8px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}}
.title{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.title h1{{font-size:20px;margin:0}}
.emoji{{font-size:22px}}
.sub{{color:var(--mut);font-size:13px;margin-top:4px;line-height:1.4}}
.aviso{{background:#2a1c10;border:1px solid #5a3a12;color:#ffcf9e;
  padding:10px 12px;border-radius:10px;font-size:13px;margin:10px 16px 0;line-height:1.45}}
.tabs{{display:flex;gap:8px;padding:12px 16px 4px;flex-wrap:wrap}}
.tab{{background:var(--card);border:1px solid var(--line);color:var(--txt);
  padding:8px 14px;border-radius:999px;font-size:14px;cursor:pointer;font-weight:600}}
.tab.active{{background:var(--accent);border-color:var(--accent);color:#111}}
.toolbar{{display:flex;gap:8px;padding:4px 16px 12px;flex-wrap:wrap;align-items:center}}
.btn{{background:var(--card);border:1px solid var(--line);color:var(--txt);
  padding:8px 12px;border-radius:8px;cursor:pointer;font-size:13px}}
.btn.primary{{background:var(--accent);border-color:var(--accent);color:#111;font-weight:700}}
.corte{{display:none;padding:0 16px 40px}}
.corte.active{{display:block}}
.corte-head{{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;
  flex-wrap:wrap;margin:14px 0 6px;padding-bottom:8px;border-bottom:1px solid var(--line)}}
.corte-head h2{{margin:0;font-size:18px}}
.rango{{color:var(--mut);font-size:13px;margin-top:2px}}
.fecha-conteo{{font-size:13px;color:var(--mut)}}
.fecha-conteo input{{margin-left:6px}}
.suc{{background:var(--card);border:1px solid var(--line);border-radius:12px;
  margin-top:14px;overflow:hidden}}
.suc-head{{display:flex;justify-content:space-between;align-items:center;
  padding:12px 14px;border-bottom:1px solid var(--line)}}
.suc-head h3{{margin:0;font-size:16px}}
.badge{{font-size:12px;color:var(--mut)}}
.badge.off{{color:#8891a2}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:9px 8px;text-align:left;border-bottom:1px solid var(--line);vertical-align:middle}}
th{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px;font-weight:700}}
td.ins{{font-weight:600}}
.uni{{width:44px;color:var(--mut);font-size:12px}}
.sr{{width:74px;text-align:right;font-variant-numeric:tabular-nums;color:#cdd3de}}
th.sr{{text-align:right}}
.fis{{width:88px}}
.dif{{width:82px;text-align:right}}
.mot{{width:26%}}
input{{width:100%;background:#0c0e12;border:1px solid var(--line);color:var(--txt);
  border-radius:7px;padding:7px 8px;font-size:15px;font-variant-numeric:tabular-nums}}
input.fisico{{text-align:right}}
input:focus{{outline:none;border-color:var(--accent)}}
.difval{{display:inline-block;min-width:78px;text-align:center;font-weight:800;
  font-size:13px;padding:4px 6px;border-radius:7px;background:#20242e;color:var(--mut);
  font-variant-numeric:tabular-nums;line-height:1.1}}
.difval.ok{{background:rgba(46,204,113,.16);color:var(--ok)}}
.difval.faltan{{background:var(--bad);color:#fff}}
.difval.sobran{{background:rgba(255,176,32,.18);color:var(--warn)}}
/* colorear TODO el renglón para que salte a la vista */
tr.r-faltan{{background:rgba(255,77,77,.12)}}
tr.r-faltan td.ins{{color:#ff9a9a}}
tr.r-sobran{{background:rgba(255,176,32,.08)}}
tr.r-ok{{background:rgba(46,204,113,.06)}}
tr.r-negsr{{background:rgba(255,77,77,.10)}}
.negsr-tag{{display:inline-block;margin-left:6px;font-size:10px;font-weight:800;
  color:#fff;background:var(--bad);border-radius:5px;padding:1px 5px;vertical-align:middle}}
/* resumen que grita dónde hay merma */
.resumen{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 2px}}
.rz{{flex:1;min-width:130px;background:var(--card);border:1px solid var(--line);
  border-radius:10px;padding:10px 12px}}
.rz .big{{font-size:24px;font-weight:800;line-height:1}}
.rz .lbl{{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.3px;margin-top:4px}}
.rz.bad .big{{color:var(--bad)}}
.rz.warn .big{{color:var(--warn)}}
.suc.tiene-merma{{border-color:var(--bad)}}
.suc.tiene-merma .suc-head{{background:rgba(255,77,77,.10)}}
.cnt-merma{{display:inline-block;font-size:12px;font-weight:800;color:#fff;
  background:var(--bad);border-radius:999px;padding:2px 9px;margin-left:8px}}
.cnt-merma.cero{{background:#2a3140;color:var(--mut)}}
footer{{padding:20px 16px;color:var(--mut);font-size:12px;text-align:center;line-height:1.5}}
@media (max-width:560px){{
  .mot{{display:none}} th.mot{{display:none}}
  body{{font-size:14px}}
}}
@media print{{
  :root{{--bg:#fff;--card:#fff;--line:#bbb;--txt:#000;--mut:#444}}
  body{{font-size:11px}}
  header,.tabs,.toolbar{{position:static}}
  .tab,.btn{{display:none}}
  .corte{{display:block !important;page-break-after:always}}
  .aviso{{color:#7a3d00;background:#fff;border-color:#aaa}}
  input{{border:1px solid #999;background:#fff}}
}}
</style>
</head>
<body>
<header>
  <div class="title"><span class="emoji">🍔</span><h1>Auditoría de Mermas</h1></div>
  <div class="sub">Titi Burger · Semana {iso} · Carne + pesados (carne, pan, tocino, queso, pollo, papa)<br>
    Existencia del sistema tomada de Soft Restaurant al <b>{gen_human}</b></div>
</header>

<div class="aviso">
  ⚠️ <b>Soft Restaurant no guarda mermas.</b> La columna <b>Sistema</b> es la existencia
  <b>teórica</b> (lo que SR cree que hay). La <b>merma real</b> es la <b>diferencia</b> contra
  el conteo físico. Cuenta en piso, anota, y donde falte de más = ahí está la fuga.
</div>

<div class="tabs" id="tabs">
  <button class="tab active" data-go="c1">Lun–Mié</button>
  <button class="tab" data-go="c2">Jue–Sáb</button>
</div>
<div class="toolbar">
  <button class="btn primary" onclick="window.print()">🖨️ Imprimir / PDF</button>
  <button class="btn" id="btnClear">Borrar lo capturado</button>
  <span class="sub" style="margin:0">Lo que escribes se guarda solo en este dispositivo.</span>
</div>

{chr(10).join(secciones)}

<footer>
  Generado por Tito 🍔 · La existencia del sistema se refresca sola cada 15 min en la Z2.<br>
  Para números exactos del día del corte, regenera esta hoja ese mismo día.
</footer>

<script>
// --- persistencia local ---
const store = {{
  get:k=>localStorage.getItem('audmerma:'+k)||'',
  set:(k,v)=>localStorage.setItem('audmerma:'+k,v)
}};
function calcDif(inp){{
  const tr=inp.closest('tr');
  const srEl=tr.querySelector('.sr');
  const sr=srEl && srEl.dataset.sr!==undefined ? parseFloat(srEl.dataset.sr) : NaN;
  const out=tr.querySelector('.difval');
  const wasNeg = tr.dataset.neg==='1' || tr.classList.contains('r-negsr');
  if(wasNeg) tr.dataset.neg='1';
  tr.classList.remove('r-faltan','r-ok','r-sobran','r-negsr');
  const raw=inp.value.trim().replace(',','.');
  if(raw===''){{
    out.textContent='—'; out.className='difval';
    // sin contar: si el sistema ya está en negativo, dejarlo marcado en rojo
    if(tr.dataset.neg==='1') tr.classList.add('r-negsr');
    return;
  }}
  const fis=parseFloat(raw);
  if(isNaN(fis)||isNaN(sr)){{ out.textContent='—'; out.className='difval'; return; }}
  const dif=+(fis-sr).toFixed(2);   // físico - sistema
  if(dif===0){{ out.textContent='OK'; out.className='difval ok'; tr.classList.add('r-ok'); }}
  else if(dif<0){{ out.textContent='FALTAN '+Math.abs(dif); out.className='difval faltan'; tr.classList.add('r-faltan'); }} // hay MENOS = merma/fuga
  else {{ out.textContent='SOBRAN '+dif; out.className='difval sobran'; tr.classList.add('r-sobran'); }}      // hay MÁS = mal capturado
}}
// ¿este renglón cuenta como merma? faltante contado, o sistema en negativo aún sin contar
function esMerma(tr){{
  if(tr.classList.contains('r-faltan')) return true;
  if(tr.classList.contains('r-negsr')) return true;
  return false;
}}
function piezasFaltan(tr){{
  const out=tr.querySelector('.difval');
  const m=out.textContent.match(/FALTAN\\s+([\\d.]+)/);
  if(m) return parseFloat(m[1]);
  const srEl=tr.querySelector('.sr');
  const sr=srEl && srEl.dataset.sr!==undefined ? parseFloat(srEl.dataset.sr) : 0;
  if(tr.classList.contains('r-negsr') && sr<0) return Math.abs(sr); // negativo = al menos esas piezas descuadradas
  return 0;
}}
function recompute(){{
  document.querySelectorAll('.corte').forEach(sec=>{{
    let totIns=0, totPz=0; const sucsMal=new Set();
    sec.querySelectorAll('.suc').forEach(suc=>{{
      let n=0;
      suc.querySelectorAll('tbody tr').forEach(tr=>{{
        if(esMerma(tr)){{ n++; totIns++; totPz+=piezasFaltan(tr); sucsMal.add(suc.dataset.sucname); }}
      }});
      const badge=suc.querySelector('.cnt-merma');
      const anyCount=suc.querySelector('.fisico') && [...suc.querySelectorAll('.fisico')].some(i=>i.value.trim());
      if(n>0){{ badge.textContent='🔴 '+n+' con merma'; badge.className='cnt-merma'; suc.classList.add('tiene-merma'); }}
      else {{ badge.textContent = anyCount ? '✅ sin merma' : 'sin contar'; badge.className='cnt-merma cero'; suc.classList.remove('tiene-merma'); }}
    }});
    const rz=sec.querySelector('.resumen');
    if(rz){{
      rz.querySelector('[data-rz=ins]').textContent=totIns;
      rz.querySelector('[data-rz=suc]').textContent=sucsMal.size;
      rz.querySelector('[data-rz=pzs]').textContent=+totPz.toFixed(1);
    }}
  }});
}}
document.querySelectorAll('input').forEach(inp=>{{
  const k=inp.dataset.key;
  if(k){{ inp.value=store.get(k); }}
  inp.addEventListener('input',()=>{{
    if(k) store.set(k,inp.value);
    if(inp.classList.contains('fisico')) calcDif(inp);
    recompute();
  }});
  if(inp.classList.contains('fisico')) calcDif(inp);
}});
recompute();
// --- tabs ---
const tabs=document.getElementById('tabs');
tabs.addEventListener('click',e=>{{
  const b=e.target.closest('.tab'); if(!b)return;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.corte').forEach(c=>c.classList.remove('active'));
  b.classList.add('active');
  document.getElementById(b.dataset.go).classList.add('active');
}});
document.getElementById('c1').classList.add('active');
document.getElementById('btnClear').addEventListener('click',()=>{{
  if(!confirm('¿Borrar todo lo que capturaste en esta hoja?'))return;
  Object.keys(localStorage).filter(k=>k.startsWith('audmerma:')).forEach(k=>localStorage.removeItem(k));
  location.reload();
}});
</script>
</body>
</html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
# resumen en consola
for s in data["sucursales"]:
    rows = rows_de_sucursal(s)
    est,_ = estado_suc(s)
    print(f"  {s['n']:18s} [{est:5s}] {len(rows)} insumos pesados")
