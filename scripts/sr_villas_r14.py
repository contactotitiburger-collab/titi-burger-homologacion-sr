#!/usr/bin/env python3
"""Reporte 14 Ventas por día — Villas del Rey rango completo."""
import json, re
from datetime import datetime, timedelta
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
    ctx = browser.new_context(viewport={"width": 1800, "height": 1600})
    page = ctx.new_page()
    login(page)

    # Reporte 14
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
    # Aumentar registros por página al máximo
    page.evaluate("""() => {
        const s = document.querySelector('select[name="registrosPorPagina"], select#registrosPorPagina');
        if (s) s.value = '100';
    }""")
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(15000)

    # Ver todas las páginas
    # Cambiar "Mostrar N por página" a 100
    try:
        # buscar el dropdown y setear a 100
        page.evaluate("""() => {
            const dropdowns = document.querySelectorAll('select');
            for (const d of dropdowns) {
                const vals = [...d.options].map(o => o.value);
                if (vals.includes('100') && vals.includes('10') && vals.includes('25')) {
                    d.value = '100';
                    d.dispatchEvent(new Event('change', {bubbles: true}));
                    break;
                }
            }
        }""")
        page.wait_for_timeout(3000)
    except: pass

    text = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/villas_r14_completo.txt").write_text(text)

    # Extraer fechas + ventas
    ventas = {}
    for line in text.split("\n"):
        l = line.strip()
        # Formato típico: DD/MM/YYYY <día> <folios> ... $venta
        m = re.match(r"^(\d{2}/\d{2}/\d{4})\s+([A-ZÁa-zá]+)\s+(\d+)\s+\d+\s+\$([\d,]+\.\d{2})", l)
        if m:
            dt = datetime.strptime(m.group(1), "%d/%m/%Y")
            dia_nombre = m.group(2)
            folios = int(m.group(3))
            venta = float(m.group(4).replace(",",""))
            ventas[dt] = (dia_nombre, folios, venta)

    print(f"\n=== VILLAS DEL REY — TODAS las ventas jun-jul 2026 ===")
    print(f"{'Fecha':<15} {'Día':<12} {'Folios':>6} {'Venta':>12}")
    inicio = datetime(2026, 6, 8)
    fin = datetime(2026, 7, 10)
    dias_es = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
    d = inicio
    dias_abiertos = 0
    dias_cerrados = 0
    total_venta = 0
    total_folios = 0
    while d <= fin:
        if d in ventas:
            dia, folios, v = ventas[d]
            marker = " ⚠️" if v > 6000 else ""
            print(f"  {d.strftime('%Y-%m-%d')} {dia:<12} {folios:>6} ${v:>10,.2f}{marker}")
            dias_abiertos += 1
            total_venta += v
            total_folios += folios
        else:
            print(f"  {d.strftime('%Y-%m-%d')} {dias_es[d.weekday()]:<12} 🔴 SIN VENTAS")
            dias_cerrados += 1
        d += timedelta(days=1)

    print(f"\n{'='*60}")
    print(f"Total días período (8-jun a 10-jul): {(fin-inicio).days + 1}")
    print(f"Días abiertos: {dias_abiertos}")
    print(f"Días cerrados: {dias_cerrados}")
    print(f"Total folios: {total_folios}")
    print(f"Total venta: ${total_venta:,.2f}")

    browser.close()
