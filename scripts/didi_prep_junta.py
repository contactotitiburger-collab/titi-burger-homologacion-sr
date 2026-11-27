#!/usr/bin/env python3
"""Jalar datos DiDi por tienda para la junta con Elias: julio 2026 + agosto a la fecha."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")
OUT = Path("/home/tito/.openclaw/data/didi_prep_junta.json")

PERIODOS = {
    "julio_2026": ("2026-07-01", "2026-07-31"),
    "agosto_2026": ("2026-08-01", "2026-08-11"),
}

def parse_stats(text):
    return [l.strip() for l in text.split("\n") if l.strip()]

resultado = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
        timezone_id="America/Tijuana",
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
    print("Login OK", flush=True)

    for nombre, (ini, fin) in PERIODOS.items():
        url = f"https://www.didi-food.com/es-MX/manager/insights/v2?tab=shopRank&startDate={ini}&endDate={fin}"
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(8000)
        page.screenshot(path=str(SCREEN / f"didi_{nombre}.png"), full_page=True)
        text = page.evaluate("() => document.body.innerText")
        (Path(f"/home/tito/.openclaw/data/didi_{nombre}_texto.txt")).write_text(text)
        resultado[nombre] = {"rango": [ini, fin], "lineas": parse_stats(text)}
        print(f"--- {nombre} ({ini} a {fin}) capturado ---", flush=True)

    browser.close()

OUT.write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
print(f"Guardado en {OUT}", flush=True)
