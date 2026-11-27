#!/usr/bin/env python3
"""Abre reporte 'Ventas mensuales' directamente por URL y captura datos."""
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
    page.wait_for_timeout(4000)
    print(f"Ventas mensuales URL: {page.url}", flush=True)
    page.screenshot(path=str(SCREEN_DIR / "06_ventas_mensuales.png"), full_page=True)
    (SCREEN_DIR / "06_ventas_mensuales.html").write_text(page.content())

    # Ventas por periodo
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/1", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)
    page.screenshot(path=str(SCREEN_DIR / "07_ventas_periodo.png"), full_page=True)

    # Ventas diarias
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/6", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)
    page.screenshot(path=str(SCREEN_DIR / "08_ventas_diarias.png"), full_page=True)

    browser.close()
print("OK", flush=True)
