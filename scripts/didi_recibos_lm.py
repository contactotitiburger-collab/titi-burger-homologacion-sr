#!/usr/bin/env python3
"""Buscar recibos de DiDi en la sucursal L Montejano (la que vende)."""
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

    # Ir a Finanzas
    page.goto("https://www.didi-food.com/es-MX/manager/micro-shop/finance", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(6000)

    # Abrir dropdown de tienda (arriba derecha)
    tienda_selector = page.locator('input[placeholder*="Titi" i], input[placeholder*="tienda" i], input[readonly]').last
    tienda_selector.click()
    page.wait_for_timeout(2000)
    page.screenshot(path=str(SCREEN / "didi_dropdown_tienda.png"), full_page=True)

    # Ver lista de tiendas
    tiendas = page.eval_on_selector_all(
        "li, div[role='option'], [class*='option']",
        """els => els.filter(e => (e.textContent||'').includes('Titi'))
                    .map(e => e.textContent.trim().slice(0, 80))
                    .filter(t => t.length < 100)"""
    )
    print("=== Tiendas disponibles ===")
    for t in tiendas[:15]:
        print(f"  {t}", flush=True)

    # Seleccionar la de L Montejano (o Montejano)
    try:
        opt = page.locator("li:has-text('Montejano'), div[role='option']:has-text('Montejano'), [class*='option']:has-text('Montejano')").first
        opt.click(timeout=5000)
        page.wait_for_timeout(3000)
        print("Seleccionada L Montejano", flush=True)
    except Exception as e:
        print(f"Sin Montejano: {e}", flush=True)
        # Intentar con "L. Montejano"
        try:
            page.get_by_text("L. Montejano").first.click(timeout=3000)
        except: pass

    page.wait_for_timeout(3000)
    # Volver a la pestaña Recibos
    try:
        page.locator("text=Recibos").first.click()
        page.wait_for_timeout(4000)
    except: pass

    # Cambiar rango de fechas — poner del 1 abril al 11 jul (3 meses hacia atrás)
    try:
        # Buscar input de fecha inicial (formato dd/mm/yyyy)
        fecha_ini = page.locator('input').filter(has_text="").first  # first date input
        # Alternativa: setear con JS
        page.evaluate("""() => {
            const inputs = document.querySelectorAll('input');
            for (const i of inputs) {
                if (i.value.match(/\\d{2}\\/\\d{2}\\/\\d{4}/)) {
                    i.value = '';
                    i.dispatchEvent(new Event('input', {bubbles: true}));
                }
            }
        }""")
    except: pass
    page.wait_for_timeout(2000)
    page.screenshot(path=str(SCREEN / "didi_recibos_lm.png"), full_page=True)
    (SCREEN / "didi_recibos_lm.html").write_text(page.content())
    print(f"URL: {page.url}", flush=True)

    browser.close()
