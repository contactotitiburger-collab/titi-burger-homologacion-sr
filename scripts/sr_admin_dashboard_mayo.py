#!/usr/bin/env python3
"""Dashboard base con rango mayo 2026 y las 6 empresas — buscar widgets de servicio/forma de pago."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 2200})
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Ir al dashboard
    page.goto("https://admin.softrestaurant.com/Dashboard", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)

    # Cambiar fechas y empresas — dependerá de UI
    # Setear los inputs
    page.evaluate("""() => {
        const f1 = document.querySelector('#FechaInicial, input[name="FechaInicial"]');
        const f2 = document.querySelector('#FechaFinal, input[name="FechaFinal"]');
        if (f1) f1.value = '01/05/2026';
        if (f2) f2.value = '31/05/2026';
    }""")

    try:
        page.evaluate("""(ids) => {
            for (const sel of document.querySelectorAll('select')) {
                try {
                    const vals = [...sel.options].map(o => o.value);
                    if (vals.includes('12764')) {
                        for (const opt of sel.options) opt.selected = ids.includes(opt.value);
                        try { sel.dispatchEvent(new Event('change', {bubbles: true})); } catch (e) {}
                        return;
                    }
                } catch (e) {}
            }
        }""", IDS)
    except Exception as e:
        print(f"select err: {e}", flush=True)
    page.wait_for_timeout(1000)

    # Botón actualizar
    try:
        actualizar = page.locator('#Actualizar, button:has-text("Actualizar")').first
        actualizar.click()
    except Exception as e:
        print(f"btn err: {e}", flush=True)
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(8000)
    page.screenshot(path=str(SCREEN_DIR / "24_dashboard_mayo.png"), full_page=True)
    (SCREEN_DIR / "24_dashboard_mayo.html").write_text(page.content())
    print(f"URL: {page.url}", flush=True)

    # Intercept: capturar todas las llamadas ajax que el dashboard hizo
    # También extraer todos los TEXTOS de la página que contengan las palabras clave
    text_all = page.evaluate("() => document.body.innerText")
    # buscar "Ventas por" y variantes
    import re
    for match in re.finditer(r"(Ventas por [^\n]{0,80})", text_all):
        print("SECTION:", match.group(1), flush=True)

    browser.close()
