#!/usr/bin/env python3
"""Recibos DiDi de la sucursal L Montejano — ver comisiones."""
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
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    # Login completo
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

    # Ir a Finanzas
    page.goto("https://www.didi-food.com/es-MX/manager/micro-shop/finance", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(6000)

    # Cambiar la sucursal — click en el segundo dropdown "TITI BURGUER ALMACEN"
    # Es el input readonly que dice el nombre de la sucursal
    dropdowns = page.query_selector_all("input")
    for d in dropdowns:
        val = (d.get_attribute("value") or "").upper()
        if "ALMACEN" in val or "BURGUER" in val:
            box = d.bounding_box()
            if box and box["x"] > 500:  # está a la derecha
                d.click()
                print(f"Click dropdown: {val}", flush=True)
                page.wait_for_timeout(2000)
                page.screenshot(path=str(SCREEN / "didi_lm_dropdown.png"), full_page=True)
                break

    # Buscar opción "Titi Burger (L Montejano)" o similar
    # Puede que en el dropdown la opción se llame diferente
    page.wait_for_timeout(2000)
    (SCREEN / "didi_lm_dropdown_html.html").write_text(page.content())

    # Buscar cualquier opción que contenga "L Montejano" o "L. Montejano"
    opciones = page.eval_on_selector_all(
        "*",
        """els => els.filter(e => {
            const t = (e.textContent||'').trim();
            return e.children.length === 0 && /Montejano|Titi Burger$/.test(t) && t.length < 100;
        }).map(e => ({tag: e.tagName, text: e.textContent.trim().slice(0,80)}))"""
    )
    print("=== Opciones encontradas ===")
    for o in opciones[:15]:
        print(f"  {o}", flush=True)

    # Click con FORCE en la opción "L Montejano" (aunque esté fuera de viewport)
    try:
        page.locator("span.shop-name:has-text('Montejano')").first.click(force=True, timeout=10000)
        print("Click Montejano (force)", flush=True)
        page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Force click err: {e}", flush=True)

    # Cambiar rango de fechas — junio 2026
    # Los inputs de fecha están en la pantalla
    page.evaluate("""() => {
        const dates = [...document.querySelectorAll('input')].filter(i =>
            i.value && i.value.match(/\\d{2}\\/\\d{2}\\/\\d{4}/));
        if (dates.length >= 2) {
            // Cambiar valores
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(dates[0], '01/06/2026');
            dates[0].dispatchEvent(new Event('input', {bubbles: true}));
            dates[0].dispatchEvent(new Event('change', {bubbles: true}));
            setter.call(dates[1], '30/06/2026');
            dates[1].dispatchEvent(new Event('input', {bubbles: true}));
            dates[1].dispatchEvent(new Event('change', {bubbles: true}));
        }
    }""")
    page.wait_for_timeout(4000)

    page.screenshot(path=str(SCREEN / "didi_recibos_lm_v3.png"), full_page=True)
    (SCREEN / "didi_recibos_lm_v3.html").write_text(page.content())
    print(f"URL: {page.url}", flush=True)

    # Extraer texto
    text = page.evaluate("() => document.body.innerText")
    with open("/home/tito/.openclaw/data/didi_recibos_lm.txt", "w") as f:
        f.write(text)
    # Buscar MXN y % en el texto
    import re
    for line in text.split("\n"):
        line = line.strip()
        if re.search(r"MXN|\$|comisi|periodo|ganancia|adeudo|transfer", line, re.I):
            print(f"  {line[:150]}", flush=True)

    browser.close()
