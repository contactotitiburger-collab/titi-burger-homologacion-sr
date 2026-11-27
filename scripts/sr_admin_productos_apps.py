#!/usr/bin/env python3
"""Reporte 7 (Productos más vendidos) mayo 2026 — filtra productos con sufijo UBER/DIDI/RAPPI."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")
OUT = Path("/home/tito/.openclaw/data/productos_mayo_2026.json")

IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 2000})
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Reporte 7 = Productos más vendidos
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Fechas mayo + Cantidad alta
    page.evaluate("""() => {
        try {
            const f1 = document.querySelector('#FechaInicial');
            const f2 = document.querySelector('#FechaFinal');
            if (f1) f1.value = '01/05/2026';
            if (f2) f2.value = '31/05/2026';
            // subir cantidad
            const cant = document.querySelector('input[type="number"]');
            if (cant) cant.value = '2000';
        } catch(e){}
    }""")

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
    try:
        page.locator('#ActualizarReporte').first.click()
    except:
        pass
    page.wait_for_load_state("networkidle", timeout=120000)
    page.wait_for_timeout(30000)
    (SCREEN_DIR / "26_productos_mayo.html").write_text(page.content())
    page.screenshot(path=str(SCREEN_DIR / "26_productos_mayo.png"), full_page=True)

    # Extraer TODA la tabla de productos
    text_all = page.evaluate("() => document.body.innerText")

    # Los productos aparecen como línea con precio: "PRODUCTO $X.XX"
    productos = []
    for line in text_all.split("\n"):
        m = re.search(r"^(\d+)\s+(.+?)\s+\$([\d,]+\.\d{2})\s+(\d+)", line.strip()) or \
            re.search(r"^(\d+)\s+(.+?)\s+(\d+)\s+\$([\d,]+\.\d{2})", line.strip())
        if m:
            # Interpretar
            productos.append(line.strip())

    # Fallback: guardar el texto y parsear la tabla completa después
    tables = page.eval_on_selector_all("table", "els => els.map(t => t.innerText)")
    print(f"Tablas encontradas: {len(tables)}", flush=True)
    for i, t in enumerate(tables):
        if len(t) > 100:
            print(f"\n--- Tabla {i} (primeras 3000 chars) ---", flush=True)
            print(t[:3000], flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "mes": "mayo 2026",
        "tables": tables,
    }, indent=2, ensure_ascii=False))

    browser.close()
