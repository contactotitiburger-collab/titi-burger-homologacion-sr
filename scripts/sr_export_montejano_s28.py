#!/usr/bin/env python3
"""Export Excel completo de productos - Montejano (12764) S28 (6-12 jul, corte a 13).
Reporte 7. Baja el xlsx (sin cap de top-N) y lo guarda para sumar hamburguesas."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
DEST = Path("/home/tito/.openclaw/data/nomina/sr_prod_montejano_s28.xlsx")
SUC = "12764"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width":1800,"height":1400}, accept_downloads=True)
    page = ctx.new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2000)
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('#FechaInicial').fill('06/07/2026')
    page.locator('#FechaFinal').fill('13/07/2026')
    page.evaluate("""() => {const c=document.querySelector('#NumElementosTop');
        if(c){const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
        s.call(c,'2000');c.dispatchEvent(new Event('input',{bubbles:true}));c.dispatchEvent(new Event('change',{bubbles:true}));}}""")
    page.evaluate("""(id)=>{const sel=document.querySelector('#ListaEmpresas');
        if(sel){for(const o of sel.options)o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));if(window.jQuery)window.jQuery(sel).val([id]).trigger('change');}}""", SUC)
    page.wait_for_timeout(1500)
    # Consultar con hasta 3 reintentos hasta que rendericen resultados
    got=False
    for intento in range(1,4):
        try:
            page.locator('#ActualizarReporte, button:has-text("Consultar")').first.click(force=True)
        except Exception as e:
            print(f"  intento {intento}: click falló {str(e)[:80]}", flush=True)
        try:
            page.wait_for_selector("table#TablaReporte tbody tr td, table tbody tr td.sorting_1, table tbody tr:has(td:nth-child(3))", timeout=70000)
            got=True; break
        except Exception:
            print(f"  intento {intento}: sin resultados aún, reintento...", flush=True)
            page.wait_for_timeout(4000)
    page.wait_for_timeout(6000)
    print("resultados renderizaron:", got, flush=True)
    # guardar tabla en texto SIEMPRE (respaldo)
    tabs = page.eval_on_selector_all("table", "els => els.map(t=>t.innerText)")
    Path("/home/tito/.openclaw/data/nomina/sr_prod_montejano_s28.txt").write_text("\n\n===TABLE===\n\n".join(tabs))
    # intentar export Excel completo por ID
    try:
        with page.expect_download(timeout=120000) as di:
            page.locator('a#ExportarExcel, #ExportarExcel').first.click(force=True)
        di.value.save_as(str(DEST))
        print(f"OK Excel descargado: {DEST} ({DEST.stat().st_size} bytes)")
    except Exception as e:
        print("export Excel falló:", str(e)[:150])
    page.screenshot(path="/home/tito/.openclaw/data/nomina/sr_s28_estado.png", full_page=True)
    b.close()
