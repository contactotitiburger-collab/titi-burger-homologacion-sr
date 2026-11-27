#!/usr/bin/env python3
"""Villas del Rey — todas las hamburguesas vendidas y consumo de carne esperado."""
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
    ctx = browser.new_context(viewport={"width": 1800, "height": 1200})
    page = ctx.new_page()
    login(page)

    # Reporte 7 — todos los productos Villas del Rey — período 08/06 al 10/07 (rango de envíos que dio Staff)
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.locator('#FechaInicial').fill('08/06/2026')
    page.locator('#FechaFinal').fill('10/07/2026')
    page.evaluate("""() => {
        const c = document.querySelector('#NumElementosTop');
        if (c) {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(c, '1500');
            c.dispatchEvent(new Event('input', {bubbles: true}));
            c.dispatchEvent(new Event('change', {bubbles: true}));
        }
    }""")
    page.evaluate(f"""() => {{
        const sel = document.querySelector('#ListaEmpresas');
        if (sel) {{
            for (const opt of sel.options) opt.selected = (opt.value === '{VILLAS}');
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
            if (window.jQuery) window.jQuery(sel).trigger('change');
        }}
    }}""", )
    page.wait_for_timeout(1000)
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(20000)

    text = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/villas_todos_productos.txt").write_text(text)

    # Extraer TODOS los productos con "TITI" en el nombre — son hamburguesas
    productos = []
    lines = text.split("\n")
    for i in range(len(lines)-4):
        joined = " ".join(lines[i:i+6]).strip()
        m = re.search(r"(\d{5})\s+([A-Z0-9#\.\s\-]+)\s+([\d,]+)\.\d+\s+\$([\d,]+\.\d+)\s+\$([\d,]+\.\d+)\s+\$([\d,]+\.\d+)", joined)
        if m:
            clave = m.group(1)
            desc = m.group(2).strip()
            cant = int(m.group(3).replace(",",""))
            # solo hamburguesas (TITI + no COCA/PAPAS/etc)
            if ("TITI" in desc.upper() or "HAMBUR" in desc.upper()) and cant > 0:
                # evitar duplicados
                if not any(p["clave"] == clave for p in productos):
                    productos.append({"clave": clave, "producto": desc, "cantidad": cant})

    # Clasificar por # patties (asumido)
    UNA_CARNE_KWS = ["CLASICA","CLÁSICA","TOCINO","PASTOR","RANCHER","QUESO","HAWAII","JAMAIC","NORTEÑ","ROMANA","MICH","BBQ","CAMP"]
    DOS_CARNES_KWS = ["DOBLE"]
    TRES_CARNES_KWS = ["TRIPLE"]

    print(f"\n=== HAMBURGUESAS VENDIDAS EN VILLAS DEL REY (8-jun al 10-jul 2026) ===")
    total_carnes = 0
    for p in productos:
        d = p["producto"].upper()
        if any(k in d for k in TRES_CARNES_KWS):
            carnes = p["cantidad"] * 3
            tipo = "3 patties"
        elif any(k in d for k in DOS_CARNES_KWS):
            carnes = p["cantidad"] * 2
            tipo = "2 patties"
        elif any(k in d for k in UNA_CARNE_KWS) or "COMBO" in d:
            carnes = p["cantidad"] * 1
            tipo = "1 patty"
        else:
            carnes = 0
            tipo = "(?)"
        total_carnes += carnes
        print(f"  {p['clave']} {p['producto']:<50s} {p['cantidad']:>4}u  {tipo:>10s}  = {carnes:>4} carnes")

    print(f"\n{'='*70}")
    print(f"TOTAL CARNES CONSUMIDAS EN VENTAS: {total_carnes}")
    print(f"CARNES ENVIADAS DESDE COCINA:      780")
    print(f"DIFERENCIA (posible merma/robo):   {780 - total_carnes}")

    # Guardar
    Path("/home/tito/.openclaw/data/villas_carne_analisis.json").write_text(json.dumps({
        "productos": productos,
        "carnes_consumidas": total_carnes,
        "carnes_enviadas": 780,
        "diferencia": 780 - total_carnes,
    }, indent=2, ensure_ascii=False))

    browser.close()
print("\nOK")
