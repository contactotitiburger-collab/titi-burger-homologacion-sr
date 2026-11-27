#!/usr/bin/env python3
"""Exporta el Excel de PRODUCTOS MÁS VENDIDOS (reporte 7) para un rango y lo guarda.
Sirve para sumar productos con sufijo UBER/DIDI/RAPPI (app) vs el resto (física)."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
DL = Path("/home/tito/.openclaw/data/productos_export")
DL.mkdir(parents=True, exist_ok=True)

INI = sys.argv[1] if len(sys.argv) > 1 else "01/08/2026"
FIN = sys.argv[2] if len(sys.argv) > 2 else "31/08/2026"
TAG = sys.argv[3] if len(sys.argv) > 3 else "ago2026"
IDS = ["12764", "13056", "22871", "22980", "23032", "26983"]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1800, "height": 1400}, accept_downloads=True)
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
    page.evaluate("""([ini,fin])=>{
        const f1=document.querySelector('#FechaInicial');
        const f2=document.querySelector('#FechaFinal');
        if(f1){f1.value=ini; f1.dispatchEvent(new Event('change',{bubbles:true}));}
        if(f2){f2.value=fin; f2.dispatchEvent(new Event('change',{bubbles:true}));}
        const cant=document.querySelector('input[type=number]');
        if(cant){cant.value='1'; cant.dispatchEvent(new Event('change',{bubbles:true}));}
    }""", [INI, FIN])
    page.wait_for_timeout(500)
    page.evaluate("""(ids)=>{const sel=document.querySelector('#ListaEmpresas');
        if(!sel) return;
        for(const o of sel.options) o.selected=ids.includes(o.value);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery) window.jQuery(sel).trigger('change');}""", IDS)
    page.wait_for_timeout(300)
    # cerrar cualquier datepicker abierto haciendo click en un área neutra
    page.evaluate("() => { document.body.click(); }")
    page.wait_for_timeout(300)
    try: page.locator('#ActualizarReporte').first.click()
    except Exception: pass
    page.wait_for_timeout(1000)
    try: page.wait_for_selector("#ExportarExcel", state="visible", timeout=180000)
    except Exception: pass
    page.wait_for_timeout(6000)

    dest = DL / f"productos_{TAG}.xlsx"
    try:
        with page.expect_download(timeout=60000) as di:
            page.locator('#ExportarExcel').first.click()
        di.value.save_as(str(dest))
        print("DESCARGADO:", dest, flush=True)
    except Exception as e:
        print("No pude descargar Excel:", e, flush=True)
        txt = page.evaluate("() => { const ts=[...document.querySelectorAll('table')]; return ts.map(t=>t.innerText).join('\\n=====\\n'); }")
        (DL / f"productos_{TAG}.txt").write_text(txt)
        print("Guardé texto en su lugar.", flush=True)
    b.close()
