#!/usr/bin/env python3
"""Login DiDi Food Manager por la URL alternativa."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")

URL = "https://www.didi-food.com/es-MX/manager"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
        timezone_id="America/Tijuana",
    )
    ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-MX','es']});
    """)
    page = ctx.new_page()

    page.goto(URL, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(SCREEN / "didi_url2_landing.png"), full_page=True)

    # Rellenar teléfono y contraseña
    tel_input = page.locator('input[placeholder*="teléfono" i], input[placeholder*="Número" i]').first
    tel_input.click(); tel_input.type(creds["user_phone"], delay=60)
    print(f"Teléfono: {creds['user_phone']}", flush=True)

    pwd_input = page.locator('input[type="password"]').first
    pwd_input.click(); pwd_input.type(creds["password"], delay=60)
    print("Password rellenada", flush=True)
    page.wait_for_timeout(1500)

    # Click en botón
    page.locator("div.button.actived, div.button:has-text('Iniciar')").first.click()
    print("Click submit", flush=True)

    page.wait_for_timeout(8000)
    page.screenshot(path=str(SCREEN / "didi_url2_after.png"), full_page=True)
    print(f"URL post login: {page.url}", flush=True)

    # Click en Aceptar del modal de rol
    try:
        page.locator("button:has-text('Aceptar'), div:has-text('Aceptar')").last.click()
        print("Click Aceptar", flush=True)
    except:
        pass
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(6000)
    page.screenshot(path=str(SCREEN / "didi_url2_dashboard.png"), full_page=True)
    (SCREEN / "didi_url2_dashboard.html").write_text(page.content())
    print(f"URL dashboard: {page.url}", flush=True)
    print(f"Title: {page.title()}", flush=True)

    # Guardar cookies
    cookies = ctx.cookies()
    Path("/home/tito/.openclaw/credentials/didi_restaurantes/cookies.json").write_text(json.dumps(cookies))
    print(f"Cookies: {len(cookies)}", flush=True)

    browser.close()
