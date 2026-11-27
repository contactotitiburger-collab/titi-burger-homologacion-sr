#!/usr/bin/env python3
"""Reporte 16: Ventas por mesero — por sucursal, junio + julio."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SUCS = {
    "12764":"FOVISSTE","13056":"MONTECARLO","22871":"SAN MARCOS",
    "22980":"HACIENDA DEL RÍO","23032":"CURTO","26983":"VILLAS DEL REY",
}

def login(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1200})
    page = ctx.new_page()
    login(page)

    resultados = {}
    # Junio y julio, por sucursal
    for periodo, (f_ini, f_fin) in [("junio", ("01/06/2026","30/06/2026")), ("julio", ("01/07/2026","11/07/2026"))]:
        print(f"\n=== {periodo.upper()} — Ventas por mesero ===", flush=True)
        for suc_id, suc_nombre in SUCS.items():
            page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/16", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2500)
            page.locator('#FechaInicial').fill(f_ini)
            page.locator('#FechaFinal').fill(f_fin)
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
            page.wait_for_load_state("networkidle", timeout=90000)
            page.wait_for_timeout(12000)

            text = page.evaluate("() => document.body.innerText")
            Path(f"/home/tito/.openclaw/data/sr_meseros_{periodo}_{suc_nombre.replace(' ','_')}.txt").write_text(text)

            # Extraer tabla de meseros
            # Formato típico: MESERO | Cuentas | Personas | Ventas | ...
            print(f"\n  {suc_nombre}:", flush=True)
            lines = text.split("\n")
            for i, line in enumerate(lines):
                l = line.strip()
                # buscar filas de meseros con nombre + venta
                m = re.match(r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s\.]+)\s+(\d+)\s+(\d+)\s+\$?([\d,]+\.\d{2})", l)
                if m and len(m.group(1).strip()) > 2 and "TOTAL" not in m.group(1).upper():
                    resultados.setdefault(periodo, {}).setdefault(suc_nombre, []).append({
                        "mesero": m.group(1).strip(),
                        "cuentas": int(m.group(2)),
                        "personas": int(m.group(3)),
                        "ventas": float(m.group(4).replace(",","")),
                    })
                    print(f"    {m.group(1).strip():25s}  cuentas:{m.group(2):>4}  ventas:${m.group(4)}", flush=True)

    Path("/home/tito/.openclaw/data/meseros_por_sucursal.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    browser.close()
print("\nOK")
