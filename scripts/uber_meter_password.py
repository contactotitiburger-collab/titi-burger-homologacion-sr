#!/usr/bin/env python3
"""Continuar login Uber — meter contraseña con las cookies guardadas."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/uber_merchants/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_uber")
STATE = Path("/home/tito/.openclaw/credentials/uber_merchants/state.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
        storage_state=str(STATE) if STATE.exists() else None,
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    page.goto("https://merchants.ubereats.com/manager", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(5000)
    page.screenshot(path=str(SCREEN / "step_password.png"), full_page=True)
    print(f"URL: {page.url}", flush=True)

    # ¿Ya está adentro?
    if "manager" in page.url and "auth.uber.com" not in page.url:
        print("Ya adentro directo", flush=True)
        ctx.storage_state(path=str(STATE))
        page.screenshot(path=str(SCREEN / "dashboard.png"), full_page=True)
        (SCREEN / "dashboard.html").write_text(page.content())
        browser.close()
        exit(0)

    # Ver si está pidiendo password
    if page.locator('input[type="password"]').count() > 0:
        pwd = page.locator('input[type="password"]').first
        pwd.click()
        pwd.type(creds["password"], delay=100)
        page.wait_for_timeout(2500)
        # Click Siguiente
        try:
            page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=10000)
            page.locator("#forward-button").click()
        except:
            page.locator("button:has-text('Siguiente'), button[type='submit']").first.click()
        print("Password metida, click Siguiente", flush=True)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(8000)
        page.screenshot(path=str(SCREEN / "post_password.png"), full_page=True)
        (SCREEN / "post_password.html").write_text(page.content())
        print(f"URL: {page.url}", flush=True)
        print(f"Title: {page.title()}", flush=True)

    # Guardar estado
    ctx.storage_state(path=str(STATE))
    print("Sesión guardada", flush=True)

    browser.close()
