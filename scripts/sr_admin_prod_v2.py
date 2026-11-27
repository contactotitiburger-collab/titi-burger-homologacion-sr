#!/usr/bin/env python3
"""Reporte 7 (Productos más vendidos) — mayo 2026 con cantidad alta."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 3000})
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Inspeccionar inputs
    inputs = page.eval_on_selector_all("input", "els => els.map(e => ({id: e.id||'', name: e.name||'', type: e.type||'', val: e.value||''}))")
    for i in inputs:
        if i["val"] or i["type"] in ["number","date","text"]:
            print(f"  input: {i}", flush=True)

    # Setear fechas
    page.locator('#FechaInicial').fill('01/05/2026')
    page.locator('#FechaFinal').fill('31/05/2026')

    # Setear cantidad = 1500 usando propiedad nativa que sobrescribe React/JQ
    page.evaluate("""() => {
        const c = document.querySelector('#NumElementosTop');
        if (c) {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(c, '1500');
            c.dispatchEvent(new Event('input', {bubbles: true}));
            c.dispatchEvent(new Event('change', {bubbles: true}));
        }
    }""")
    print("Cantidad seteada a 1500", flush=True)

    # 6 empresas
    page.evaluate("""(ids) => {
        try {
            const sel = document.querySelector('#ListaEmpresas');
            if (sel) {
                for (const opt of sel.options) opt.selected = ids.includes(opt.value);
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
            }
        } catch(e){}
    }""", IDS)
    page.wait_for_timeout(1000)

    # Consultar
    consultar = page.locator('#ActualizarReporte, input[value="Consultar"], button:has-text("Consultar")').first
    consultar.click()
    page.wait_for_load_state("networkidle", timeout=180000)
    # Esperar 90s adicionales para que la tabla grande cargue
    page.wait_for_timeout(90000)

    page.screenshot(path=str(SCREEN_DIR / "27_productos_mayo_v2.png"), full_page=True)
    (SCREEN_DIR / "27_productos_mayo_v2.html").write_text(page.content())

    text_all = page.evaluate("() => document.body.innerText")
    # Buscar productos UBER / DIDI / RAPPI
    total_uber = 0.0
    total_didi = 0.0
    total_rappi = 0.0
    productos_uber = []
    productos_didi = []
    productos_rappi = []
    for line in text_all.split("\n"):
        # buscar formatos "N ... $X.XX qty" o similar
        m = re.match(r"^\d+\s+(.+?)\s+\$?([\d,]+\.\d{2})", line.strip())
        if not m:
            continue
        nombre = m.group(1).strip().upper()
        monto = float(m.group(2).replace(",", ""))
        if "UBER" in nombre:
            total_uber += monto
            productos_uber.append((nombre, monto))
        elif "DIDI" in nombre:
            total_didi += monto
            productos_didi.append((nombre, monto))
        elif "RAPPI" in nombre or "RAPPY" in nombre:
            total_rappi += monto
            productos_rappi.append((nombre, monto))

    print(f"\n{'='*70}", flush=True)
    print(f"UBER:  ${total_uber:>12,.2f}  ({len(productos_uber)} productos)", flush=True)
    print(f"DIDI:  ${total_didi:>12,.2f}  ({len(productos_didi)} productos)", flush=True)
    print(f"RAPPI: ${total_rappi:>12,.2f}  ({len(productos_rappi)} productos)", flush=True)

    # También guardar todo
    Path("/home/tito/.openclaw/data/productos_mayo_2026_texto.txt").write_text(text_all)

    browser.close()
