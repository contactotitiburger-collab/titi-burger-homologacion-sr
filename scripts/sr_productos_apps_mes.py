#!/usr/bin/env python3
"""Reporte 7 productos: suma TOTAL y CANTIDAD de SKUs con sufijo UBER/DIDI/RAPPI vs total, para un rango."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
IDS = ["12764","13056","22871","22980","23032","26983"]
INI = sys.argv[1]   # dd/mm/yyyy
FIN = sys.argv[2]
TAG = sys.argv[3] if len(sys.argv) > 3 else "mes"
OUT = Path(f"/home/tito/.openclaw/data/sr_productos_apps_{TAG}.json")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_context(viewport={"width":1800,"height":2200}).new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2500)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    # cantidad alto para traer todos los SKUs
    page.evaluate("""() => { const c=document.querySelector('input[type=number]'); if(c){c.value='5000'; c.dispatchEvent(new Event('input',{bubbles:true})); c.dispatchEvent(new Event('change',{bubbles:true}));} }""")
    # fechas
    for sel,val in (("#FechaInicial",INI),("#FechaFinal",FIN)):
        page.evaluate("""([s,v])=>{const el=document.querySelector(s); if(!el)return; el.value=v;
            el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); el.dispatchEvent(new Event('blur',{bubbles:true}));}""",[sel,val])
    # empresas
    page.evaluate("""(ids)=>{const sel=document.querySelector('#ListaEmpresas'); if(!sel)return;
        for(const o of sel.options) o.selected=ids.includes(o.value);
        sel.dispatchEvent(new Event('change',{bubbles:true})); if(window.jQuery) window.jQuery(sel).trigger('change');}""",IDS)
    page.wait_for_timeout(800)
    try: page.locator('#ActualizarReporte').first.click()
    except: pass
    page.wait_for_load_state("networkidle", timeout=120000)
    page.wait_for_timeout(20000)
    # elegir 100 por pagina si existe
    try:
        page.select_option("select", "100"); page.wait_for_timeout(4000)
    except: pass

    # Confirmar rango que el reporte realmente usó
    header = ""
    for line in page.evaluate("()=>document.body.innerText").split("\n"):
        if "Productos más vendidos del" in line:
            header = line.strip()
    # extraer filas de la tabla principal: CLAVE DESC CANTIDAD PRECIO IMPORTE TOTAL
    rows = page.evaluate("""() => {
        const out=[];
        for (const tr of document.querySelectorAll('table tr')) {
            const tds=[...tr.querySelectorAll('td')].map(td=>td.innerText.trim());
            if (tds.length>=6) out.push(tds);
        }
        return out;
    }""")
    b.close()

def num(s):
    return float(re.sub(r"[^0-9.]", "", s)) if s and re.search(r"\d", s) else 0.0

app_rows=[]; app_cant=0.0; app_total=0.0
grand_cant=0.0; grand_total=0.0; page_cant=0.0; page_total=0.0
for r in rows:
    desc = r[1] if len(r)>1 else ""
    clave = r[0]
    cant = num(r[2]) if len(r)>2 else 0
    total = num(r[-1])
    if not clave and not desc:  # total rows (empty clave/desc)
        # could be page total or grand total
        if grand_total==0 and page_total>0:
            grand_cant=cant; grand_total=total
        else:
            page_cant=cant; page_total=total;
        continue
    U = desc.upper()
    if re.search(r"\b(UBER|DIDI|RAPPI)\b", U) or U.endswith("UBER") or U.endswith("DIDI") or U.endswith("RAPPI"):
        app_rows.append({"clave":clave,"desc":desc,"cant":cant,"total":total})
        app_cant+=cant; app_total+=total

# separar por app
by_app={}
for a in app_rows:
    for k in ("UBER","DIDI","RAPPI"):
        if k in a["desc"].upper():
            d=by_app.setdefault(k,{"cant":0.0,"total":0.0,"skus":0})
            d["cant"]+=a["cant"]; d["total"]+=a["total"]; d["skus"]+=1
res={"rango_pedido":[INI,FIN],"header_reporte":header,
     "app_cant_unidades":app_cant,"app_total_pesos":app_total,
     "by_app":by_app,"n_app_skus":len(app_rows),
     "app_rows":app_rows}
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2))
print("HEADER:",header)
print("N app SKUs:",len(app_rows),"| app unidades:",app_cant,"| app pesos:",app_total)
print("BY APP:",json.dumps(by_app,ensure_ascii=False))
print("Ejemplos:",[a['desc'] for a in app_rows[:15]])
