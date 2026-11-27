#!/usr/bin/env python3
"""Desglose Doble Carne por sucursal + por mesero (reporte 16)."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SUCS = {
    "12764":"FOVISSTE","13056":"MONTECARLO","22871":"SAN MARCOS",
    "22980":"HACIENDA DEL RÍO","23032":"CURTO","26983":"VILLAS DEL REY",
}

def login(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

def buscar_doble_carne(texto):
    """De un reporte de productos, extrae DOBLE CARNE + COMBO DOBLE CARNE."""
    lines = texto.split("\n")
    result = {"doble_carne": 0, "combo_doble_carne": 0}
    for i, line in enumerate(lines):
        l = line.strip().upper()
        if "TITI DOBLE CARNE" in l and "COMBO" not in l:
            m = re.search(r"([\d,]+)\.\d+\s+\$", l)
            if m: result["doble_carne"] += int(float(m.group(1).replace(",","")))
        elif "COMBO DOBLE CARNE" in l:
            m = re.search(r"([\d,]+)\.\d+\s+\$", l)
            if m: result["combo_doble_carne"] += int(float(m.group(1).replace(",","")))
    return result

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1200})
    page = ctx.new_page()
    login(page)

    # Por sucursal, junio y julio
    resultados = {"por_sucursal": {}}
    for periodo, (f_ini, f_fin) in [("junio", ("01/06/2026","30/06/2026")), ("julio_hasta_hoy", ("01/07/2026","11/07/2026"))]:
        print(f"\n=== {periodo.upper()} ===", flush=True)
        for suc_id, suc_nombre in SUCS.items():
            page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2500)
            page.locator('#FechaInicial').fill(f_ini)
            page.locator('#FechaFinal').fill(f_fin)
            page.evaluate("""() => {
                const c = document.querySelector('#NumElementosTop');
                if (c) {
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(c, '1500');
                    c.dispatchEvent(new Event('input', {bubbles: true}));
                    c.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }""")
            # solo esta sucursal
            page.evaluate("""(id) => {
                const sel = document.querySelector('#ListaEmpresas');
                if (sel) {
                    for (const opt of sel.options) opt.selected = (opt.value === id);
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    if (window.jQuery) window.jQuery(sel).trigger('change');
                }
            }""", suc_id)
            page.wait_for_timeout(1200)
            page.locator('#ActualizarReporte').first.click()
            page.wait_for_load_state("networkidle", timeout=90000)
            page.wait_for_timeout(15000)

            text = page.evaluate("() => document.body.innerText")
            dc = buscar_doble_carne(text)
            key = f"{periodo}_{suc_nombre}"
            resultados["por_sucursal"][key] = dc
            print(f"  {suc_nombre:20s} DobleCarne:{dc['doble_carne']:>4}  Combo:{dc['combo_doble_carne']:>4}  TOTAL:{dc['doble_carne']+dc['combo_doble_carne']:>4}", flush=True)

    Path("/home/tito/.openclaw/data/doble_carne_por_sucursal.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    browser.close()
print("\nGuardado /home/tito/.openclaw/data/doble_carne_por_sucursal.json")
