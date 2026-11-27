#!/usr/bin/env python3
"""Ir a Finanzas Recibos, ampliar fechas, cambiar sucursal — ver recibos reales de junio."""
import json, re
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
    page.wait_for_timeout(3000)

    # Finanzas
    page.goto("https://www.didi-food.com/es-MX/manager/micro-shop/finance", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(8000)
    page.screenshot(path=str(SCREEN / "didi_finanzas_v3.png"), full_page=True)

    # ===== FASE 1: Ver qué muestra con la sucursal por default (ALMACEN) =====
    print("=== Recibos con sucursal por default ===", flush=True)
    r_default = page.evaluate("""() => {
        const rows = document.querySelectorAll('tr, [class*="row"]');
        const results = [];
        rows.forEach(r => {
            const t = r.innerText || '';
            if (/\\d+\\/\\d+\\/\\d+/.test(t) && /MXN/.test(t)) {
                results.push(t.split('\\n').filter(x=>x.trim()).join(' | '));
            }
        });
        return results.slice(0, 15);
    }""")
    for r in r_default:
        print(f"  DEFAULT: {r[:200]}", flush=True)

    # ===== FASE 2: Cambiar sucursal — usar keyboard navigation =====
    # Click en el dropdown de sucursal (el segundo, arriba a la derecha)
    print("\n=== Cambiando sucursal ===", flush=True)
    dropdowns = page.query_selector_all('input[readonly], .ant-select-selection-item, [class*="select"] input')
    # Buscar el que tenga "ALMACEN" o "BURGUER" en el value
    for d in dropdowns:
        try:
            val = (d.get_attribute("value") or d.inner_text() or "")
            box = d.bounding_box()
            if box and box["x"] > 1200 and ("ALMACEN" in val.upper() or "TITI" in val.upper()):
                d.click()
                print(f"Click dropdown ({val[:40]}) en x={box['x']}", flush=True)
                page.wait_for_timeout(2500)
                break
        except: pass

    page.screenshot(path=str(SCREEN / "didi_finanzas_dropdown.png"), full_page=True)

    # Buscar en el HTML todas las opciones que tengan "Montejano" y usar keyboard
    page.keyboard.type("Montejano")
    page.wait_for_timeout(2000)
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    page.screenshot(path=str(SCREEN / "didi_lm_seleccionada.png"), full_page=True)

    # ===== FASE 3: Ampliar fechas a todo junio =====
    print("\n=== Ampliando fechas a junio ===", flush=True)
    page.evaluate("""() => {
        const inputs = [...document.querySelectorAll('input')];
        const dates = inputs.filter(i => (i.value||'').match(/\\d{2}\\/\\d{2}\\/\\d{4}/));
        console.log('date inputs:', dates.length);
        if (dates.length >= 2) {
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(dates[0], '01/06/2026');
            dates[0].dispatchEvent(new Event('input', {bubbles: true}));
            dates[0].dispatchEvent(new Event('change', {bubbles: true}));
            dates[0].dispatchEvent(new Event('blur', {bubbles: true}));
            setter.call(dates[1], '11/07/2026');
            dates[1].dispatchEvent(new Event('input', {bubbles: true}));
            dates[1].dispatchEvent(new Event('change', {bubbles: true}));
            dates[1].dispatchEvent(new Event('blur', {bubbles: true}));
        }
    }""")
    page.wait_for_timeout(5000)

    page.screenshot(path=str(SCREEN / "didi_recibos_lm_junio.png"), full_page=True)
    (SCREEN / "didi_recibos_lm_junio.html").write_text(page.content())

    # Extraer todos los recibos visibles
    print("\n=== Recibos visibles después de filtros ===", flush=True)
    r_final = page.evaluate("""() => {
        const rows = document.querySelectorAll('tr, [class*="row"]');
        const results = [];
        rows.forEach(r => {
            const t = r.innerText || '';
            if (/\\d+\\/\\d+\\/\\d+/.test(t) && /MXN|\\$/.test(t)) {
                results.push(t.split('\\n').filter(x=>x.trim()).join(' | '));
            }
        });
        return [...new Set(results)].slice(0, 25);
    }""")
    for r in r_final:
        print(f"  {r[:250]}", flush=True)

    # Guardar texto
    text = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/didi_recibos_real.txt").write_text(text)
    print(f"\nURL: {page.url}", flush=True)

    browser.close()
