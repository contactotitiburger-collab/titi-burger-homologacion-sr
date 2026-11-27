#!/usr/bin/env python3
"""Reporte VENTAS POR ESTACIÓN (13) para un rango — para separar app vs física."""
import json, sys
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/estaciones_app_vs_fisica.json")

INI = sys.argv[1] if len(sys.argv) > 1 else "01/08/2026"
FIN = sys.argv[2] if len(sys.argv) > 2 else "01/09/2026"
IDS = ["12764", "13056", "22871", "22980", "23032", "26983"]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_context(viewport={"width": 1800, "height": 1400}).new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2500)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/13",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # setear fechas (mismo patrón que el reporte diario)
    for campo, val in (("#FechaInicial", INI), ("#FechaFinal", FIN)):
        page.evaluate("""([sel,v])=>{const el=document.querySelector(sel);
            if(!el) return; el.value=v;
            el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true}));}""", [campo, val])
    page.wait_for_timeout(300)
    # todas las empresas
    page.evaluate("""(ids)=>{const sel=document.querySelector('#ListaEmpresas');
        if(!sel) return;
        for(const o of sel.options) o.selected=ids.includes(o.value);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery) window.jQuery(sel).trigger('change');}""", IDS)
    page.wait_for_timeout(600)
    try:
        page.locator("#ActualizarReporte").first.click()
    except Exception:
        page.locator('text="Consultar"').first.click()
    page.wait_for_timeout(1000)
    try:
        page.wait_for_selector("#ExportarExcel", state="visible", timeout=180000)
    except Exception:
        pass
    page.wait_for_timeout(4000)

    # volcar TODAS las tablas visibles con su texto
    tablas = page.evaluate("""() => {
        const res = [];
        for (const t of document.querySelectorAll('table')) {
            const r = t.getBoundingClientRect();
            if (r.height > 0 && t.innerText.trim()) res.push(t.innerText);
        }
        return res;
    }""")
    OUT.write_text(json.dumps({"ini": INI, "fin": FIN, "tablas": tablas},
                              ensure_ascii=False, indent=1))
    print(f"=== rango {INI} -> {FIN} : {len(tablas)} tablas ===", flush=True)
    for i, t in enumerate(tablas):
        print(f"\n----- TABLA {i} -----\n{t[:3000]}", flush=True)
    b.close()
