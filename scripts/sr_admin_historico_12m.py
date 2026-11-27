#!/usr/bin/env python3
"""Extrae venta 12 meses (jul 2025 - jun 2026) por cada una de las 6 sucursales."""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/ventas_12m_por_sucursal.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

EMPRESAS = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
IDS = ["12764", "13056", "22871", "22980", "23032", "26983"]

MESES = [
    (2025, 7), (2025, 8), (2025, 9), (2025, 10), (2025, 11), (2025, 12),
    (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5), (2026, 6),
]

def set_year_month(page, year, month):
    """Setear año y mes en el reporte."""
    # Año: selector con opciones tipo 2024, 2025, 2026
    for s in page.query_selector_all("select"):
        vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
        if str(year) in vals and any(v in vals for v in ["2024","2025","2026"]) and "7" not in vals:
            s.select_option(str(year)); break
    # Mes
    for s in page.query_selector_all("select"):
        vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
        if "7" in vals and "12" in vals and "2025" not in vals:
            s.select_option(str(month)); break

def set_empresas(page, ids):
    page.evaluate("""(ids) => {
        for (const sel of document.querySelectorAll('select')) {
            const vals = [...sel.options].map(o => o.value);
            if (vals.includes('12764')) {
                for (const opt of sel.options) opt.selected = ids.includes(opt.value);
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
                return;
            }
        }
    }""", ids)

def parse_tab(page, name):
    """Click tab y extraer venta total."""
    try:
        tab = page.locator(f'a:has-text("{name}"), button:has-text("{name}"), [role="tab"]:has-text("{name}")').first
        tab.click()
        page.wait_for_timeout(1500)
        texto = page.evaluate("""() => {
            const tables = document.querySelectorAll('table');
            for (const t of tables) {
                const rect = t.getBoundingClientRect();
                if (rect.height > 0 && (t.innerText.includes('NÚMERO DE TICKETS') || t.innerText.includes('Número de tickets'))) {
                    return t.innerText;
                }
            }
            return '';
        }""")
        m = re.search(r"(\d[\d,]*)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)", texto)
        if m:
            return {
                "tickets": int(m.group(1).replace(",", "")),
                "ticket_promedio": float(m.group(2).replace(",", "")),
                "subtotal": float(m.group(3).replace(",", "")),
                "descuentos": float(m.group(4).replace(",", "")),
                "impuestos": float(m.group(5).replace(",", "")),
                "total": float(m.group(6).replace(",", "")),
                "con_propina": float(m.group(7).replace(",", "")),
            }
        return {"raw": texto[:200]}
    except Exception as e:
        return {"error": str(e)}


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400})
    page = ctx.new_page()

    print("[login]", flush=True)
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    print("[ir a reporte]", flush=True)
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/3", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    resultados_por_mes = {}

    for year, month in MESES:
        key = f"{year}-{month:02d}"
        print(f"\n=== {key} ===", flush=True)
        try:
            set_year_month(page, year, month)
            page.wait_for_timeout(500)
            set_empresas(page, IDS)
            page.wait_for_timeout(500)
            page.locator('text="Consultar"').first.click()
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(6000)

            mes_data = {}
            for name in EMPRESAS:
                d = parse_tab(page, name)
                mes_data[name] = d
                if "total" in d:
                    print(f"  {name:20s}: ${d['total']:>12,.2f}  ({d['tickets']} tickets)", flush=True)
                else:
                    print(f"  {name:20s}: (sin datos)", flush=True)
            resultados_por_mes[key] = mes_data

            # Guardar parcial cada mes
            OUT.write_text(json.dumps({"meses": resultados_por_mes}, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ERROR mes {key}: {e}", flush=True)
            resultados_por_mes[key] = {"error": str(e)}
            OUT.write_text(json.dumps({"meses": resultados_por_mes}, indent=2, ensure_ascii=False))

    print(f"\n\n[LISTO] Guardado en {OUT}", flush=True)
    browser.close()
