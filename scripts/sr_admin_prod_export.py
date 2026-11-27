#!/usr/bin/env python3
"""Reporte 7 mayo — descargar Excel completo con TODOS los productos."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")
DOWNLOAD_DIR = Path("/home/tito/.openclaw/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400}, accept_downloads=True)
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Fechas + cantidad + empresas — usando el mismo enfoque que ya funciona parcialmente
    page.locator('#FechaInicial').fill('01/05/2026')
    page.locator('#FechaFinal').fill('31/05/2026')

    # Cantidad al máximo
    page.evaluate("""() => {
        const c = document.querySelector('#NumElementosTop');
        if (c) {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(c, '1500');
            c.dispatchEvent(new Event('input', {bubbles: true}));
            c.dispatchEvent(new Event('change', {bubbles: true}));
        }
    }""")

    # Empresas
    page.evaluate("""(ids) => {
        try {
            const sel = document.querySelector('#ListaEmpresas');
            if (sel) {
                for (const opt of sel.options) opt.selected = ids.includes(opt.value);
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
            }
        } catch(e){}
    }""", IDS)
    page.wait_for_timeout(1000)

    # Consultar
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=120000)
    page.wait_for_timeout(30000)

    # Ahora click en botón EXCEL
    with page.expect_download(timeout=120000) as download_info:
        page.locator('a:has-text("EXCEL"), button:has-text("EXCEL"), text="EXCEL"').first.click()
    download = download_info.value
    dest = DOWNLOAD_DIR / f"productos_mayo_2026.xlsx"
    download.save_as(str(dest))
    print(f"Descargado: {dest} ({dest.stat().st_size} bytes)", flush=True)

    browser.close()
