#!/usr/bin/env python3
"""Villas del Rey análisis completo: ticket promedio, ventas por hora, día 7-jun."""
import json, re
from datetime import datetime
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

    # 1. Ticket promedio por sucursal (reporte 3 — ventas mensuales)
    print("=== 1. TICKET PROMEDIO por sucursal Junio 2026 ===")
    ventas = json.loads(Path("/home/tito/.openclaw/data/ventas_junio_2026.json").read_text())
    for s, d in ventas["sucursales"].items():
        if d.get("ticket_promedio"):
            print(f"  {s:20s}  Ticket promedio: ${d['ticket_promedio']:.2f}")

    # 2. Ventas por hora Villas del Rey — reporte 15
    print("\n\n=== 2. VENTAS POR HORA — VILLAS DEL REY jun-jul 2026 ===")
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/15", wait_until="networkidle", timeout=45000)
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
    Path("/home/tito/.openclaw/data/sr_hora_VILLAS.txt").write_text(text)

    # Extraer horas — buscar patrones tipo "HH:00 hrs $X,XXX.XX" o filas con hora + venta
    horas_venta = {}
    lines = text.split("\n")
    for i, line in enumerate(lines):
        l = line.strip()
        # patrón: hora seguido de venta en próxima línea
        m = re.match(r"^(\d{1,2}):(\d{2})\s*hrs?", l)
        if m:
            h = int(m.group(1))
            # buscar venta en siguientes líneas
            for j in range(1, 4):
                if i+j < len(lines):
                    m2 = re.search(r"\$?([\d,]+\.\d{2})", lines[i+j].strip())
                    if m2:
                        horas_venta[h] = horas_venta.get(h, 0) + float(m2.group(1).replace(",",""))
                        break
        # patrón alterno: número solo (hora) seguido de $
        m3 = re.match(r"^(\d{1,2})\s*\$([\d,]+\.\d{2})", l)
        if m3:
            h = int(m3.group(1))
            if 6 <= h <= 23:
                horas_venta[h] = horas_venta.get(h, 0) + float(m3.group(2).replace(",",""))

    if horas_venta:
        for h in sorted(horas_venta):
            print(f"  {h:02d}:00  ${horas_venta[h]:>10,.2f}")
    else:
        # Si no encontré con regex, mostrar la parte relevante del texto
        print("  Regex falló. Muestro parte del texto:")
        for line in lines:
            if re.search(r"\d{1,2}[:h]", line) and "$" in line:
                print(f"    {line.strip()[:150]}")

    # 3. Ventas TODO junio para ver el DOMINGO 7-JUN
    print("\n\n=== 3. VENTAS DIARIAS COMPLETAS — VILLAS DEL REY (jun-jul) ===")
    # Ya tengo el texto de villas_descuentos
    if Path("/home/tito/.openclaw/data/villas_descuentos.txt").exists():
        text_desc = Path("/home/tito/.openclaw/data/villas_descuentos.txt").read_text()
        print("Detalle día por día (de reporte descuentos que incluye venta diaria):")
        totales = {}
        for line in text_desc.split("\n"):
            m = re.search(r"(\d{2}/\d{2}/\d{4}).*?\$([\d,]+\.\d+)\s+\$([\d,]+\.\d+)\s+([\d\.]+)\s*%", line)
            if m:
                dt = datetime.strptime(m.group(1), "%d/%m/%Y")
                venta = float(m.group(2).replace(",",""))
                dia_sem = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][dt.weekday()]
                marker = " ⚠️" if venta > 6000 else ""
                print(f"  {dt.strftime('%Y-%m-%d')} ({dia_sem})  ${venta:>8,.2f}{marker}")

    # 4. Ventas por hora del DOMINGO 7 DE JUNIO específicamente
    print("\n\n=== 4. VENTAS POR HORA — DOMINGO 7 JUNIO 2026 (día anómalo) ===")
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/15", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.locator('#FechaInicial').fill('07/06/2026')
    page.locator('#FechaFinal').fill('07/06/2026')
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
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(12000)
    text_dom = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/sr_domingo_7jun.txt").write_text(text_dom)
    # Mostrar el texto relevante
    for line in text_dom.split("\n"):
        l = line.strip()
        if "$" in l and len(l) < 100:
            print(f"    {l}")

    browser.close()
print("\nOK")
