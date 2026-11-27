#!/usr/bin/env python3
"""Ventas por hora — reporte 15 por sucursal para detectar picos horarios."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SUCS_ACTIVAS = {
    "12764":"FOVISSTE","13056":"MONTECARLO","22871":"SAN MARCOS",
    "22980":"HACIENDA DEL RÍO","26983":"VILLAS DEL REY",
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
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400})
    page = ctx.new_page()
    login(page)

    # Reporte 15: Ventas por hora
    resultados = {}
    for suc_id, suc_nombre in SUCS_ACTIVAS.items():
        print(f"\n=== {suc_nombre} — Ventas por hora (jun+jul 2026) ===", flush=True)
        page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/15", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)
        page.locator('#FechaInicial').fill('01/06/2026')
        page.locator('#FechaFinal').fill('11/07/2026')
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
        page.wait_for_timeout(15000)

        text = page.evaluate("() => document.body.innerText")
        Path(f"/home/tito/.openclaw/data/sr_hora_{suc_nombre.replace(' ','_')}.txt").write_text(text)
        # Extraer hora → venta
        horas = {}
        for line in text.split("\n"):
            # patrones tipo "13:00 $12,345.67" o "13 $12,345"
            m = re.match(r"^(\d{1,2})(?::\d{2})?\s+\$?([\d,]+\.\d{2})", line.strip())
            if m and 6 <= int(m.group(1)) <= 23:
                h = int(m.group(1))
                v = float(m.group(2).replace(",",""))
                horas[h] = horas.get(h, 0) + v
        resultados[suc_nombre] = horas
        for h in sorted(horas):
            print(f"  {h:2d}:00 - ${horas[h]:>10,.2f}", flush=True)

    Path("/home/tito/.openclaw/data/dc_por_hora.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    browser.close()
print("\nOK")
