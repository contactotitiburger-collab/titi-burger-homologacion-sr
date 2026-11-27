#!/usr/bin/env python3
"""Reporte 13 (Ventas por estación) con rango mayo 2026 y las 6 empresas."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400})
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/13", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Setear fechas mayo
    page.evaluate("""() => {
        document.querySelector('#FechaInicial').value = '01/05/2026';
        document.querySelector('#FechaFinal').value = '31/05/2026';
    }""")
    page.wait_for_timeout(500)

    # Seleccionar las 6 empresas
    page.evaluate("""(ids) => {
        const sel = document.querySelector('#ListaEmpresas');
        for (const opt of sel.options) opt.selected = ids.includes(opt.value);
        sel.dispatchEvent(new Event('change', {bubbles: true}));
        if (window.jQuery) window.jQuery(sel).trigger('change');
    }""", IDS)
    page.wait_for_timeout(1000)

    # Consultar
    page.locator('#ActualizarReporte').click()
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(8000)
    page.screenshot(path=str(SCREEN_DIR / "23_r13_mayo.png"), full_page=True)
    (SCREEN_DIR / "23_r13_mayo.html").write_text(page.content())

    # Extraer tablas
    tables = page.eval_on_selector_all("table", "els => els.map(t => t.innerText)")
    for i, t in enumerate(tables):
        if len(t.strip()) > 30:
            print(f"\n--- Tabla {i+1} ---\n{t[:2000]}", flush=True)

    browser.close()
