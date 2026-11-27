#!/usr/bin/env python3
"""Consulta ventas mensuales de un mes/año dado. Uso: python3 sr_admin_mes.py 5 2026"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())

MES = sys.argv[1] if len(sys.argv) > 1 else "5"
ANIO = sys.argv[2] if len(sys.argv) > 2 else "2026"
NOMBRE_MES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
              "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][int(MES)]

OUT = Path(f"/home/tito/.openclaw/data/ventas_{NOMBRE_MES}_{ANIO}.json")

EMPRESAS = {
    "12764": "FOVISSTE",
    "13056": "MONTECARLO",
    "22871": "SAN MARCOS",
    "22980": "HACIENDA DEL RÍO",
    "23032": "CURTO",
    "26983": "VILLAS DEL REY",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1200})
    page = ctx.new_page()

    # Login
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    print(f"\n===== VENTAS {NOMBRE_MES.upper()} {ANIO} =====\n", flush=True)
    resultados = {}
    for eid, ename in EMPRESAS.items():
        page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/3", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)

        # Mes
        for s in page.query_selector_all("select"):
            vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
            if "7" in vals and "12" in vals:
                s.select_option(MES); break
        # Año
        for s in page.query_selector_all("select"):
            vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
            if "2025" in vals and "2024" in vals:
                s.select_option(ANIO); break

        # Solo esta empresa
        page.evaluate("""(id) => {
            for (const sel of document.querySelectorAll('select')) {
                const vals = [...sel.options].map(o => o.value);
                if (vals.includes('12764')) {
                    for (const opt of sel.options) opt.selected = (opt.value === id);
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    if (window.jQuery) window.jQuery(sel).trigger('change');
                    return;
                }
            }
        }""", eid)

        page.locator('text="Consultar"').first.click()
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(5000)

        tables_text = page.eval_on_selector_all("table", "els => els.map(t => t.innerText)")
        found = False
        for txt in tables_text:
            m = re.search(r"(\d[\d,]*)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)", txt)
            if m and "TICKETS" in txt.upper():
                tickets = int(m.group(1).replace(",", ""))
                prom = float(m.group(2).replace(",", ""))
                subtotal = float(m.group(3).replace(",", ""))
                descuentos = float(m.group(4).replace(",", ""))
                impuestos = float(m.group(5).replace(",", ""))
                total = float(m.group(6).replace(",", ""))
                con_prop = float(m.group(7).replace(",", ""))
                resultados[ename] = {
                    "id": eid, "tickets": tickets, "ticket_promedio": prom,
                    "subtotal": subtotal, "descuentos": descuentos,
                    "impuestos": impuestos, "total": total, "con_propina": con_prop,
                }
                print(f"{ename:20s}: {tickets:5d} tickets  prom ${prom:>7.2f}  TOTAL ${total:>12,.2f}", flush=True)
                found = True
                break
        if not found:
            resultados[ename] = {"id": eid, "error": "no match / sin datos"}
            print(f"{ename:20s}: sin datos en {NOMBRE_MES} {ANIO}", flush=True)

    total_venta = sum(r.get("total", 0) for r in resultados.values() if isinstance(r.get("total"), (int, float)))
    total_tickets = sum(r.get("tickets", 0) for r in resultados.values() if isinstance(r.get("tickets"), int))
    print(f"\n{'='*70}", flush=True)
    print(f"TOTAL {NOMBRE_MES} {ANIO}: ${total_venta:,.2f}  ({total_tickets:,} tickets)", flush=True)

    OUT.write_text(json.dumps({
        "mes": f"{NOMBRE_MES} {ANIO}",
        "consultado": "2026-07-10",
        "sucursales": resultados,
        "total_venta": total_venta,
        "total_tickets": total_tickets,
    }, indent=2, ensure_ascii=False))
    print(f"Guardado en {OUT}", flush=True)

    browser.close()
