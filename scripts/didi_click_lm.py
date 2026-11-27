#!/usr/bin/env python3
"""Cambiar sucursal a L Montejano usando click con posición del ratón."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1200},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    # Login (compacto)
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
    page.wait_for_timeout(3000)

    # Finanzas
    page.goto("https://www.didi-food.com/es-MX/manager/micro-shop/finance", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(6000)

    # Click en las coordenadas del dropdown de sucursal (esquina sup der)
    # Basado en screenshots anteriores: aprox x=1450, y=100
    page.mouse.click(1450, 100)
    print("Click coords (1450, 100)", flush=True)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(SCREEN / "didi_dd_open_v2.png"), full_page=True)

    # Ver qué opciones aparecen
    (SCREEN / "didi_dd_open.html").write_text(page.content())
    opciones = page.eval_on_selector_all(
        "*",
        """els => {
            const seen = new Set();
            return els.filter(e => {
                const t = (e.textContent||'').trim();
                return t.length > 5 && t.length < 80 && e.children.length === 0 &&
                       /Titi Burger|Titi Burguer/i.test(t) && !seen.has(t) && seen.add(t);
            }).map(e => {
                const r = e.getBoundingClientRect();
                return {text: e.textContent.trim().slice(0,60), x: r.x, y: r.y, w: r.width, h: r.height};
            });
        }"""
    )
    print("=== Opciones dropdown ===", flush=True)
    for o in opciones[:15]:
        print(f"  {o}", flush=True)

    # Click en L Montejano usando coordenadas del bounding box
    for o in opciones:
        if "montejano" in o["text"].lower():
            # Click con coordenadas
            page.mouse.click(o["x"] + o["w"]/2, o["y"] + o["h"]/2)
            print(f"Click en coords ({o['x']}, {o['y']}): {o['text']}", flush=True)
            page.wait_for_timeout(5000)
            break

    # Ampliar fechas
    page.evaluate("""() => {
        const inputs = [...document.querySelectorAll('input')];
        const dates = inputs.filter(i => (i.value||'').match(/\\d{2}\\/\\d{2}\\/\\d{4}/));
        if (dates.length >= 2) {
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(dates[0], '01/06/2026');
            ['input','change','blur'].forEach(ev => dates[0].dispatchEvent(new Event(ev, {bubbles: true})));
            setter.call(dates[1], '11/07/2026');
            ['input','change','blur'].forEach(ev => dates[1].dispatchEvent(new Event(ev, {bubbles: true})));
        }
    }""")
    page.wait_for_timeout(6000)

    page.screenshot(path=str(SCREEN / "didi_recibos_lm_final.png"), full_page=True)
    text = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/didi_recibos_lm_final.txt").write_text(text)

    # Buscar líneas con "MXN"
    import re
    print("\n=== Recibos ===")
    for line in text.split("\n"):
        line = line.strip()
        if re.search(r"MXN|periodo|ganancias|transfer", line, re.I) and len(line) < 250:
            print(f"  {line}", flush=True)

    browser.close()
