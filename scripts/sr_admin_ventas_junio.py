#!/usr/bin/env python3
"""Consulta ventas de junio 2026 seleccionando las 6 sucursales."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

# IDs vistos en el dropdown
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
    ctx = browser.new_context(viewport={"width": 1800, "height": 1200})
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

    # Cambiar mes a Junio (val=6)
    mes_select = page.locator('select').filter(has_text="Julio").first
    # buscar el select de mes por presencia de opción "Julio"
    all_selects = page.query_selector_all("select")
    for s in all_selects:
        opts = s.query_selector_all("option")
        vals = [o.get_attribute("value") for o in opts]
        if "7" in vals and "12" in vals:
            s.select_option("6")
            print("Mes → Junio", flush=True)
            break

    # Seleccionar las 6 empresas (multi-select o checkboxes)
    # Usar JS para seleccionar todas las opciones en el select de empresas
    result = page.evaluate("""() => {
        const selects = document.querySelectorAll('select');
        for (const sel of selects) {
            const vals = [...sel.options].map(o => o.value);
            if (vals.includes('12764') && vals.includes('26983')) {
                // Este es el select de empresas
                for (const opt of sel.options) {
                    opt.selected = true;
                }
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                return 'seleccionadas ' + sel.options.length + ' opciones';
            }
        }
        return 'no encontró el select de empresas';
    }""")
    print(f"Empresas: {result}", flush=True)
    page.wait_for_timeout(1500)

    # Consultar
    page.locator('text="Consultar"').first.click()
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(6000)
    page.screenshot(path=str(SCREEN_DIR / "11_junio_6_sucursales.png"), full_page=True)
    (SCREEN_DIR / "11_junio_6_sucursales.html").write_text(page.content())
    print(f"Consulta hecha. URL: {page.url}", flush=True)

    # Intentar extraer tablas de datos
    tables = page.eval_on_selector_all(
        "table",
        "els => els.map(t => t.innerText)"
    )
    for i, t in enumerate(tables):
        print(f"\n--- Tabla {i+1} ---\n{t}", flush=True)

    browser.close()
print("OK", flush=True)
