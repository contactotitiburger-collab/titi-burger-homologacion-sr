#!/usr/bin/env python3
"""Dos reportes diarios de PRODUCTOS por sucursal, estilo del reporte de ventas.

  A) Hamburguesas por sucursal (grupo TITI BURGER, sin boneless) — # reales y por tipo.
  B) Todos los productos por sucursal — unidades reales por categoría + top productos.

Fuente: reporte 7 "Productos más vendidos" de la nube de Soft Restaurant (las 6 carretas),
con NumElementosTop=1500 y lectura por la API del DataTable (todas las filas, no top-10).
Clasificación por catálogo maestro clave->grupo (data/catalogo_productos.json).
Rango: [fecha, fecha+1) por el corte de SR.  Cantidades = unidades reales vendidas.
"""
import json, sys, argparse, subprocess, math, re, time
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT   = Path("/home/tito/.openclaw/data/reportes_diarios")
OUT.mkdir(parents=True, exist_ok=True)
LOG   = Path("/home/tito/.openclaw/logs/reporte_productos.log")
RAFAEL_WA  = "+5216861445614"
DON_TITI_WA = "+5216861131003"

SUCS = {  # id nube -> nombre (mismo orden/nombres que el reporte de ventas)
    "12764": "L Montejano", "13056": "Montecarlo", "22980": "Hacienda del Río",
    "22871": "San Marcos", "23032": "Cine Curto", "26983": "Villas del Rey",
}
COLORES = [(226,74,62),(243,156,18),(39,174,96),(41,128,185),(142,68,173),(26,188,156)]
# Colores por tipo de hamburguesa (consistentes entre reportes)
COLOR_TIPO = {
    "Clásica":(226,74,62), "Doble Queso":(243,156,18), "Tocino":(142,68,173),
    "Doble Carne":(192,57,43), "California":(39,174,96), "Western":(211,84,0),
    "Hawaiana":(26,188,156), "Pechuga de Pollo":(41,128,185), "Low Carb":(52,73,94),
    "Otras / Promos":(149,165,166),
}
COLOR_CAT = {  # categorías para el reporte de todos los productos
    "Hamburguesas":(226,74,62), "Bebidas":(41,128,185), "Papas":(243,156,18),
    "Boneless":(142,68,173), "Extras":(39,174,96), "Otros":(149,165,166),
}


def log(msg):
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea, flush=True)
    with LOG.open("a") as f:
        f.write(linea + "\n")


# ---------- clasificación (por DESCRIPCIÓN de la nube; las claves se reciclan entre carretas) ----------
_DRINKS = ["JAMAICA","COCA","PEPSI","DR PEPPER","ROOT BEER","AGUA","MANZANITA","7 UP","7UP",
           "SQUIRT","CRUSH","MIRINDA","REFRESCO","SPRITE","FANTA","BOING","JARRITO","LIMONAD"]

def _es_bebida(d):
    if d == "TE": return True
    if "A.SODAS" in d or "SODAS O AGUA" in d: return True
    return any(k in d for k in _DRINKS)

def es_hamburguesa(clave, desc):
    d = (desc or "").upper().strip()
    # exclusiones duras
    if "BONEL" in d: return False           # boneless (incl. "BONELES")
    if "NACHO" in d or "HOT DOG" in d: return False
    if _es_bebida(d): return False
    if "ARO" in d and "CEBOLLA" in d: return False
    if "ADEREZO" in d or "SALSA" in d or "CATSUP" in d: return False
    if "EXTRA" in d and "TITI" not in d and "COMBO" not in d: return False  # modificadores
    if "PAPA" in d and "COMBO" not in d and "TITI" not in d: return False   # papas solas
    # señales de hamburguesa
    if "TITI" in d: return True
    if "HAMBURG" in d: return True          # "HAMBURGUSA SLIDE"
    if "COMBO" in d and any(k in d for k in ["TOCINO","CLASIC","DOBLE","CALIFORNIA","WESTER",
                                             "HAWAIANA","POLLO","PECHUGA","NIGHT"]): return True
    if "PROMOCION" in d and ("DUO" in d or "CLASIC" in d or "99" in d): return True
    return False

def categoria(clave, desc):
    d = (desc or "").upper().strip()
    if es_hamburguesa(clave, desc): return "Hamburguesas"
    if "BONEL" in d: return "Boneless"
    if _es_bebida(d): return "Bebidas"
    if "PAPA" in d or ("ARO" in d and "CEBOLLA" in d): return "Papas"
    if any(k in d for k in ["NACHO","HOT DOG","EXTRA","ADEREZO","SALSA","QUESO","PIÑA","CARNE","TOCINO"]):
        return "Extras"
    return "Otros"

def tipo_burger(clave, desc):
    d = (desc or "").upper()
    if "LOW CARB" in d: return "Low Carb"
    if "DOBLE QUESO" in d: return "Doble Queso"
    if "DOBLE CARNE" in d: return "Doble Carne"
    if "TOCINO" in d: return "Tocino"
    if "CALIFORNIA" in d: return "California"
    if "WESTER" in d: return "Western"
    if "HAWAIANA" in d: return "Hawaiana"
    if "PECHUGA" in d or "POLLO" in d: return "Pechuga de Pollo"
    if "CLASIC" in d or "CLASIA" in d: return "Clásica"
    return "Otras / Promos"


# ---------- scraping reporte 7 ----------
def login(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2500)

def _num(v):
    if v is None: return 0.0
    if isinstance(v,(int,float)): return float(v)
    s = re.sub(r"<[^>]+>","",str(v))
    return float(re.sub(r"[^\d.\-]","",s)) if re.search(r"\d",s) else 0.0

def _clean(v):
    return re.sub(r"<[^>]+>","",str(v)).strip() if v is not None else ""

def scrape_suc(page, suc_id, f_ini, f_fin):
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.locator('#FechaInicial').fill(f_ini)
    page.locator('#FechaFinal').fill(f_fin)
    page.keyboard.press("Escape"); page.wait_for_timeout(400)
    page.evaluate("""(id)=>{const sel=document.querySelector('#ListaEmpresas');
        if(sel){for(const o of sel.options)o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery)window.jQuery(sel).trigger('change');}}""", suc_id)
    page.wait_for_timeout(800)
    page.evaluate("""(v)=>{const c=document.querySelector('#NumElementosTop');
        const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
        s.call(c,String(v));
        for(const ev of ['input','change','blur','keyup']) c.dispatchEvent(new Event(ev,{bubbles:true}));
        if(window.jQuery) window.jQuery(c).val(String(v)).trigger('change');}""", 1500)
    page.wait_for_timeout(400)
    page.locator('#ActualizarReporte').first.click()
    tbl = f"reporte_datatable_{suc_id}"
    for _ in range(60):
        res = page.evaluate("""(tid)=>{
            const t=document.getElementById(tid);
            if(!t||!window.jQuery||!window.jQuery.fn.dataTable)return null;
            try{const dt=window.jQuery('#'+tid).DataTable();
                if(dt.rows().count()<1)return null;
                const hdr=[...t.querySelectorAll('thead th')].map(th=>th.innerText.trim());
                const rows=dt.rows().data().toArray().map(r=>Array.isArray(r)?r:Object.values(r));
                return {hdr,rows};
            }catch(e){return null;}
        }""", tbl)
        if res and res.get("rows"):
            break
        page.wait_for_timeout(3000)
    else:
        return []
    hdr = [h.upper() for h in res["hdr"]]
    def col(*names):
        for j,h in enumerate(hdr):
            if any(n in h for n in names): return j
        return None
    ci, cd = col("CLAVE"), col("DESCRIP")
    cc, ctot = col("CANTIDAD"), col("TOTAL")
    items = []
    for r in res["rows"]:
        if ci is None or ci>=len(r): continue
        clave = _clean(r[ci])
        if not clave or clave.upper().startswith("TOTAL"): continue
        items.append({"clave":clave,
                      "desc":_clean(r[cd]) if cd is not None else "",
                      "cantidad":_num(r[cc]) if cc is not None else 0,
                      "total":_num(r[ctot]) if ctot is not None else 0})
    return items


def sacar_todo(fecha, fecha_fin):
    datos = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=True)
        page = nav.new_context(viewport={"width":1800,"height":1300}).new_page()
        login(page)
        for sid, nombre in SUCS.items():
            try:
                items = scrape_suc(page, sid, fecha, fecha_fin)
            except Exception as e:
                log(f"  {nombre}: ERROR scraping ({e})"); items = []
            datos[nombre] = items
            tot_u = sum(i["cantidad"] for i in items)
            tot_v = sum(i["total"] for i in items)
            log(f"  {nombre}: {len(items)} productos · {tot_u:.0f} unidades · ${tot_v:,.0f}")
        nav.close()
    return datos


# ---------- dibujo ----------
def fuente(tam, negrita=False):
    base = "/usr/share/fonts/truetype/dejavu/DejaVuSans"
    try: return ImageFont.truetype(f"{base}-Bold.ttf" if negrita else f"{base}.ttf", tam)
    except OSError: return ImageFont.load_default()

def _pastel(dr, items, cx, cy, r, umbral=18):
    total = sum(v for v,_ in items)
    ang = -90.0
    for valor, color in items:
        barrido = valor/total*360 if total else 0
        dr.pieslice([cx-r,cy-r,cx+r,cy+r], ang, ang+barrido, fill=color, outline="white", width=3)
        if barrido >= umbral:
            med = math.radians(ang+barrido/2)
            tx, ty = cx+math.cos(med)*r*0.62, cy+math.sin(med)*r*0.62
            etq = f"{valor/total*100:.0f}%"
            for ox,oy in ((-2,0),(2,0),(0,-2),(0,2)):
                dr.text((tx+ox,ty+oy), etq, font=fuente(max(18,int(r*0.12)),True), fill="black", anchor="mm")
            dr.text((tx,ty), etq, font=fuente(max(18,int(r*0.12)),True), fill="white", anchor="mm")
        ang += barrido

def _fecha_sub(fecha):
    d = datetime.strptime(fecha, "%d/%m/%Y")
    dias  = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto",
             "septiembre","octubre","noviembre","diciembre"]
    return f"{dias[d.weekday()]} {d.day} de {meses[d.month-1]} de {d.year}"

def dibujar_hamburguesas(por_suc, por_tipo, fecha, ruta):
    """por_suc: {carreta: n_burgers} ; por_tipo: {tipo: n} (global)."""
    datos = sorted([(n,c) for n,c in por_suc.items() if c>0], key=lambda x:-x[1])
    total = sum(c for _,c in datos)
    tipos = sorted([(t,n) for t,n in por_tipo.items() if n>0], key=lambda x:-x[1])
    W, H = 1100, 1580
    img = Image.new("RGB",(W,H),(248,249,250)); dr = ImageDraw.Draw(img)
    dr.rectangle([0,0,W,155], fill=(30,36,46))
    dr.text((W//2,55),"Hamburguesas por sucursal",font=fuente(44,True),fill="white",anchor="mm")
    dr.text((W//2,110),_fecha_sub(fecha),font=fuente(26),fill=(170,178,189),anchor="mm")
    # dos pasteles: por carreta (izq) y por tipo (der)
    r, cy, cxL, cxR = 175, 400, 300, 800
    dr.text((cxL,190),"Por carreta",font=fuente(24,True),fill=(90,96,105),anchor="mm")
    dr.text((cxR,190),"Por tipo",font=fuente(24,True),fill=(90,96,105),anchor="mm")
    _pastel(dr, [(c,COLORES[i%len(COLORES)]) for i,(n,c) in enumerate(datos)], cxL, cy, r)
    _pastel(dr, [(n,COLOR_TIPO.get(t,(150,150,150))) for t,n in tipos], cxR, cy, r)
    # leyenda de tipos (der, debajo)
    ly = cy + r + 26
    for t,n in tipos:
        pct = n/total*100 if total else 0
        dr.rectangle([600,ly+4,620,ly+24], fill=COLOR_TIPO.get(t,(150,150,150)))
        dr.text((630,ly),f"{t}",font=fuente(20,True),fill=(45,50,58))
        dr.text((1000,ly+2),f"{n:.0f}  ({pct:.0f}%)",font=fuente(19),fill=(70,76,86),anchor="ra")
        ly += 29
    y = max(830, ly+20)
    # tabla por carreta
    cca, cvt, cdt = 70, 560, 1030
    dr.text((cca,y),"Carreta",font=fuente(20,True),fill=(120,128,138))
    dr.text((cvt,y),"Hamburguesas",font=fuente(20,True),fill=(120,128,138),anchor="ra")
    dr.text((cdt,y),"Del total",font=fuente(20,True),fill=(120,128,138),anchor="ra")
    y += 10; dr.line([cca,y+28,cdt,y+28],fill=(210,215,222),width=1); y += 42
    for i,(nombre,c) in enumerate(datos):
        dr.ellipse([cca,y+8,cca+22,y+30],fill=COLORES[i%len(COLORES)])
        dr.text((cca+32,y+6),nombre,font=fuente(27,True),fill=(35,40,48))
        dr.text((cvt,y+8),f"{c:.0f}",font=fuente(26,True),fill=(70,76,86),anchor="ra")
        pct = c/total*100 if total else 0
        dr.text((cdt,y+8),f"{pct:.1f}%",font=fuente(25),fill=(70,76,86),anchor="ra")
        y += 62
    y += 10; dr.line([cca,y,cdt,y],fill=(180,185,195),width=2); y += 28
    dr.text((cca,y),"TOTAL",font=fuente(38,True),fill=(35,40,48))
    dr.text((cvt,y+4),f"{total:.0f}",font=fuente(38,True),fill=(39,150,90),anchor="ra")
    img.save(ruta, quality=92)
    return total

def dibujar_productos(por_suc_u, por_cat, top_prod, fecha, ruta):
    """por_suc_u: {carreta: unidades} ; por_cat: {categoria: unidades} ; top_prod: [(desc,unid)]."""
    datos = sorted([(n,u) for n,u in por_suc_u.items() if u>0], key=lambda x:-x[1])
    total = sum(u for _,u in datos)
    cats = sorted([(c,u) for c,u in por_cat.items() if u>0], key=lambda x:-x[1])
    W, H = 1100, 1780
    img = Image.new("RGB",(W,H),(248,249,250)); dr = ImageDraw.Draw(img)
    dr.rectangle([0,0,W,155], fill=(30,36,46))
    dr.text((W//2,55),"Productos vendidos por sucursal",font=fuente(42,True),fill="white",anchor="mm")
    dr.text((W//2,110),_fecha_sub(fecha),font=fuente(26),fill=(170,178,189),anchor="mm")
    r, cy, cxL, cxR = 175, 400, 300, 800
    dr.text((cxL,190),"Por carreta",font=fuente(24,True),fill=(90,96,105),anchor="mm")
    dr.text((cxR,190),"Por categoría",font=fuente(24,True),fill=(90,96,105),anchor="mm")
    _pastel(dr, [(u,COLORES[i%len(COLORES)]) for i,(n,u) in enumerate(datos)], cxL, cy, r)
    _pastel(dr, [(u,COLOR_CAT.get(c,(150,150,150))) for c,u in cats], cxR, cy, r)
    ly = cy + r + 26
    for c,u in cats:
        pct = u/total*100 if total else 0
        dr.rectangle([600,ly+4,620,ly+24], fill=COLOR_CAT.get(c,(150,150,150)))
        dr.text((630,ly),f"{c}",font=fuente(20,True),fill=(45,50,58))
        dr.text((1000,ly+2),f"{u:.0f}  ({pct:.0f}%)",font=fuente(19),fill=(70,76,86),anchor="ra")
        ly += 29
    y = max(830, ly+20)
    cca, cvt, cdt = 70, 560, 1030
    dr.text((cca,y),"Carreta",font=fuente(20,True),fill=(120,128,138))
    dr.text((cvt,y),"Unidades",font=fuente(20,True),fill=(120,128,138),anchor="ra")
    dr.text((cdt,y),"Del total",font=fuente(20,True),fill=(120,128,138),anchor="ra")
    y += 10; dr.line([cca,y+28,cdt,y+28],fill=(210,215,222),width=1); y += 42
    for i,(nombre,u) in enumerate(datos):
        dr.ellipse([cca,y+8,cca+22,y+30],fill=COLORES[i%len(COLORES)])
        dr.text((cca+32,y+6),nombre,font=fuente(27,True),fill=(35,40,48))
        dr.text((cvt,y+8),f"{u:.0f}",font=fuente(26,True),fill=(70,76,86),anchor="ra")
        pct = u/total*100 if total else 0
        dr.text((cdt,y+8),f"{pct:.1f}%",font=fuente(25),fill=(70,76,86),anchor="ra")
        y += 62
    y += 10; dr.line([cca,y,cdt,y],fill=(180,185,195),width=2); y += 28
    dr.text((cca,y),"TOTAL",font=fuente(38,True),fill=(35,40,48))
    dr.text((cvt,y+4),f"{total:.0f}",font=fuente(38,True),fill=(39,150,90),anchor="ra")
    y += 70
    # top productos
    dr.text((cca,y),"Top 10 productos (unidades)",font=fuente(22,True),fill=(90,96,105)); y += 40
    for i,(desc,u) in enumerate(top_prod[:10],1):
        dr.text((cca,y),f"{i}.",font=fuente(22,True),fill=(120,128,138))
        dr.text((cca+40,y),desc[:38],font=fuente(22),fill=(45,50,58))
        dr.text((cdt,y),f"{u:.0f}",font=fuente(22,True),fill=(70,76,86),anchor="ra")
        y += 34
    img.save(ruta, quality=92)
    return total


def mandar_wa(numero, mensaje, imagen=None, intentos=3):
    cmd = ["openclaw","message","send","--channel","whatsapp","--target",numero,"--message",mensaje]
    if imagen: cmd += ["--media", str(Path(imagen).resolve())]
    for i in range(1,intentos+1):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            log(f"  enviado a {numero}"); return True
        log(f"  intento {i} falló a {numero}: {r.stderr.strip()[:150]}")
        if i < intentos: time.sleep(5)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    ap.add_argument("--enviar", choices=["rafael","ambos","ninguno"], default="ninguno")
    a = ap.parse_args()
    fecha = a.fecha or (datetime.now()-timedelta(days=1)).strftime("%d/%m/%Y")
    d = datetime.strptime(fecha, "%d/%m/%Y")
    fecha_fin = (d+timedelta(days=1)).strftime("%d/%m/%Y")
    log(f"=== Reporte productos {fecha} (rango [{fecha},{fecha_fin})) ===")

    datos = sacar_todo(fecha, fecha_fin)

    # Agregaciones
    ham_por_suc, ham_por_tipo = {}, {}
    prod_por_suc, prod_por_cat = {}, {}
    top_global = {}
    for carreta, items in datos.items():
        nb = 0.0
        for it in items:
            cat = categoria(it["clave"], it["desc"])
            prod_por_cat[cat] = prod_por_cat.get(cat,0) + it["cantidad"]
            top_global[it["desc"] or it["clave"]] = top_global.get(it["desc"] or it["clave"],0) + it["cantidad"]
            if cat == "Hamburguesas":
                nb += it["cantidad"]
                t = tipo_burger(it["clave"], it["desc"])
                ham_por_tipo[t] = ham_por_tipo.get(t,0) + it["cantidad"]
        ham_por_suc[carreta] = nb
        prod_por_suc[carreta] = sum(it["cantidad"] for it in items)

    top_prod = sorted(top_global.items(), key=lambda x:-x[1])

    # Validación en log (cantidades reales)
    log(f"  TOTAL hamburguesas: {sum(ham_por_suc.values()):.0f}")
    log(f"  por tipo: " + ", ".join(f"{t}={n:.0f}" for t,n in sorted(ham_por_tipo.items(),key=lambda x:-x[1])))
    log(f"  TOTAL unidades (todos): {sum(prod_por_suc.values()):.0f}")

    rutaA = OUT / f"hamburguesas_{d:%Y-%m-%d}.jpg"
    rutaB = OUT / f"productos_{d:%Y-%m-%d}.jpg"
    dibujar_hamburguesas(ham_por_suc, ham_por_tipo, fecha, rutaA)
    dibujar_productos(prod_por_suc, prod_por_cat, top_prod, fecha, rutaB)
    (OUT / f"productos_{d:%Y-%m-%d}.json").write_text(json.dumps(
        {"fecha":fecha,"ham_por_suc":ham_por_suc,"ham_por_tipo":ham_por_tipo,
         "prod_por_suc":prod_por_suc,"prod_por_cat":prod_por_cat,
         "detalle":{k:v for k,v in datos.items()}}, ensure_ascii=False, indent=1))
    log(f"  imágenes: {rutaA} · {rutaB}")

    if a.enviar in ("rafael","ambos"):
        mandar_wa(RAFAEL_WA, f"Borrador 1/2 — Hamburguesas por sucursal ({fecha}).", rutaA)
        mandar_wa(RAFAEL_WA, f"Borrador 2/2 — Todos los productos por sucursal ({fecha}).", rutaB)
    return 0


if __name__ == "__main__":
    sys.exit(main())
