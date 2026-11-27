#!/usr/bin/env python3
"""DiDi: pedidos (Ventas completadas) por tienda AGOSTO 2026 completo (1-31)."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")
OUT = Path("/home/tito/.openclaw/data/didi_agosto2026_completo.json")
INI, FIN = "2026-08-01", "2026-08-31"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX", timezone_id="America/Tijuana",
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()
    page.goto("https://www.didi-food.com/es-MX/manager", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    page.locator('input[placeholder*="Número" i]').first.type(creds["user_phone"], delay=60)
    page.locator('input[type="password"]').first.type(creds["password"], delay=60)
    page.wait_for_timeout(1000)
    page.locator("div.button.actived").first.click()
    page.wait_for_timeout(6000)
    try: page.locator("button:has-text('Aceptar')").first.click(timeout=8000)
    except: pass
    page.wait_for_timeout(5000)
    try: page.locator("text=Saltar").first.click(timeout=5000)
    except: pass
    page.wait_for_timeout(2000)
    print("Login OK", flush=True)

    url = f"https://www.didi-food.com/es-MX/manager/insights/v2?tab=shopRank&startDate={INI}&endDate={FIN}"
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(10000)
    page.screenshot(path=str(SCREEN / "didi_agosto_completo.png"), full_page=True)
    text = page.evaluate("() => document.body.innerText")
    (Path("/home/tito/.openclaw/data/didi_agosto_completo_texto.txt")).write_text(text)
    browser.close()

# Parse: after 'Tiempo promedio...' header come groups of 5, then 'Nombre de la tienda' then names
lines = [l.strip() for l in text.split("\n") if l.strip()]
try:
    idx = lines.index("Tiempo promedio de preparación (minutos)")
except ValueError:
    idx = None
result = {"periodo": [INI, FIN], "sucursales": {}, "total_pedidos": 0}
if idx is not None:
    block = lines[idx+1:]
    # numbers groups until 'Nombre de la tienda'
    try:
        nidx = block.index("Nombre de la tienda")
    except ValueError:
        nidx = None
    nums_part = block[:nidx] if nidx is not None else block
    names_part = block[nidx+1:] if nidx is not None else []
    # extract pedidos = every 5th starting at 0
    pedidos = []
    i = 0
    while i < len(nums_part):
        try:
            ped = int(nums_part[i].replace(",", ""))
        except ValueError:
            i += 1; continue
        pedidos.append(ped)
        i += 5
    # names: take valid store names in order
    names = [n for n in names_part if n.lower().startswith("titi")]
    for j, nm in enumerate(names):
        if j < len(pedidos):
            result["sucursales"][nm] = pedidos[j]
    result["total_pedidos"] = sum(pedidos)
    result["_pedidos_raw"] = pedidos
    result["_names_raw"] = names
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
