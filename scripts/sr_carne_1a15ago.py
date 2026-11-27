#!/usr/bin/env python3
"""Productos mas vendidos (reporte 7) por sucursal, 1-15 ago 2026.
Guarda texto crudo por sucursal para mapear patties a mano. NO inventa."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/carne_1a15ago")
OUT.mkdir(parents=True, exist_ok=True)

SUC = {
    "12764": "Montejano",
    "13056": "Montecarlo",
    "22980": "Hacienda_del_Rio",
    "22871": "San_Marcos",
    "23032": "Cine_Curto",
    "26983": "Villas_del_Rey",
}
F_INI = "01/08/2026"
F_FIN = "16/08/2026"  # fecha final exclusiva -> incluye 15 ago

def login(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

def pull(page, eid):
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('#FechaInicial').fill(F_INI)
    page.locator('#FechaFinal').fill(F_FIN)
    page.evaluate("""(eid) => {
        const sel = document.querySelector('#ListaEmpresas');
        if (sel) {
            for (const opt of sel.options) opt.selected = (opt.value === eid);
            sel.dispatchEvent(new Event('change', {bubbles: true}));
            if (window.jQuery) window.jQuery(sel).trigger('change');
        }
    }""", eid)
    page.wait_for_timeout(1000)
    # Spinner custom: #NumElementosTop esta oculto; teclear en el input de texto visible
    vis = page.locator('#NumElementosTop').locator('xpath=following-sibling::div//input[@type="text"]')
    vis.click(); vis.fill('1500'); vis.press('Enter'); page.wait_for_timeout(300); vis.press('Tab')
    page.wait_for_timeout(600)
    hidden = page.evaluate("() => document.querySelector('#NumElementosTop').value")
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(18000)
    try:
        page.evaluate("""() => {
            const s = document.querySelector('select[name$="_length"]');
            if (s) { s.value='100'; s.dispatchEvent(new Event('change',{bubbles:true})); }
        }""")
        page.wait_for_timeout(2500)
    except Exception:
        pass
    txt = page.evaluate("() => document.body.innerText")
    return txt, hidden, hidden

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1200})
    page = ctx.new_page()
    login(page)
    print("login OK", flush=True)
    for eid, name in SUC.items():
        try:
            txt, v, v2 = pull(page, eid)
            f = OUT / f"{name}_{eid}.txt"
            f.write_text(txt)
            print(f"OK {name} ({eid}) -> {len(txt)} chars | top_set={v} top_read={v2}", flush=True)
        except Exception as e:
            print(f"FAIL {name} ({eid}): {e}", flush=True)
    browser.close()
print("DONE", flush=True)
