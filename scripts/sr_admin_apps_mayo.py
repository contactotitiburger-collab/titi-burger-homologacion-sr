#!/usr/bin/env python3
"""Busca desglose por app (Uber/Rappi/DiDi) desde varios reportes con rango mayo 2026."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

IDS = ["12764","13056","22871","22980","23032","26983"]

def login_and_setup(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

def probar_reporte(page, rep_id, nombre):
    page.goto(f"https://admin.softrestaurant.com/analytics/reportes/Consultar/{rep_id}", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    # fechas mayo
    try:
        page.evaluate("""() => {
            const f1 = document.querySelector('#FechaInicial');
            const f2 = document.querySelector('#FechaFinal');
            if (f1) f1.value = '01/05/2026';
            if (f2) f2.value = '31/05/2026';
        }""")
    except: pass
    # mes/año
    for s in page.query_selector_all("select"):
        try:
            vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
            if "7" in vals and "12" in vals: s.select_option("5")
            if "2025" in vals and "2026" in vals: s.select_option("2026")
        except: pass
    # empresas
    try:
        page.evaluate("""(ids) => {
            const sel = document.querySelector('#ListaEmpresas');
            if (sel) {
                for (const opt of sel.options) opt.selected = ids.includes(opt.value);
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
            } else {
                // multi-select genérico
                for (const s of document.querySelectorAll('select')) {
                    const vals = [...s.options].map(o => o.value);
                    if (vals.includes('12764')) {
                        for (const opt of s.options) opt.selected = ids.includes(opt.value);
                        s.dispatchEvent(new Event('change', {bubbles: true}));
                        if (window.jQuery) window.jQuery(s).trigger('change');
                        break;
                    }
                }
            }
        }""", IDS)
    except: pass
    page.wait_for_timeout(1000)
    # Consultar
    try:
        btn = page.locator('#ActualizarReporte, text="Consultar"').first
        btn.click()
    except: pass
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(6000)
    (SCREEN_DIR / f"r{rep_id}_{nombre}_mayo.html").write_text(page.content())
    page.screenshot(path=str(SCREEN_DIR / f"r{rep_id}_{nombre}_mayo.png"), full_page=True)
    tables = page.eval_on_selector_all("table", "els => els.map(t => t.innerText)")
    return tables

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400})
    page = ctx.new_page()
    login_and_setup(page)

    for rep_id, nombre in [(1, "ventas_periodo"), (11, "grupos_productos"), (19, "temporadas"), (21, "restcard"), (22, "descuentos_sucursal")]:
        print(f"\n===== Reporte {rep_id} — {nombre} =====", flush=True)
        try:
            tables = probar_reporte(page, rep_id, nombre)
            for i, t in enumerate(tables):
                t2 = t.strip()
                if len(t2) > 30 and ("UBER" in t2.upper() or "RAPPI" in t2.upper() or "DIDI" in t2.upper() or "DOMICILIO" in t2.upper() or "SERVICIO" in t2.upper()):
                    print(f"--- Tabla {i} (con apps/servicios) ---", flush=True)
                    print(t2[:1500], flush=True)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)

    browser.close()
