#!/usr/bin/env python3
"""Consulta ventas mensuales — ver todas las empresas disponibles y datos."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
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

    # Abrir el dropdown de empresas
    empresa_dropdown = page.locator('text="Seleccionar empresas"').first
    try:
        empresa_dropdown.locator('..').click()
    except:
        pass
    page.wait_for_timeout(1500)
    page.screenshot(path=str(SCREEN_DIR / "09_empresas_dropdown.png"), full_page=True)

    # Extraer del HTML todas las opciones de empresa disponibles
    html = page.content()
    (SCREEN_DIR / "09_empresas_dropdown.html").write_text(html)

    # Buscar opciones directas
    opciones = page.eval_on_selector_all(
        "select option, li[role='option'], div[role='option']",
        "els => els.map(e => ({tag: e.tagName, text: e.textContent.trim(), val: e.value || e.dataset.value || ''}))"
    )
    print("Opciones dropdown:", flush=True)
    for o in opciones[:30]:
        if o["text"]:
            print(f"  {o}", flush=True)

    # Intentar clickear "Consultar" con lo que esté seleccionado (Fovissste)
    page.locator('text="Consultar"').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(4000)
    page.screenshot(path=str(SCREEN_DIR / "10_ventas_consulta_resultado.png"), full_page=True)
    (SCREEN_DIR / "10_ventas_consulta_resultado.html").write_text(page.content())
    print(f"Consulta hecha. URL: {page.url}", flush=True)

    browser.close()
print("OK", flush=True)
