#!/usr/bin/env python3
"""Productos vendidos (reporte /7) de L Montejano (FOVISSTE, id 12764) -> JSON, para el punto de equilibrio.
El reporte trae TOP-N productos (NumElementosTop, máx 1500) y los muestra en un DataTable paginado de 10.
Fix: NumElementosTop=1500 y se leen TODAS las filas por la API del DataTable.
Rango: junio 2026 (último mes normal antes del incendio).
"""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT_DIR = Path("/home/tito/.openclaw/data/pe_montejano")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUC_ID = "12764"
DESDE, HASTA = "01/06/2026", "30/06/2026"
out = OUT_DIR / "productos_montejano_jun2026.json"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width":1800,"height":1400})
    page = ctx.new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2500)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('#FechaInicial').fill(DESDE)
    page.locator('#FechaFinal').fill(HASTA)
    page.keyboard.press("Escape"); page.wait_for_timeout(500)
    # 1) elegir sucursal PRIMERO (elegirla resetea NumElementosTop a 10)
    page.evaluate("""(id)=>{const sel=document.querySelector('#ListaEmpresas');
        if(sel){for(const o of sel.options)o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery)window.jQuery(sel).trigger('change');}}""", SUC_ID)
    page.wait_for_timeout(800)
    # 2) top a 1500 (máx válido) DESPUÉS, con todos los eventos + jQuery (el input está oculto)
    top = page.evaluate("""(v)=>{const c=document.querySelector('#NumElementosTop');
        const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
        s.call(c,String(v));
        for(const ev of ['input','change','blur','keyup']) c.dispatchEvent(new Event(ev,{bubbles:true}));
        if(window.jQuery) window.jQuery(c).val(String(v)).trigger('change');
        return c.value;}""", 1500)
    print(f"  NumElementosTop = {top}", flush=True)
    page.wait_for_timeout(400)
    page.locator('#ActualizarReporte').first.click()

    # poll: esperar a que el DataTable tenga filas
    tbl_id = f"reporte_datatable_{SUC_ID}"
    data = None
    for i in range(60):
        res = page.evaluate("""(tid)=>{
            const t=document.getElementById(tid);
            if(!t||!window.jQuery||!window.jQuery.fn.dataTable)return null;
            try{const dt=window.jQuery('#'+tid).DataTable();
                const n=dt.rows().count(); if(n<1)return null;
                const hdr=[...t.querySelectorAll('thead th')].map(th=>th.innerText.trim());
                const rows=dt.rows().data().toArray().map(r=>Array.isArray(r)?r:Object.values(r));
                return {hdr, rows};
            }catch(e){return null;}
        }""", tbl_id)
        if res and res.get("rows"):
            data = res
            print(f"  DataTable listo en ~{i*3}s con {len(res['rows'])} filas", flush=True)
            break
        page.wait_for_timeout(3000)
    b.close()

def num(v):
    if v is None: return 0.0
    if isinstance(v,(int,float)): return float(v)
    s=re.sub(r"<[^>]+>","",str(v))
    return float(re.sub(r"[^\d.\-]","",s)) if re.search(r"\d",s) else 0.0
def clean(v):
    return re.sub(r"<[^>]+>","",str(v)).strip() if v is not None else ""

productos=[]
if data:
    hdr=[h.upper() for h in data["hdr"]]
    def col(*names):
        for j,h in enumerate(hdr):
            if any(n in h for n in names): return j
        return None
    ci=col("CLAVE"); cd=col("DESCRIP"); cc=col("CANTIDAD")
    cp=col("PRECIO"); cimp=col("IMPORTE SIN","IMPORTE"); ctot=col("TOTAL")
    for r in data["rows"]:
        if ci is None or ci>=len(r) or not clean(r[ci]): continue
        clave=clean(r[ci])
        if clave.upper().startswith("TOTAL"): continue
        productos.append({
            "clave":clave,
            "descripcion":clean(r[cd]) if cd is not None else "",
            "cantidad":num(r[cc]) if cc is not None else 0,
            "precio_promedio":num(r[cp]) if cp is not None else 0,
            "importe_sin_imp":num(r[cimp]) if cimp is not None else 0,
            "total":num(r[ctot]) if ctot is not None else 0,
        })

out.write_text(json.dumps({"sucursal":"L Montejano (FOVISSTE)","id":SUC_ID,
    "periodo":f"{DESDE} a {HASTA}","n_productos":len(productos),
    "productos":productos}, ensure_ascii=False, indent=1))
print(f"OK {len(productos)} productos -> {out}")
for pr in sorted(productos,key=lambda x:-x['importe_sin_imp'])[:8]:
    print(f"  {pr['clave']:6} {pr['descripcion'][:30]:30} cant={pr['cantidad']:.0f} precio=${pr['precio_promedio']:.2f}")
