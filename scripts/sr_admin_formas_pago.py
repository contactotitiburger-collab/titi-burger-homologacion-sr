#!/usr/bin/env python3
"""Consulta ventas por formas de pago desde el dashboard con rango de mayo."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

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

    # Ir al Dashboard (analytics)
    page.goto("https://admin.softrestaurant.com/analytics/Settings/Dashboard", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)
    page.screenshot(path=str(SCREEN_DIR / "20_dashboard_analytics.png"), full_page=True)
    (SCREEN_DIR / "20_dashboard_analytics.html").write_text(page.content())
    print(f"Dashboard analytics URL: {page.url}", flush=True)

    # También intentar el dashboard base
    page.goto("https://admin.softrestaurant.com/Dashboard", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(5000)
    page.screenshot(path=str(SCREEN_DIR / "21_dashboard_base.png"), full_page=True)
    (SCREEN_DIR / "21_dashboard_base.html").write_text(page.content())
    print(f"Dashboard base URL: {page.url}", flush=True)

    browser.close()
print("OK", flush=True)
