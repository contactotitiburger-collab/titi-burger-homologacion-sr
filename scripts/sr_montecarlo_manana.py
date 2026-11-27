#!/usr/bin/env python3
"""Ventas de Montecarlo por hora — últimos 30 días — para evaluar turno mañana."""
import json, re
from datetime import date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
MONTECARLO_ID = "13056"

hoy = date.today()
hace_30 = hoy - timedelta(days=30)
DESDE = hace_30.strftime("%d/%m/%Y")
HASTA = hoy.strftime("%d/%m/%Y")
print(f"Rango: {DESDE} a {HASTA}", flush=True)


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

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/15",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.locator('#FechaInicial').fill(DESDE)
    page.locator('#FechaFinal').fill(HASTA)
    page.evaluate("""(id) => {
        const sel = document.querySelector('#ListaEmpresas');
        if (sel) {
            for (const opt of sel.options) opt.selected = (opt.value === id);
            sel.dispatchEvent(new Event('change', {bubbles: true}));
            if (window.jQuery) window.jQuery(sel).trigger('change');
        }
    }""", MONTECARLO_ID)
    page.wait_for_timeout(1000)
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(20000)

    # Cambiar a 100 registros por página (default es 10 — nos perdemos horas)
    try:
        page.select_option('select[name*="length"]', "100")
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"(no pude cambiar a 100: {e})")

    text = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/sr_montecarlo_hora_ultimo_mes.txt").write_text(text)
    print("Reporte capturado.", flush=True)

    # Extraer horas
    horas = {}
    for line in text.split("\n"):
        m = re.match(r"^(\d{1,2})(?::\d{2})?\s+\$?([\d,]+\.\d{2})", line.strip())
        if m and 0 <= int(m.group(1)) <= 23:
            h = int(m.group(1))
            v = float(m.group(2).replace(",",""))
            horas[h] = horas.get(h, 0) + v

    print(f"\n=== VENTAS POR HORA — MONTECARLO {DESDE} a {HASTA} ===")
    total = 0
    for h in sorted(horas):
        v = horas[h]
        total += v
        print(f"  {h:>2}:00  ${v:>12,.2f}")
    print(f"\nTOTAL: ${total:,.2f}")

    manana = sum(v for h, v in horas.items() if 6 <= h <= 13)   # 6am a 1:59pm
    tarde = sum(v for h, v in horas.items() if 14 <= h <= 23)
    print(f"\nMañana (6am-2pm):  ${manana:,.2f}  ({100*manana/total:.1f}%)")
    print(f"Tarde  (2pm-fin):  ${tarde:,.2f}  ({100*tarde/total:.1f}%)")

    browser.close()

    Path("/tmp/montecarlo_manana.json").write_text(json.dumps({
        "rango": f"{DESDE} a {HASTA}",
        "por_hora": horas,
        "total": total,
        "manana_6a14": manana,
        "tarde_14a24": tarde,
    }))
