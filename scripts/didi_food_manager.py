#!/usr/bin/env python3
"""Login DiDi Food Manager."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")

URL = "https://page.didiglobal.com/public-biz/pc-login/3.0.1/index.html?source=200068&appid=200068&role=13&country_id=484&lang=es-MX"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
    )
    page = ctx.new_page()

    page.goto(URL, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(SCREEN / "didi_manager_landing.png"), full_page=True)

    # Inspeccionar los inputs
    inputs = page.eval_on_selector_all(
        "input, button",
        "els => els.map(e => ({tag: e.tagName, type: e.type||'', name: e.name||'', id: e.id||'', placeholder: e.placeholder||'', label: (e.textContent||'').trim().slice(0,40)}))"
    )
    print("=== Inputs / Botones ===", flush=True)
    for i in inputs:
        if i["type"] not in ("hidden",):
            print(f"  {i}", flush=True)

    # Buscar los campos: teléfono y contraseña
    # El campo de teléfono debe ser input tipo text/tel
    # La contraseña input type=password
    tel_input = page.locator('input[type="text"], input[type="tel"], input[placeholder*="teléfono" i], input[placeholder*="número" i]').first
    pwd_input = page.locator('input[type="password"]').first

    # Rellenar
    tel_input.click()
    tel_input.fill(creds["user_phone"])
    print(f"Teléfono rellenado: {creds['user_phone']}", flush=True)

    pwd_input.click()
    pwd_input.fill(creds["password"])
    print(f"Contraseña rellenada", flush=True)

    page.wait_for_timeout(1000)
    page.screenshot(path=str(SCREEN / "didi_manager_filled.png"), full_page=True)

    # Click en el div con clase 'button actived' (el naranja de Iniciar sesión)
    page.locator("div.button.actived").first.click()
    print("Click en div.button.actived", flush=True)

    # Esperar más tiempo y capturar mensajes de error
    page.wait_for_timeout(10000)
    # Ver si aparece mensaje de error o toast
    error_msgs = page.eval_on_selector_all(
        ".error, .toast, .message, [class*='error'], [class*='toast']",
        "els => els.map(e => e.textContent.trim()).filter(t => t.length > 0)"
    )
    for e in error_msgs:
        print(f"ERROR/MSG: {e}", flush=True)
    page.screenshot(path=str(SCREEN / "didi_manager_after_login.png"), full_page=True)
    (SCREEN / "didi_manager_after_login.html").write_text(page.content())
    print(f"URL post-login: {page.url}", flush=True)
    print(f"Title: {page.title()}", flush=True)

    # Guardar cookies para uso posterior
    cookies = ctx.cookies()
    Path("/home/tito/.openclaw/credentials/didi_restaurantes/cookies.json").write_text(json.dumps(cookies))
    print(f"Cookies guardadas: {len(cookies)}", flush=True)

    browser.close()
