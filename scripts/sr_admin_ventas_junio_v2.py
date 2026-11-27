#!/usr/bin/env python3
"""Consulta ventas junio 2026 — asegurar las 6 sucursales y desglose por nombre."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

EMPRESAS = {
    "12764": "FOVISSTE",
    "13056": "MONTECARLO",
    "22871": "SAN MARCOS",
    "22980": "HACIENDA DEL RÍO",
    "23032": "CURTO",
    "26983": "VILLAS DEL REY",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400})
    page = ctx.new_page()

    # Login
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    # Ventas mensuales
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/3", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Cambiar a Junio
    all_selects = page.query_selector_all("select")
    for s in all_selects:
        opts = s.query_selector_all("option")
        vals = [o.get_attribute("value") for o in opts]
        if "7" in vals and "12" in vals:
            s.select_option("6")
            break

    # Seleccionar las 6 empresas — con dispatch de eventos correctos
    result = page.evaluate("""(ids) => {
        const selects = document.querySelectorAll('select');
        for (const sel of selects) {
            const vals = [...sel.options].map(o => o.value);
            if (vals.includes('12764')) {
                let count = 0;
                for (const opt of sel.options) {
                    if (ids.includes(opt.value)) {
                        opt.selected = true;
                        count++;
                    } else {
                        opt.selected = false;
                    }
                }
                // Trigger multiple events
                sel.dispatchEvent(new Event('input', {bubbles: true}));
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                // Si tiene jQuery, también triggerearlo
                if (window.jQuery) { window.jQuery(sel).trigger('change'); }
                return {ok: true, count: count, selected_vals: [...sel.selectedOptions].map(o => o.value)};
            }
        }
        return {ok: false, error: 'no select'};
    }""", list(EMPRESAS.keys()))
    print(f"Empresas selected: {result}", flush=True)
    page.wait_for_timeout(2000)

    # Consultar
    page.locator('text="Consultar"').first.click()
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(8000)
    page.screenshot(path=str(SCREEN_DIR / "12_junio_final.png"), full_page=True)
    (SCREEN_DIR / "12_junio_final.html").write_text(page.content())

    # Extraer datos por sucursal: buscar tabs con nombre + tabla asociada
    html = page.content()
    # Buscar bloques por nombre de sucursal
    for name in EMPRESAS.values():
        # patrón: nombre seguido de tabla con números
        m = re.search(rf"{re.escape(name)}[\s\S]{{0,3000}}?(\d[\d,]*)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)", html)
        if m:
            tickets, prom, sub, desc, imp, total = m.groups()
            print(f"{name}: {tickets} tickets, promedio ${prom}, TOTAL ${total}", flush=True)
        else:
            print(f"{name}: no match", flush=True)

    # También intentar el total general
    m = re.search(r"Empresas seleccionadas:\s*(\d+)", html)
    if m:
        print(f"\nEmpresas en total mostrado: {m.group(1)}", flush=True)

    browser.close()
print("OK", flush=True)
