#!/usr/bin/env python3
"""Sacar datos DiDi junio 2026 por tienda desde Estadísticas."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")
OUT = Path("/home/tito/.openclaw/data/didi_junio_2026.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    # Login
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

    # Ir a Estadísticas con fechas junio 2026
    URL_EST = "https://www.didi-food.com/es-MX/manager/insights/v2?tab=shopRank&startDate=2026-06-01&endDate=2026-06-30"
    page.goto(URL_EST, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(8000)
    page.screenshot(path=str(SCREEN / "didi_estadisticas_junio.png"), full_page=True)
    (SCREEN / "didi_estadisticas_junio.html").write_text(page.content())

    # Extraer info del texto completo
    text = page.evaluate("() => document.body.innerText")
    with open("/home/tito/.openclaw/data/didi_junio_texto.txt", "w") as f:
        f.write(text)

    print("=== Contenido relevante ===")
    for line in text.split("\n"):
        line = line.strip()
        if not line: continue
        # Buscar líneas con Titi Burger + números
        if "Titi Burger" in line or re.match(r"^MX?\$?[\d,]+\.?\d*$", line) or re.match(r"^\d+\.?\d*%?$", line):
            print(f"  {line[:100]}", flush=True)

    browser.close()
