#!/usr/bin/env python3
"""Info financiera + cambiar sucursal + estadísticas por tienda."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
        accept_downloads=True,
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    # Flujo completo login
    page.goto("https://www.didi-food.com/es-MX/manager", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('input[placeholder*="Número" i]').first.type(creds["user_phone"], delay=60)
    page.locator('input[type="password"]').first.type(creds["password"], delay=60)
    page.wait_for_timeout(1000)
    page.locator("div.button.actived").first.click()
    page.wait_for_timeout(6000)
    try: page.locator("button:has-text('Aceptar')").first.click(timeout=8000)
    except: pass
    page.wait_for_timeout(6000)
    try: page.locator("text=Saltar").first.click(timeout=5000)
    except: pass
    page.wait_for_timeout(2000)

    # Ir directo a Finanzas
    page.goto("https://www.didi-food.com/es-MX/manager/micro-shop/finance", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(6000)

    # Click en Información financiera
    try:
        page.locator("text=Información financiera").first.click(timeout=8000)
        page.wait_for_timeout(5000)
        page.screenshot(path=str(SCREEN / "didi_info_financiera.png"), full_page=True)
        (SCREEN / "didi_info_financiera.html").write_text(page.content())
        print(f"→ Info financiera: {page.url}", flush=True)
    except Exception as e:
        print(f"Info financiera err: {e}", flush=True)

    # Ver info visible en pantalla
    text = page.evaluate("() => document.body.innerText")
    with open("/home/tito/.openclaw/data/didi_info_financiera.txt", "w") as f:
        f.write(text)
    # Buscar %, comisión, tarifa
    import re
    for line in text.split("\n"):
        if re.search(r"comisi|tarifa|servicio|%|iva", line, re.I):
            print(f"  LINE: {line.strip()}", flush=True)

    browser.close()
