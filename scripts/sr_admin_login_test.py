#!/usr/bin/env python3
"""Prueba de login a SR Admin (admin.softrestaurant.com) y screenshot inicial."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")
SCREEN_DIR.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    print(f"Ir a: {CREDS['panel']}", flush=True)
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.screenshot(path=str(SCREEN_DIR / "01_landing.png"), full_page=True)
    print(f"URL landing: {page.url}", flush=True)
    print(f"Title: {page.title()}", flush=True)

    # Guardar HTML para inspección
    (SCREEN_DIR / "01_landing.html").write_text(page.content())
    print(f"HTML guardado en {SCREEN_DIR / '01_landing.html'}", flush=True)

    browser.close()
print("OK", flush=True)
