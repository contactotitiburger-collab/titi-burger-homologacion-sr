#!/usr/bin/env python3
"""DIAGNÓSTICO: ver columnas/encabezados del reporte Consultar/1 para un día,
para saber si trae desglose por forma de pago (efectivo/tarjeta/apps)."""
import json, sys
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SUC_ID = "12764"   # L Montejano (la que más vende)
FECHA = sys.argv[1] if len(sys.argv) > 1 else "07/09/2026"

d = datetime.strptime(FECHA, "%d/%m/%Y")
fecha_fin = (d + timedelta(days=1)).strftime("%d/%m/%Y")

with sync_playwright() as p:
    nav = p.chromium.launch(headless=True)
    page = nav.new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2500)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/1",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    for campo, val in (("#FechaInicial", FECHA), ("#FechaFinal", fecha_fin)):
        page.evaluate("""([sel,v])=>{const el=document.querySelector(sel);
            el.value=v; el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true})); el.blur&&el.blur();}""",
            [campo, val])
    page.wait_for_timeout(300)
    page.evaluate(
        """(id)=>{const sel=document.querySelector('#ListaEmpresas');
        for(const o of sel.options) o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery) window.jQuery(sel).trigger('change');}""", SUC_ID)
    page.wait_for_timeout(600)
    page.locator("#ActualizarReporte").first.click()
    try:
        page.wait_for_selector("#ExportarExcel", state="visible", timeout=180000)
    except Exception:
        print("TIMEOUT esperando reporte")
    page.wait_for_timeout(3000)

    # Volcar TODAS las tablas con su innerText
    tablas = page.evaluate("""() => {
        const out = [];
        for (const t of document.querySelectorAll('table')) {
            out.push((t.innerText||'').trim());
        }
        return out;
    }""")
    for i, t in enumerate(tablas):
        if not t:
            continue
        print(f"\n========== TABLA {i} ==========")
        print(t[:2000])
    nav.close()
