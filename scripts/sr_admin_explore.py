#!/usr/bin/env python3
"""Explora SR Admin: sucursales registradas y reportes de venta."""
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
    print(f"Login OK, dashboard en {page.url}", flush=True)

    # 1. Grupo de Empresas — ver sucursales
    page.goto("https://admin.softrestaurant.com/AgrupadorSistema", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(SCREEN_DIR / "04_grupo_empresas.png"), full_page=True)
    (SCREEN_DIR / "04_grupo_empresas.html").write_text(page.content())
    print("Grupo Empresas capturado", flush=True)

    # 2. Reportes de ventas
    page.goto("https://admin.softrestaurant.com/Analytics/ReportesVentas", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(SCREEN_DIR / "05_reportes.png"), full_page=True)
    (SCREEN_DIR / "05_reportes.html").write_text(page.content())
    print(f"Reportes capturado. URL: {page.url}", flush=True)

    browser.close()
print("OK", flush=True)
