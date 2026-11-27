#!/usr/bin/env python3
"""Análisis Villas del Rey — ventas por día y descuentos."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
VILLAS = "26983"

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

    # Reporte 14 — Ventas por día — Villas del Rey
    print("=== VILLAS DEL REY — Ventas diarias jun-jul 2026 ===")
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/14", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.locator('#FechaInicial').fill('01/06/2026')
    page.locator('#FechaFinal').fill('11/07/2026')
    page.evaluate(f"""() => {{
        const sel = document.querySelector('#ListaEmpresas');
        if (sel) {{
            for (const opt of sel.options) opt.selected = (opt.value === '{VILLAS}');
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
            if (window.jQuery) window.jQuery(sel).trigger('change');
        }}
    }}""")
    page.wait_for_timeout(1000)
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(15000)

    text = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/villas_ventas_diarias.txt").write_text(text)

    # Extraer líneas con fecha + venta
    from datetime import datetime
    ventas_dia = []
    for line in text.split("\n"):
        # dd/mm/yyyy [dia semana] $X,XXX.XX
        m = re.match(r"^(\d{2}/\d{2}/\d{4})\s+.*?\$?([\d,]+\.\d{2})", line.strip())
        if m:
            try:
                dt = datetime.strptime(m.group(1), "%d/%m/%Y")
                ventas_dia.append((dt, float(m.group(2).replace(",",""))))
            except: pass

    dias_semana = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    por_dia_semana = {d:{"total":0,"cuenta":0} for d in dias_semana}
    for dt, v in ventas_dia:
        d = dias_semana[dt.weekday()]
        por_dia_semana[d]["total"] += v
        por_dia_semana[d]["cuenta"] += 1

    print("\nVentas por día de la semana (promedio):")
    for d, dat in por_dia_semana.items():
        prom = dat["total"]/dat["cuenta"] if dat["cuenta"]>0 else 0
        print(f"  {d:12s}  {dat['cuenta']:>2} días  total ${dat['total']:>10,.2f}  prom/día ${prom:>8,.2f}")

    # Detalle día por día
    print("\nDetalle día por día:")
    for dt, v in sorted(ventas_dia):
        print(f"  {dt.strftime('%Y-%m-%d')} ({dias_semana[dt.weekday()][:3]})  ${v:>8,.2f}")

    # ---- Reporte 22 - Descuentos por sucursal ----
    print("\n\n=== DESCUENTOS aplicados — Villas del Rey ===")
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/22", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.locator('#FechaInicial').fill('01/06/2026')
    page.locator('#FechaFinal').fill('11/07/2026')
    page.evaluate(f"""() => {{
        const sel = document.querySelector('#ListaEmpresas');
        if (sel) {{
            for (const opt of sel.options) opt.selected = (opt.value === '{VILLAS}');
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
            if (window.jQuery) window.jQuery(sel).trigger('change');
        }}
    }}""")
    page.wait_for_timeout(1000)
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(12000)
    text2 = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/villas_descuentos.txt").write_text(text2)
    for line in text2.split("\n"):
        l = line.strip()
        if "$" in l and len(l) < 200 and l != "$0.00":
            print(f"  {l}")

    # ---- Cortesías (reporte 20) — para ver si Memo se regala hamburguesas ----
    print("\n\n=== CORTESÍAS — Villas del Rey ===")
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/20", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.locator('#FechaInicial').fill('01/06/2026')
    page.locator('#FechaFinal').fill('11/07/2026')
    page.evaluate(f"""() => {{
        const sel = document.querySelector('#ListaEmpresas');
        if (sel) {{
            for (const opt of sel.options) opt.selected = (opt.value === '{VILLAS}');
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
            if (window.jQuery) window.jQuery(sel).trigger('change');
        }}
    }}""")
    page.wait_for_timeout(1000)
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(12000)
    text3 = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/villas_cortesias.txt").write_text(text3)
    for line in text3.split("\n")[:60]:
        l = line.strip()
        if l and ("$" in l or "DOBLE" in l.upper() or "TITI" in l.upper() or "COMBO" in l.upper()):
            print(f"  {l}")

    browser.close()
print("\nOK")
