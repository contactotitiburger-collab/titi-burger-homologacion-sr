#!/usr/bin/env python3
"""Ir directo a Finanzas y sacar comisiones."""
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

    # Login
    page.goto("https://www.didi-food.com/es-MX/manager", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('input[placeholder*="Número" i]').first.type(creds["user_phone"], delay=60)
    page.locator('input[type="password"]').first.type(creds["password"], delay=60)
    page.wait_for_timeout(1500)
    page.locator("div.button.actived").first.click()
    page.wait_for_timeout(6000)

    # Aceptar rol
    try:
        page.locator("button:has-text('Aceptar')").first.click(timeout=8000)
    except: pass
    page.wait_for_timeout(6000)

    # Cerrar guía
    try:
        page.locator("text=Saltar").first.click(timeout=5000)
        page.wait_for_timeout(2000)
    except: pass

    # Click Finanzas
    try:
        page.locator("text=Finanzas").first.click(timeout=8000)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREEN / "didi_finanzas.png"), full_page=True)
        (SCREEN / "didi_finanzas.html").write_text(page.content())
        print(f"→ Finanzas URL: {page.url}", flush=True)
    except Exception as e:
        print(f"Finanzas: {e}", flush=True)

    # Buscar sub-menús de Finanzas (Comisiones, Pagos, etc.)
    print("\n=== Sub-menú Finanzas ===")
    subs = page.evaluate("""() => {
        const results = new Set();
        document.querySelectorAll('a, span, div, li, button').forEach(e => {
            const t = (e.textContent||'').trim();
            if (t.length > 2 && t.length < 40 && e.children.length < 3 &&
                /pago|ingres|comisi|liquid|movim|estado.*cuenta|balance|resumen|periodo|hist/i.test(t)) {
                results.add(t);
            }
        });
        return [...results];
    }""")
    for s in subs[:30]:
        print(f"  {s}", flush=True)

    # Buscar mensaje de bienvenida en Finanzas
    all_text = page.evaluate("() => document.body.innerText")
    with open("/home/tito/.openclaw/data/didi_finanzas_texto.txt", "w") as f:
        f.write(all_text)
    print(f"\nTexto completo guardado: /home/tito/.openclaw/data/didi_finanzas_texto.txt", flush=True)

    browser.close()
