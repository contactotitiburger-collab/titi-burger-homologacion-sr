#!/usr/bin/env python3
"""Investigación Doble Carne — patrones por sucursal, día y hora."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/sr_admin_screens/doble_carne")
SCREEN.mkdir(parents=True, exist_ok=True)

SUCS = ["12764","13056","22871","22980","23032","26983"]
NOMBRES = {
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

    # Reporte 7: Productos más vendidos — junio y julio, cantidad alta
    # Vamos a hacer 2 consultas: junio y julio, cada una con todas las sucursales
    resultados = {}
    for mes_num, mes_nombre in [(6, "junio"), (7, "julio")]:
        print(f"\n=== {mes_nombre.upper()} 2026 ===", flush=True)
        # Fechas del mes completo (junio o hasta hoy en julio)
        if mes_num == 6:
            f_ini, f_fin = "01/06/2026", "30/06/2026"
        else:
            f_ini, f_fin = "01/07/2026", "11/07/2026"

        page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        # Fechas
        page.locator('#FechaInicial').fill(f_ini)
        page.locator('#FechaFinal').fill(f_fin)

        # Cantidad al máximo
        page.evaluate("""() => {
            const c = document.querySelector('#NumElementosTop');
            if (c) {
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                setter.call(c, '1500');
                c.dispatchEvent(new Event('input', {bubbles: true}));
                c.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""")

        # Todas las empresas
        page.evaluate("""(ids) => {
            const sel = document.querySelector('#ListaEmpresas');
            if (sel) {
                for (const opt of sel.options) opt.selected = ids.includes(opt.value);
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
            }
        }""", SUCS)
        page.wait_for_timeout(1500)

        page.locator('#ActualizarReporte').first.click()
        page.wait_for_load_state("networkidle", timeout=120000)
        page.wait_for_timeout(30000)

        text = page.evaluate("() => document.body.innerText")
        Path(f"/home/tito/.openclaw/data/sr_productos_{mes_nombre}.txt").write_text(text)

        # Buscar productos con "DOBLE CARNE" (variantes)
        productos_dc = []
        for line in text.split("\n"):
            line = line.strip()
            m = re.search(r"(\d+)\s+([A-Z0-9#\s\.\-\+_]+DOBLE[A-Z0-9#\s\.\-\+_]*CARNE[A-Z0-9#\s\.\-\+_]*)\s*\$?([\d,]+\.\d{2})", line, re.I)
            if m:
                productos_dc.append({"cantidad": int(m.group(1)), "producto": m.group(2).strip(), "importe": float(m.group(3).replace(",",""))})
        print(f"Productos DOBLE CARNE encontrados: {len(productos_dc)}", flush=True)
        for pd in productos_dc[:10]:
            print(f"  {pd['cantidad']:>4}  {pd['producto']:50s}  ${pd['importe']:>10,.2f}", flush=True)

        resultados[mes_nombre] = productos_dc

    # Guardar
    Path("/home/tito/.openclaw/data/doble_carne_reporte.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    browser.close()
print("OK")
