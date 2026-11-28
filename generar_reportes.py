#!/usr/bin/env python3
"""Seccion REPORTES de la pagina de avance (Rafael, 27-nov-2026).
Como los portales de proyecto profesionales: cada reporte con fecha, version, para quien, estado
(En revision -> Aprobado), boton de aprobar y comentarios pegados al reporte (no perdidos en WhatsApp).
Datos: reportes_datos/ (codigos_propuesta.json) + noche_2026-11-26/propuestas.json. Nada inventado.
Aprobaciones/comentarios: los guarda avance_server.py en reportes_estado.json."""
import json, html, collections
from pathlib import Path
from datetime import datetime
BASE = Path(__file__).resolve().parent
TOKEN = (BASE / ".token_avance").read_text().strip()
OUT = BASE / "avance" / TOKEN / "reportes"; OUT.mkdir(parents=True, exist_ok=True)
DAT = BASE / "reportes_datos"
E = lambda t: html.escape(str(t if t is not None else ""))
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
def fecha_es(iso): y, m, d = map(int, iso.split("-")); return f"{d} de {MESES[m-1]} de {y}"
def num(n): return f"{n:,}"

CSS = """
:root{--bg:#EEF7FC;--bg-top:#D6EEFA;--card:#fff;--border:#E6EEF5;--blue:#1E90F0;--ink:#12324A;--ink2:#5B7488;--ok:#22C55E;--warn:#F5B83D;--bad:#F04E5E}
*{box-sizing:border-box}body{margin:0;font-family:"Poppins",system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}
.top{background:linear-gradient(180deg,var(--bg-top),var(--bg));padding:18px 16px 4px}
.wrap{max-width:860px;margin:0 auto;padding:0 16px 48px}
.volver{display:inline-flex;align-items:center;gap:6px;min-height:44px;color:var(--blue);text-decoration:none;font-weight:600;font-size:14px}
h1{font-size:24px;line-height:1.25;margin:6px 0 6px}h2{font-size:18px;margin:0 0 10px}h3{font-size:15px;margin:18px 0 8px}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 4px}.chip{font-size:12px;background:#fff;border:1px solid var(--border);border-radius:999px;padding:3px 10px;color:var(--ink2)}
.chip.estado{font-weight:600;color:#fff;border:none;background:var(--warn)}.chip.estado.ok{background:var(--ok)}
.card{background:var(--card);border:1px solid var(--border);border-radius:18px;box-shadow:0 4px 16px rgba(20,60,100,.06);padding:18px;margin:14px 0}
.lead{font-size:16px;margin:0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kpi{background:#fff;border:1px solid var(--border);border-radius:14px;padding:12px 14px}.kpi b{display:block;font-size:24px;line-height:1.2}.kpi span{font-size:13px;color:var(--ink2)}
.tabla{width:100%;border-collapse:collapse;font-size:13px}.tabla th{text-align:left;font-weight:600;color:var(--ink2);border-bottom:2px solid var(--border);padding:8px 6px;white-space:nowrap}
.tabla td{border-bottom:1px solid #F0F4F8;padding:8px 6px;vertical-align:top}.tabla td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.cod{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;white-space:nowrap}.cod.nuevo{color:var(--blue);font-weight:600}
.tag{display:inline-block;white-space:normal;font-size:11px;font-weight:600;border-radius:999px;padding:1px 8px;margin:1px 2px 1px 0}
.t-rep{background:#FDECEE;color:#C0283A}.t-cero{background:#FFF4DE;color:#9A6400}.t-ort{background:#EAF4FE;color:#1565C0}.t-choca{background:#FDECEE;color:#C0283A}.t-ok{background:#E6F7EC;color:#15803D}
details{background:#fff;border:1px solid var(--border);border-radius:14px;margin:10px 0}details>summary{cursor:pointer;list-style:none;padding:14px 16px;font-weight:600;display:flex;justify-content:space-between;gap:10px;min-height:48px;align-items:center}
details>summary::-webkit-details-marker{display:none}details>summary::after{content:"+";color:var(--blue);font-size:20px}details[open]>summary::after{content:"–"}
details .det{padding:0 12px 12px}
.regla{display:flex;gap:8px;align-items:stretch;flex-wrap:wrap;margin:10px 0}
.regla>div{flex:1;min-width:120px;border-radius:12px;padding:10px;text-align:center;background:#F4FAFE;border:1px solid var(--border)}
.regla .d{display:block;font-family:ui-monospace,Menlo,monospace;font-size:26px;font-weight:700;color:var(--blue)}.regla .l{font-size:12px;color:var(--ink2)}
.paso{display:flex;gap:12px;margin:12px 0}.paso .num{flex:0 0 30px;height:30px;border-radius:50%;background:var(--blue);color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center}
.nota{font-size:13px;color:var(--ink2)}
.tabla tr.fam td{background:#F4FAFE;font-weight:600;color:var(--ink2);font-size:12px;padding:6px}.tabla td.cods{white-space:nowrap}.codtab{table-layout:fixed}.mentab{table-layout:fixed}.mentab th:nth-child(2){width:62px}.mentab th:nth-child(3){width:58px}.mentab td:first-child{word-break:break-word}.codtab th:nth-child(1){width:70px}.codtab th:nth-child(3){width:54px}.codtab td:nth-child(2){word-break:break-word}.ejtab{table-layout:fixed}.ejtab td,.ejtab th{padding:7px 3px;word-break:break-word}.codtab td.cods .cod{font-size:11.5px}.codtab td,.codtab th{padding:7px 4px}details .det{padding:0 6px 10px}
.aprob textarea{width:100%;min-height:80px;border:1.5px solid var(--border);border-radius:12px;padding:10px;font:inherit;font-size:15px}
.btn{min-height:46px;padding:0 18px;border:none;border-radius:12px;font:inherit;font-weight:600;font-size:15px;cursor:pointer}
.btn.azul{background:var(--blue);color:#fff}.btn.verde{background:var(--ok);color:#fff}.btn.gris{background:#EEF2F6;color:var(--ink)}
.botones{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.com{border-top:1px solid #F0F4F8;padding:10px 0;font-size:14px}.com small{color:var(--ink2)}
.msg{font-size:13px;margin-top:8px;color:var(--ink2)}
@media print{.aprob,.volver{display:none}body{background:#fff}.card,details{box-shadow:none}details{display:block}details>.det{display:block}}
"""
NOMBRES = {"felix": "Félix", "rafael": "Rafael", "tito": "Tito", "dontiti": "Don Titi", "marco": "Marco"}
JS = """
const RID = document.body.dataset.rid;
const NOM = %s;
function _e(t){const d=document.createElement('div');d.textContent=t==null?'':String(t);return d.innerHTML;}
async function cargar(){
  try{const r=await fetch('/api/reportes',{credentials:'same-origin',cache:'no-store'}); if(!r.ok) return; const d=await r.json();
    const s=(d.estado||{})[RID]||{aprobado:[],comentarios:[]};
    const ch=document.getElementById('estado');
    if(s.aprobado.length){ch.textContent='Aprobado por '+s.aprobado.map(a=>NOM[a.usuario]||a.usuario).join(' y ');ch.classList.add('ok');}
    else{ch.textContent='En revisión';ch.classList.remove('ok');}
    const yo=s.aprobado.find(a=>a.usuario===d.yo); document.getElementById('b-aprobar').style.display=yo?'none':'';
    document.getElementById('coms').innerHTML = s.comentarios.length ? s.comentarios.map(c=>'<div class="com"><b>'+_e(NOM[c.usuario]||c.usuario)+'</b> <small>'+_e(c.fecha)+'</small><br>'+_e(c.texto)+'</div>').join('') : '<p class="nota">Todavía no hay comentarios.</p>';
  }catch(e){}
}
async function mandar(accion){
  const t=document.getElementById('txt'); const m=document.getElementById('msg');
  if(accion==='comentar' && !t.value.trim()){m.textContent='Escribe tu comentario primero.';return;}
  m.textContent='Guardando…';
  try{const r=await fetch('/api/reporte',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:RID,accion,texto:t.value})});
    const d=await r.json(); if(!r.ok) throw new Error(d.error||'No se pudo guardar');
    t.value=''; m.textContent= accion==='aprobar'?'Listo: quedó aprobado con tu nombre.':'Listo: comentario guardado.'; cargar();
  }catch(e){m.textContent='No se guardó: '+e.message;}
}
cargar();
""" % json.dumps(NOMBRES, ensure_ascii=False)

def pagina(rid, titulo, para, version, fecha, cuerpo):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(titulo)} — Titi Burger</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet"><style>{CSS}</style></head>
<body data-rid="{E(rid)}"><div class="top"><div class="wrap" style="padding-bottom:0"><a class="volver" href="../">‹ Volver al avance</a>
<h1>{E(titulo)}</h1><div class="meta"><span class="chip estado" id="estado">En revisión</span><span class="chip">Para: {E(para)}</span><span class="chip">Versión {E(version)}</span><span class="chip">{fecha_es(fecha)}</span></div></div></div>
<div class="wrap">{cuerpo}
<div class="card aprob"><h2>¿Está bien este reporte?</h2><p class="nota">Si está bien, apruébalo. Si algo no cuadra, escríbelo aquí abajo: Tito lo lee y lo corrige.</p>
<textarea id="txt" placeholder="Escribe un comentario (opcional)"></textarea>
<div class="botones"><button class="btn verde" id="b-aprobar" onclick="mandar('aprobar')">Aprobar reporte</button><button class="btn gris" onclick="mandar('comentar')">Mandar comentario</button></div>
<div class="msg" id="msg"></div><h3>Comentarios</h3><div id="coms"><p class="nota">Cargando…</p></div></div>
<p class="nota">Lo genera Tito con los datos leídos de las cajas · {datetime.now():%d-%m-%Y %H:%M}</p></div><script>{JS}</script></body></html>"""

def tabla(cols, filas, nums=()):
    th = "".join(f"<th>{E(c)}</th>" for c in cols)
    tr = "".join("<tr>" + "".join(f'<td class="{"n" if i in nums else ""}">{v}</td>' for i, v in enumerate(f)) + "</tr>" for f in filas)
    return f'<div class="scroll"><table class="tabla"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

# ======================= REPORTE 1: DIFERENCIAS =======================
def reporte_diferencias():
    L = json.loads((BASE / "noche_2026-11-26" / "propuestas.json").read_text(encoding="utf-8"))
    suc5 = [s for s in sorted({x["sucursal"] for x in L}) if s != "Cine Curto"]
    cinco = [x for x in L if x["sucursal"] != "Cine Curto"]; cc = [x for x in L if x["sucursal"] == "Cine Curto"]
    porsuc = collections.Counter(x["sucursal"] for x in cinco)
    dec = collections.Counter(x["decision"] for x in L)
    T = {
      "Presentacion de insumo": ("Cómo se compra cada insumo (paquete, caja o pieza)", "Ej. el pan: la base de Félix lo maneja por paquete de 12.", "Decidido el pan: las sucursales cuentan por pieza y la base compra por paquete de 12; el Pan JR va por pieza. Lo demás se iguala a la base de Félix."),
      "Costo/proveedor de presentacion": ("Costo o proveedor de cada presentación", "Precios de compra viejos o en $0 en la sucursal.", "Se toma el de la base de Félix al copiar."),
      "Costo de insumo": ("Costo del insumo", "Ej. Teriyaki: $246 en la sucursal contra $54.67 en la base de Félix.", "Se toma el de la base de Félix. A la base de Félix le faltan 6 costos (ya se los preguntamos)."),
      "Presentacion nueva": ("Presentaciones que solo tiene la base de Félix", "", "Llegan solas al copiar."),
      "Codigo de producto cruzado con Felix": ("Mismo código, cosa distinta", "Ej. 01007: Titi Western en la sucursal y mostaza galón en la base de Félix.", "Decidido: se ordenan los códigos (ver reporte de códigos). Ninguna descripción cambia."),
      "Configuracion de caja": ("Ajustes de la caja", "Ej. pedir autorización para cancelar.", "Pendiente: cancelaciones, lo ve Rafael con Félix."),
      "Insumo (nombre/unidad)": ("Nombre o unidad del insumo", "Ej. catsup galón contra catsup botella.", "Se toma el de la base de Félix."),
      "Insumo nuevo": ("Insumos nuevos de Félix", "Tapa 2 oz, servilleta chica, plato almeja 8x8, papas en gajo.", "Llegan solos al copiar."),
      "Insumo que Felix ya no tiene": ("Insumos que la base de Félix no tiene", "Mayonesa y aderezo de la casa 4 oz.", "Decidido: se agregan a la base de Félix."),
      "Usuarios de caja": ("Usuarios de caja", "", "No se tocan."),
      "Precio de venta": ("Precio de venta", "Titi JR: $79 en la mayoría, $69 en Villas y San Marcos.", "Decidido: $79 en todas."),
      "Modificador": ("Modificadores", "", "Se revisan con Félix."),
      "Producto (bandera)": ("Ajustes de productos", "", "Se revisan con Félix."),
    }
    c = collections.Counter(x["tema"] for x in cinco)
    porsuc_t = collections.Counter((x["tema"], x["sucursal"]) for x in cinco)
    maxsuc = {t: max(v for (tt, s), v in porsuc_t.items() if tt == t) for t in c}
    filas = []
    for tema, n in c.most_common():
        t = T.get(tema, (tema, "", "Pendiente"))
        filas.append([f"<b>{E(t[0])}</b><br><span class='nota'>{E(t[1])}</span>", num(maxsuc[tema]), E(t[2])])
    cc_t = collections.Counter(x["tema"] for x in cc)
    cuerpo = f"""
<div class="card"><p class="lead"><b>Las 5 sucursales normales son idénticas entre sí</b> (Montejano, Hacienda, Montecarlo, Villas y San Marcos: mismos 233 productos y 113 insumos). Todas tienen las mismas diferencias contra la base de Félix, unas 300 cada una. Cine Curto va aparte, con su menú de cine.</p></div>
<div class="kpis"><div class="kpi"><b>{num(len(L))}</b><span>diferencias en total contra la base de Félix</span></div>
<div class="kpi"><b style="color:var(--ok)">{num(dec['PROPUESTO'])}</b><span>Tito ya sabe cómo dejarlas igual</span></div>
<div class="kpi"><b style="color:var(--warn)">{num(dec['REVISAR'])}</b><span>necesitan el visto bueno de Félix</span></div>
<div class="kpi"><b style="color:var(--ink2)">{num(dec['NO_TOCAR'])}</b><span>no se tocan</span></div></div>
<div class="card"><h2>Qué es distinto y qué se decidió</h2><p class="nota">Contado en las 5 sucursales normales ({', '.join(E(s) for s in suc5)}). «Cuántas» = las que tiene cada sucursal (casi todas son iguales en las 5).</p>
{tabla(["Tema", "Cuántas", "Qué se hace"], filas, nums=(1,))}</div>
<div class="card"><h2>Cine Curto</h2><p>Su menú es de cine (164 productos) y no se toca. Tiene {len(cc)} diferencias propias:</p>
<ul><li><b>{cc_t.get('Codigo de insumo cruzado con Felix', 0)} insumos con código cruzado:</b> por ejemplo, su carne es el 001034, que en la base de Félix es el insumo «C». Se cuidan en su lista aparte antes de copiar.</li>
<li><b>{cc_t.get('Forma de pago sin clave SAT', 0)} formas de pago sin clave del SAT:</b> hay que ponérsela para facturar bien.</li>
<li>Sus 4 usuarios de caja no se tocan.</li></ul></div>
<div class="card"><h2>Lo que nunca se toca</h2><p>Usuarios y contraseñas, ventas pasadas, folios e impresoras de cada sucursal. Nada se borra sin respaldo y nada cambia sin el visto bueno de Félix y de Rafael. En diciembre no se toca ninguna caja.</p></div>
<div class="card"><h2>Lo que sigue</h2>
<div class="paso"><div class="num">1</div><div>Félix contesta lo que falta en «Preguntas para Félix»: cancelaciones y 6 costos.</div></div>
<div class="paso"><div class="num">2</div><div>Se respalda la base de Félix y se agregan la mayonesa y el aderezo.</div></div>
<div class="paso"><div class="num">3</div><div>Se arma una base de prueba con los códigos ordenados y se cala en una máquina, como pidió Félix.</div></div>
<div class="paso"><div class="num">4</div><div>Félix y Rafael revisan la base completa. Desde enero se copia a las sucursales, una por una.</div></div></div>
<p class="nota">Las diferencias se leyeron el 26 de noviembre. La base de Félix ha seguido cambiando: el 27 de noviembre ya tenía 108 productos (antes 95). Antes de copiar se vuelven a leer todas.</p>"""
    return pagina("diferencias", "Diferencias de cada sucursal contra la base de Félix", "Rafael y Félix", "2", "2026-11-27", cuerpo)

# ======================= REPORTE 2: CODIGOS =======================
CAN_N = {"CAJA": "Caja", "DIDI": "DiDi", "UBER": "Uber", "RAPPI": "Rappi", "APPS": "Todas las apps"}
FAM_N = {"HAMB": "Hamburguesas", "COMBO": "Combos y promociones", "EXTRA": "Extras y acompañantes", "BEBIDA": "Bebidas", "BONELESS": "Boneless", "MODIF": "Modificadores", "MERMA": "Merma de sucursal"}
def tags(x):
    t = ""
    if x.get("repetido"): t += '<span class="tag t-rep">Repetido</span>'
    if x.get("lineas", 1) == 0 and x.get("fam") not in ("MODIF", "MERMA"): t += '<span class="tag t-cero">0 ventas</span>'
    if x.get("ortografia"): t += f'<span class="tag t-ort">Ortografía: {E(x["ortografia"])}</span>'
    return t
def reporte_codigos():
    P = json.loads((DAT / "codigos_propuesta.json").read_text(encoding="utf-8"))
    F, X, C = P["sucursales"], P["felix"], P["curto"]
    cambian = sum(1 for x in F if x["nuevo"] != x["cod"])
    rep = sum(1 for x in F if x["repetido"]); cero = sum(1 for x in F if x["lineas"] == 0); ort = sum(1 for x in F if x["ortografia"])
    # ejemplo: un producto en todos los canales
    by = collections.defaultdict(dict)
    for x in F:
        if x["fam"] in ("HAMB", "COMBO"): by[(x["fam"], x["nuevo"][2:])][x["canal"]] = x
    ej = []
    for k in [("HAMB", "001"), ("HAMB", "007"), ("COMBO", "006")]:
        d = by.get(k, {}); base = d.get("CAJA")
        if base: ej.append([E(base["desc"])] + [f'<span class="cod nuevo">{E(d[c]["nuevo"])}</span><br><span class="cod nota">hoy {E(d[c]["cod"])}</span>' if c in d else "—" for c in ("CAJA", "DIDI", "UBER", "RAPPI")])
    ej = [[f[0]] + [v.split("<br>")[0] for v in f[1:]] for f in ej]
    secciones = ""
    for can in ("CAJA", "DIDI", "UBER", "RAPPI", "APPS"):
        xs = [x for x in F if x["canal"] == can]
        if not xs: continue
        filas = []
        for fam in ("HAMB", "COMBO", "EXTRA", "BEBIDA", "BONELESS", "MODIF", "MERMA"):
            fx_ = sorted([x for x in xs if x["fam"] == fam], key=lambda x: (x["nuevo"], x["cod"]))
            if fx_: filas.append(f'<tr class="fam"><td colspan="3">{E(FAM_N[fam])}</td></tr>')
            for x in fx_:
                filas.append(f'<tr><td class="cods"><span class="cod nuevo">{E(x["nuevo"])}</span><br><span class="cod nota">hoy {E(x["cod"])}</span></td><td>{E(x["desc"])}<div>{tags(x)}</div></td><td class="n">{num(x["lineas"])}</td></tr>')
        secciones += f'<details><summary>{E(CAN_N[can])} · {len(xs)} productos</summary><div class="det"><div class="scroll"><table class="tabla codtab"><thead><tr><th>Código</th><th>Descripción (no cambia)</th><th style="text-align:right">Ventas</th></tr></thead><tbody>{"".join(filas)}</tbody></table></div></div></details>'
    fx = [[f'<span class="cod nuevo">{E(x["nuevo"])}</span><br><span class="cod nota">hoy {E(x["cod"])}</span>', E(x["desc"]),
           (f'<span class="tag t-choca">En sucursales es: {E(x["en_sucursal"])}</span>' if x["choca"] else ('<span class="tag t-ok">Igual en sucursales</span>' if x["en_sucursal"] == "igual" else ""))] for x in X]
    cpro = [x for x in C if x["como"] == "Propio de Cine Curto"]
    cfil = [[f'<span class="cod nuevo">{E(x["nuevo"])}</span><br><span class="cod nota">hoy {E(x["cod"])}</span>', E(x["desc"]), num(x["lineas"])] for x in sorted(cpro, key=lambda x: x["nuevo"])]
    choques = sum(1 for x in X if x["choca"])
    cuerpo = f"""
<div class="card"><p class="lead"><b>Propuesta: cada código dice de qué canal es, de qué familia y qué producto es.</b> Así la Titi Clásica es 01001 en caja, 21001 en DiDi, 31001 en Uber y 41001 en Rappi. <b>Ninguna descripción cambia</b>, como pidió Félix: solo cambia el número.</p></div>
<div class="card"><h2>Cómo se lee un código</h2>
<div class="regla"><div><div class="d">0</div><div class="l">Canal<br>0 Caja · 2 DiDi · 3 Uber · 4 Rappi · 6 Todas las apps · 7 Cine Curto · 9 Surtido de cocina</div></div>
<div><div class="d">1</div><div class="l">Familia<br>1 Hamburguesas · 2 Combos · 3 Extras · 4 Bebidas · 5 Boneless</div></div>
<div><div class="d">001</div><div class="l">Producto<br>El mismo número en todos los canales</div></div></div>
<p class="nota">Los modificadores (100xxx) y las mermas (101xxx) ya están en orden y se quedan igual.</p>
<h3>Ejemplo: el mismo producto en todos los canales</h3>{tabla(["Producto", "Caja", "DiDi", "Uber", "Rappi"], ej).replace('class="tabla"', 'class="tabla ejtab"')}</div>
<div class="kpis"><div class="kpi"><b>{cambian}</b><span>de {len(F)} productos cambian de número</span></div>
<div class="kpi"><b style="color:var(--bad)">{rep}</b><span>están repetidos (mismo producto con 2 o 3 códigos)</span></div>
<div class="kpi"><b style="color:var(--warn)">{cero}</b><span>nunca se han vendido: ¿se dan de baja?</span></div>
<div class="kpi"><b style="color:var(--blue)">{ort}</b><span>tienen faltas de ortografía (solo sugerencia)</span></div></div>
<div class="card"><h2>Menú de las 5 sucursales, código por código</h2><p class="nota">Ventas = renglones vendidos en Montejano desde 2021. Las faltas de ortografía solo se marcan: la descripción no se toca sin que Félix diga.</p>{secciones}</div>
<div class="card"><h2>Base de Félix: el surtido de cocina pasa al bloque 9</h2><p>En la base de Félix el grupo 01 es «Surtido a sucursal». Hoy {choques} de esos códigos chocan con hamburguesas y combos de las sucursales. Propuesta: surtido 90xxx, verdura 93xxx y bebidas de surtido 94xxx. La descripción no cambia.</p>
<details><summary>Ver los {len(X)} productos de la base de Félix</summary><div class="det">{tabla(["Código", "Descripción (no cambia) y nota"], [[a, b + "<div>" + c + "</div>"] for a, b, c in fx]).replace('class="tabla"', 'class="tabla codtab"')}</div></details></div>
<div class="card"><h2>Cine Curto</h2><p>{sum(1 for x in C if x['como']=='Igual que en las sucursales')} de sus {len(C)} productos son los mismos del menú normal y toman ese código. {len(cpro)} son propios de Cine Curto y van al bloque 7.</p>
<p class="nota">Ojo: Cine Curto tiene precios de cine. Hay que decidir si sus productos iguales llevan su propio precio.</p>
<details><summary>Ver los {len(cpro)} productos propios de Cine Curto</summary><div class="det">{tabla(["Código", "Descripción (no cambia)", "Ventas"], cfil, nums=(2,)).replace('class="tabla"', 'class="tabla codtab"')}</div></details></div>
<div class="card"><h2>Por qué así</h2><ul>
<li><b>Se lee solo:</b> con ver el número sabes si es de caja o de una app, y de qué familia.</li>
<li><b>No rompe nada:</b> los pedidos de apps se capturan a mano, así que ninguna conexión depende del código.</li>
<li><b>Se pierde poco:</b> la historia vieja por código queda con el número viejo; los reportes por nombre siguen igual.</li>
<li><b>Se prueba antes:</b> primero en una base de prueba en otra máquina, como pidió Félix.</li></ul></div>"""
    return pagina("codigos", "Códigos de productos: cómo están y cómo quedarían", "Rafael y Félix", "1", "2026-11-27", cuerpo)

# ======================= REPORTE 3: APPS =======================
def reporte_apps():
    P = json.loads((DAT / "codigos_propuesta.json").read_text(encoding="utf-8"))
    F = P["sucursales"]; ap = json.loads((DAT / "apps_30dias.json").read_text(encoding="utf-8"))
    hist = collections.Counter()
    for x in F: hist[x["canal"]] += x["lineas"]
    tot = sum(hist.values())
    fil = [[E(CAN_N[c]), num(hist[c]), f"{100*hist[c]/tot:.0f}%"] for c in ("CAJA", "DIDI", "UBER", "RAPPI", "APPS") if hist[c]]
    m = ap["Montejano"]
    cuerpo = f"""
<div class="card"><p class="lead"><b>Hoy los pedidos de Uber, DiDi y Rappi llegan a la tablet de cada app, se preparan, se entregan y alguien los captura después en Soft Restaurant.</b> Proponemos capturarlos en el momento y que Tito cuadre todos los días lo capturado contra las apps. Sin comprar nada y sin contratar a nadie.</p></div>
<div class="kpis"><div class="kpi"><b>{num(m['DIDI'])}</b><span>renglones de DiDi en Montejano, últimos 30 días</span></div>
<div class="kpi"><b>{num(m['UBER'])}</b><span>renglones de Uber, últimos 30 días</span></div>
<div class="kpi"><b>{num(m['RAPPI'])}</b><span>renglones de Rappi, últimos 30 días</span></div></div>
<div class="card"><h2>Cuánto pesan las apps</h2><p class="nota">Renglones vendidos en Montejano desde 2021, por canal.</p>{tabla(["Canal", "Renglones", "Del total"], fil, nums=(1, 2))}</div>
<div class="card"><h2>El problema de capturar después</h2><ul>
<li><b>Se olvidan pedidos:</b> lo que no se captura no descuenta inventario y el corte no cuadra.</li>
<li><b>Se captura tarde:</b> ya vimos tickets que llegan horas después a la base (Montejano), y eso descuadra los reportes del día.</li>
<li><b>No hay quien lo revise:</b> nadie compara lo que dice la app contra lo que quedó en la caja.</li></ul></div>
<div class="card"><h2>Propuesta, sin costo</h2>
<div class="paso"><div class="num">1</div><div><b>Capturar en el momento, con un botón por app.</b> En la caja, un grupo DiDi, uno Uber y uno Rappi, cada uno solo con los productos de esa app. Con los códigos nuevos queda natural: 2xxxx DiDi, 3xxxx Uber, 4xxxx Rappi. Regla: el pedido se captura antes de entregarlo al repartidor.</div></div>
<div class="paso"><div class="num">2</div><div><b>Precio de la app en la caja.</b> Que cada producto de app tenga el precio que cobra la app, para que el corte diga lo que de verdad entra. La comisión (Uber 30%, DiDi 20%, Rappi 27%, más IVA y retenciones, según lo que tenemos registrado) la descuenta Tito en el reporte.</div></div>
<div class="paso"><div class="num">3</div><div><b>Cuadre diario por Tito.</b> Cada mañana Tito compara lo capturado en Soft Restaurant contra lo que reporta cada app y le avisa a Rafael qué pedido faltó y en qué sucursal. Para DiDi ya tenemos acceso a su portal de tiendas; para Uber y Rappi hace falta el acceso a sus portales.</div></div>
<div class="paso"><div class="num">4</div><div><b>Limpiar el menú de apps.</b> Hay productos de apps repetidos o que nunca se han vendido (ver el reporte de códigos). Menos botones, menos errores.</div></div></div>
<div class="card"><h2>Por decidir</h2><ul><li>¿Quién captura en cada sucursal: el cajero o quien recibe la tablet?</li>
<li>¿Nos pasan el acceso a los portales de Uber y Rappi para el cuadre diario?</li>
<li>Cine Curto no tiene ninguna venta de apps en Soft Restaurant en los últimos 30 días. ¿No vende por apps, o no las está capturando?</li></ul></div>"""
    return pagina("apps", "Pedidos de apps: cómo capturarlos mejor sin gastar", "Rafael y Félix", "1", "2026-11-27", cuerpo)

# ======================= REPORTE 4: MENU CON PRECIOS =======================
def reporte_menu():
    P = json.loads((DAT / "codigos_propuesta.json").read_text(encoding="utf-8"))
    PR = json.loads((DAT / "precios_27nov.json").read_text(encoding="utf-8"))
    F = P["sucursales"]; cinco = ["Montejano", "Hacienda", "Montecarlo", "Villas", "San Marcos"]
    cdesc = {}
    for x in P["curto"]:
        if x["como"] == "Igual que en las sucursales": cdesc[x["nuevo"]] = x["cod"]
    def precio(x):
        ps = {s: PR.get(s, {}).get(x["cod"]) for s in cinco}
        vals = {v for v in ps.values() if v is not None}
        if not vals: return "—", ""
        if len(vals) == 1:
            v = vals.pop(); return (f"${v:,.0f}" if v else "$0"), ('<span class="tag t-cero">En $0</span>' if not v else "")
        base = max(vals, key=lambda v: sum(1 for s in cinco if ps[s] == v))
        dif = ", ".join(f"{s} ${ps[s]:,.0f}" for s in cinco if ps[s] is not None and ps[s] != base)
        return f"${base:,.0f}", f'<span class="tag t-rep">Distinto: {E(dif)}</span>'
    secciones = ""; total = 0; ceros = 0; dist = 0
    for can in ("CAJA", "DIDI", "UBER", "RAPPI", "APPS"):
        xs = [x for x in F if x["canal"] == can and x["fam"] in ("HAMB", "COMBO", "EXTRA", "BEBIDA", "BONELESS")]
        if not xs: continue
        filas = []
        for fam in ("HAMB", "COMBO", "EXTRA", "BEBIDA", "BONELESS"):
            fx_ = sorted([x for x in xs if x["fam"] == fam], key=lambda x: (x["nuevo"], x["cod"]))
            if fx_: filas.append(f'<tr class="fam"><td colspan="3">{E(FAM_N[fam])}</td></tr>')
            for x in fx_:
                pr, nota = precio(x); total += 1; ceros += "En $0" in nota; dist += "Distinto" in nota
                cc = cdesc.get(x["nuevo"]); pc = PR.get("Cine Curto", {}).get(cc) if cc else None
                if pc is not None and f"${pc:,.0f}" != pr: nota += f'<span class="tag t-ort">Cine Curto ${pc:,.0f}</span>'
                if x["repetido"]: nota += '<span class="tag t-rep">Repetido</span>'
                if x["lineas"] == 0: nota += '<span class="tag t-cero">0 ventas</span>'
                filas.append(f'<tr><td>{E(x["desc"])}<div class="nota cod">{E(x["nuevo"])}</div><div>{nota}</div></td><td class="n">{pr}</td><td class="n">{num(x["lineas"])}</td></tr>')
        secciones += f'<details{" open" if can == "CAJA" else ""}><summary>{E(CAN_N[can])} · {len(xs)} productos</summary><div class="det"><div class="scroll"><table class="tabla mentab"><thead><tr><th>Producto y código nuevo</th><th style="text-align:right">Precio</th><th style="text-align:right">Ventas</th></tr></thead><tbody>{"".join(filas)}</tbody></table></div></div></details>'
    nf = len(PR.get("Félix", {}))
    cuerpo = f"""
<div class="card"><p class="lead"><b>Este es el menú que hoy venden las 5 sucursales, con su precio.</b> Es el punto de partida para armar el menú desde cero en tu base: marca qué se queda, qué se quita y qué precio cambia.</p></div>
<div class="kpis"><div class="kpi"><b>{total}</b><span>productos de venta (sin modificadores ni mermas)</span></div>
<div class="kpi"><b style="color:var(--bad)">{dist}</b><span>con precio distinto entre sucursales</span></div>
<div class="kpi"><b style="color:var(--warn)">{ceros}</b><span>en $0</span></div>
<div class="kpi"><b>{nf}</b><span>productos tiene hoy tu base (sigue creciendo)</span></div></div>
<div class="card"><h2>El menú, por canal</h2><p class="nota">Precio = el de las 5 sucursales normales. Si alguna cobra distinto, sale en rojo. «Cine Curto» en azul = cobra otro precio allá. Ventas = renglones vendidos en Montejano desde 2021. Abajo de cada producto va su código nuevo propuesto.</p>{secciones}</div>
<div class="card"><h2>Cómo lo revisas</h2>
<div class="paso"><div class="num">1</div><div>Revisa la caja primero: hamburguesas, combos, extras, bebidas y boneless.</div></div>
<div class="paso"><div class="num">2</div><div>Si algo se quita o cambia de precio, escríbelo en los comentarios de abajo (ej. «quitar COMBO PAREJA repetido», «Titi JR $79»).</div></div>
<div class="paso"><div class="num">3</div><div>Luego las apps. Los productos con 0 ventas son candidatos a quitarse.</div></div></div>
<p class="nota">Precios leídos de las 7 cajas el 27 de noviembre de 2026 por la noche.</p>"""
    return pagina("menu", "Menú completo con precios, para armar tu base", "Félix y Rafael", "1", "2026-11-27", cuerpo)

REPORTES = [("diferencias", "Diferencias de cada sucursal contra la base de Félix", reporte_diferencias),
            ("codigos", "Códigos de productos: cómo están y cómo quedarían", reporte_codigos),
            ("apps", "Pedidos de apps: cómo capturarlos mejor sin gastar", reporte_apps),
            ("menu", "Menú completo con precios, para armar tu base", reporte_menu)]
if __name__ == "__main__":
    idx = []
    for rid, tit, fn in REPORTES:
        (OUT / f"{rid}.html").write_text(fn(), encoding="utf-8")
        idx.append({"id": rid, "titulo": tit, "para": "Félix y Rafael" if rid == "menu" else "Rafael y Félix", "fecha": "2026-11-27"})
    (BASE / "reportes.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print("ok:", [r["id"] for r in idx])
