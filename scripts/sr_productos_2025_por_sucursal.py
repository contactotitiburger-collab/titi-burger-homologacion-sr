#!/usr/bin/env python3
"""
Baja el Excel de "Productos más vendidos" de Soft Restaurant para cada sucursal
y para 2025 completo, en 2 tramos (H1 y H2). Guarda en:
    ~/.openclaw/data/sr_productos_2025/<sucursal>_<H>.xlsx

Estrategia (probada): usa el botón EXCEL del portal en lugar de parsear HTML.
"""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT_DIR = Path("/home/tito/.openclaw/data/sr_productos_2025")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUCS = {
    "22871":"SAN_MARCOS",
    "26983":"VILLAS_DEL_REY",
}

TRAMOS = [
    # 2026 mes por mes — Villas del Rey y San Marcos son sucursales nuevas
    # (2025 dio vacío para ambas)
    ("ene26", "01/01/2026", "31/01/2026"),
    ("feb26", "01/02/2026", "28/02/2026"),
    ("mar26", "01/03/2026", "31/03/2026"),
    ("abr26", "01/04/2026", "30/04/2026"),
    ("may26", "01/05/2026", "31/05/2026"),
    ("jun26", "01/06/2026", "30/06/2026"),
]

def login(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400}, accept_downloads=True)
    page = ctx.new_page()
    login(page)

    for tramo, desde, hasta in TRAMOS:
        for suc_id, suc_nombre in SUCS.items():
            out = OUT_DIR / f"{suc_nombre}_{tramo}.xlsx"
            if out.exists() and out.stat().st_size > 3000:
                print(f"[skip] ya existe {out.name}", flush=True)
                continue

            print(f"\n=== {suc_nombre} — {tramo} ({desde} a {hasta}) ===", flush=True)
            page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
                      wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(3000)
            page.locator('#FechaInicial').fill(desde)
            page.locator('#FechaFinal').fill(hasta)
            page.keyboard.press("Escape")   # cerrar cualquier picker
            page.wait_for_timeout(500)

            # cantidad al máx
            page.evaluate("""() => {
                const c = document.querySelector('#NumElementosTop');
                if (c) {
                    const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    s.call(c, '2000');
                    c.dispatchEvent(new Event('input', {bubbles: true}));
                    c.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }""")
            # empresa
            page.evaluate("""(id) => {
                const sel = document.querySelector('#ListaEmpresas');
                if (sel) {
                    for (const opt of sel.options) opt.selected = (opt.value === id);
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    if (window.jQuery) window.jQuery(sel).trigger('change');
                }
            }""", suc_id)
            page.wait_for_timeout(1000)

            page.locator('#ActualizarReporte').first.click()
            page.wait_for_load_state("networkidle", timeout=120000)
            # Esperar tab de la sucursal
            try:
                page.wait_for_selector(f'#tab_{suc_id}', state="visible", timeout=90000)
                page.locator(f'#tab_{suc_id}').click()
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  ⚠️  no apareció tab: {e}", flush=True)
                continue

            try:
                with page.expect_download(timeout=90000) as dinfo:
                    page.locator('#ExportarExcel').click(force=True)
                d = dinfo.value
                d.save_as(str(out))
                print(f"  ✅ {out.name}  ({out.stat().st_size} bytes)", flush=True)
            except Exception as e:
                print(f"  ❌ no bajó: {e}", flush=True)

    browser.close()

print(f"\nArchivos en {OUT_DIR}:")
for f in sorted(OUT_DIR.iterdir()):
    print(f"  {f.name}  ({f.stat().st_size} bytes)")
