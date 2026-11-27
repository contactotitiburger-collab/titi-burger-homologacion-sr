#!/usr/bin/env python3
"""Cambiar tienda a L Montejano y ver recibos."""
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

    # Ir a Finanzas
    page.goto("https://www.didi-food.com/es-MX/manager/micro-shop/finance", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(6000)

    # Buscar todos los inputs para localizar el selector de tienda
    all_inputs = page.eval_on_selector_all(
        "input",
        "els => els.map(e => ({placeholder: e.placeholder||'', value: e.value||'', readonly: e.readOnly, id: e.id||'', pos: e.getBoundingClientRect()}))"
    )
    print("=== INPUTS en Finanzas ===")
    for i, inp in enumerate(all_inputs):
        print(f"  {i}: placeholder={inp['placeholder']!r} value={inp['value']!r} pos={inp['pos']}", flush=True)

    # Click en el segundo dropdown (el de la tienda específica)
    # Es el input readOnly con value "TITI BURGUER..."
    for i, inp in enumerate(all_inputs):
        if "TITI" in inp["value"].upper() or "ALMACEN" in inp["value"].upper():
            # click en ese elemento
            elems = page.query_selector_all("input")
            elems[i].click()
            print(f"Click en input {i}: {inp['value']}", flush=True)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SCREEN / "didi_dropdown_open.png"), full_page=True)
            (SCREEN / "didi_dropdown_open.html").write_text(page.content())
            break

    # Ver opciones disponibles
    opciones = page.eval_on_selector_all(
        "*",
        """els => els.filter(e => (e.textContent||'').toLowerCase().includes('montejano') && e.children.length < 3)
                    .map(e => ({tag: e.tagName, text: e.textContent.trim().slice(0,80), cls: e.className}))
                    .slice(0, 5)"""
    )
    print("=== Opciones con 'montejano' ===")
    for o in opciones:
        print(f"  {o}", flush=True)

    # Click en L. Montejano
    for o in opciones:
        if "montejano" in o["text"].lower():
            try:
                page.locator(f"text={o['text']}").first.click(timeout=5000)
                page.wait_for_timeout(5000)
                print(f"Click en: {o['text']}", flush=True)
                break
            except Exception as e:
                print(f"  Err: {e}", flush=True)

    # Ampliar rango de fechas: buscar los 2 inputs de fecha
    page.evaluate("""() => {
        const dates = [...document.querySelectorAll('input')].filter(i => i.value && i.value.match(/\\d{2}\\/\\d{2}\\/\\d{4}/));
        console.log('date inputs found:', dates.length);
    }""")

    page.wait_for_timeout(3000)
    page.screenshot(path=str(SCREEN / "didi_recibos_montejano.png"), full_page=True)
    (SCREEN / "didi_recibos_montejano.html").write_text(page.content())
    print(f"URL: {page.url}", flush=True)

    # Extraer texto
    text = page.evaluate("() => document.body.innerText")
    with open("/home/tito/.openclaw/data/didi_recibos_montejano.txt", "w") as f:
        f.write(text)

    browser.close()
