#!/usr/bin/env python3
"""Precio promedio de #5 TITI DOBLE CARNE en cada sucursal — detectar descuento sistemático."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SUCS = {
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
    ctx = browser.new_context(viewport={"width": 1800, "height": 1200})
    page = ctx.new_page()
    login(page)

    resultados = {}
    for suc_id, suc_nombre in SUCS.items():
        print(f"\n=== {suc_nombre} — reporte 7 detalle ===", flush=True)
        page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)
        page.locator('#FechaInicial').fill('01/06/2026')
        page.locator('#FechaFinal').fill('11/07/2026')
        page.evaluate("""() => {
            const c = document.querySelector('#NumElementosTop');
            if (c) {
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                setter.call(c, '1500');
                c.dispatchEvent(new Event('input', {bubbles: true}));
                c.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""")
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
        Path(f"/home/tito/.openclaw/data/rep7_{suc_nombre.replace(' ','_')}.txt").write_text(text)

        # Buscar líneas de #5 TITI DOBLE CARNE y TITI COMBO DOBLE CARNE
        # Formato: clave, descripción, cantidad, precio promedio, importe sin imp, total
        # ej: 01002 #5 TITI DOBLE CARNE 55.00 $200.00 $11,000.00 $11,000.00
        detalle = {}
        lines = text.split("\n")
        for i in range(len(lines)-4):
            joined = " ".join(lines[i:i+6]).strip()
            m = re.search(r"(01002|01037)\s+([A-Z0-9#\.\s]+(?:DOBLE CARNE|COMBO DOBLE CARNE))\s+([\d,]+)\.\d+\s+\$([\d,]+\.\d+)\s+\$([\d,]+\.\d+)\s+\$([\d,]+\.\d+)", joined)
            if m:
                clave = m.group(1)
                desc = m.group(2).strip()
                cantidad = int(m.group(3).replace(",",""))
                precio_prom = float(m.group(4).replace(",",""))
                importe_sin_imp = float(m.group(5).replace(",",""))
                total = float(m.group(6).replace(",",""))
                detalle[clave] = {
                    "producto": desc,
                    "cantidad": cantidad,
                    "precio_promedio": precio_prom,
                    "importe_sin_imp": importe_sin_imp,
                    "total": total,
                }
                print(f"  {clave} {desc}: {cantidad}u × ${precio_prom} = TOTAL ${total} (esperado ${cantidad*precio_prom})", flush=True)

        resultados[suc_nombre] = detalle

    # Comparativa
    print("\n\n=== COMPARATIVA #5 TITI DOBLE CARNE (clave 01002) ===")
    print(f"{'Sucursal':<25} {'Cant':>6} {'Precio prom':>12} {'Total':>15} {'Precio lista?':>15}")
    for suc, det in resultados.items():
        dc = det.get("01002", {})
        if dc:
            print(f"{suc:<25} {dc['cantidad']:>6} ${dc['precio_promedio']:>11.2f} ${dc['total']:>14,.2f} {'$200 lista':>15}")

    print("\n=== COMPARATIVA TITI COMBO DOBLE CARNE (clave 01037) ===")
    for suc, det in resultados.items():
        dc = det.get("01037", {})
        if dc:
            print(f"{suc:<25} {dc['cantidad']:>6} ${dc['precio_promedio']:>11.2f} ${dc['total']:>14,.2f} {'$260 lista':>15}")

    Path("/home/tito/.openclaw/data/dc_precio_por_sucursal.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    browser.close()
print("\nOK")
