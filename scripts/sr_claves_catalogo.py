#!/usr/bin/env python3
"""Jala el catálogo de productos de SR (reporte 7) con sus CLAVES (ID interno de Soft Restaurant).
Rango amplio (12 meses) + 6 sucursales para capturar todo lo activo. Descarga Excel y extrae CLAVE+DESCRIPCION."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
DOWNLOAD_DIR = Path("/home/tito/.openclaw/downloads"); DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUT = Path("/home/tito/.openclaw/data/sr_claves_verif.json")
IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400}, accept_downloads=True)
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2000)
    print("[login ok]", flush=True)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    page.locator('#FechaInicial').fill('01/01/2022')
    page.locator('#FechaFinal').fill('07/08/2026')
    # Subir "Cantidad" con el botón '+' (touchspin paso 5) — ponerlo por JS no pega en la consulta
    TARGET = 1200
    inc = page.locator('button.btn-increment, .input-group-append button, button:has-text("+")').first
    clicks = 0
    while clicks < 260:
        val = page.evaluate("() => { const c=document.querySelector('#NumElementosTop'); return c?parseInt(c.value||'0'):0; }")
        if val >= TARGET: break
        try: inc.click()
        except Exception as e: print("click + falló:", str(e)[:80]); break
        clicks += 1; page.wait_for_timeout(50)
    val = page.evaluate("() => { const c=document.querySelector('#NumElementosTop'); return c?c.value:'?'; }")
    print(f"[cantidad={val} tras {clicks} clicks]", flush=True)
    page.evaluate("""(ids) => { const sel=document.querySelector('#ListaEmpresas');
        if(sel){ for(const o of sel.options) o.selected=ids.includes(o.value);
        sel.dispatchEvent(new Event('change',{bubbles:true})); if(window.jQuery) window.jQuery(sel).trigger('change'); } }""", IDS)
    page.wait_for_timeout(1000)
    print("[filtros puestos] consultando...", flush=True)

    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=120000)
    page.wait_for_timeout(25000)

    with page.expect_download(timeout=120000) as di:
        page.locator('a:has-text("EXCEL"), button:has-text("EXCEL")').first.click()
    dest = DOWNLOAD_DIR / "sr_catalogo_max.xlsx"
    di.value.save_as(str(dest))
    print(f"[excel descargado] {dest} ({dest.stat().st_size} bytes)", flush=True)
    browser.close()

# --- parsear xlsx ---
import openpyxl
wb = openpyxl.load_workbook(dest, read_only=True, data_only=True)
ws = wb.active
claves = {}
header_seen = False
for row in ws.iter_rows(values_only=True):
    if not row or len(row) < 3: continue
    # columnas: [Empresa, Clave, Descripción, Cantidad, ...]
    empresa = (str(row[0]).strip() if row[0] else "")
    clave = (str(row[1]).strip() if row[1] else "")
    desc = (str(row[2]).strip() if row[2] else "")
    if empresa.lower() == "totales": continue
    if clave and clave.replace(".0","").isdigit() and desc:
        c = clave.replace(".0","")
        if c not in claves or len(desc) > len(claves[c]):
            claves[c] = desc

OUT.write_text(json.dumps(claves, ensure_ascii=False, indent=2))
print(f"[LISTO] {len(claves)} claves únicas -> {OUT}", flush=True)
# resumen por prefijo
from collections import Counter
pref = Counter(c[:2] for c in claves)
print("Por prefijo:", dict(sorted(pref.items())), flush=True)
