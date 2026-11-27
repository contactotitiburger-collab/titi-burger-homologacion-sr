#!/usr/bin/env python3
"""Ver Términos y Condiciones y Detalles de reportes."""
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

    # Términos y Condiciones
    try:
        page.locator("text=Términos y Condiciones").first.click(timeout=8000)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREEN / "didi_terminos.png"), full_page=True)
        print(f"→ Términos: {page.url}", flush=True)
    except Exception as e:
        print(f"Términos err: {e}", flush=True)

    text = page.evaluate("() => document.body.innerText")
    with open("/home/tito/.openclaw/data/didi_terminos.txt", "w") as f:
        f.write(text)
    # Buscar tarifas
    import re
    for line in text.split("\n"):
        if re.search(r"tarifa|comisi|servicio|%|precio|iva|impuesto", line, re.I) and len(line) < 300:
            print(f"  T: {line.strip()[:200]}", flush=True)

    # También ir a Estadísticas
    try:
        page.locator("text=Estadísticas").first.click(timeout=8000)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREEN / "didi_estadisticas.png"), full_page=True)
        print(f"\n→ Estadísticas: {page.url}", flush=True)
    except: pass

    browser.close()
