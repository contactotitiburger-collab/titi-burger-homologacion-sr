#!/usr/bin/env python3
"""Extrae venta de junio 2026 por cada una de las 6 sucursales."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")
OUT = Path("/home/tito/.openclaw/data/ventas_junio_2026.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

EMPRESAS = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
IDS = ["12764", "13056", "22871", "22980", "23032", "26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400})
    page = ctx.new_page()

    # Login + reporte + junio + 6 empresas
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/3", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # Junio
    for s in page.query_selector_all("select"):
        vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
        if "7" in vals and "12" in vals:
            s.select_option("6"); break

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
    }""", IDS)

    page.locator('text="Consultar"').first.click()
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(8000)

    # Iterar sobre cada tab de sucursal — click y capturar tabla
    resultados = {}
    for name in EMPRESAS:
        try:
            # click en tab con ese nombre
            tab = page.locator(f'a:has-text("{name}"), button:has-text("{name}"), [role="tab"]:has-text("{name}")').first
            tab.click()
            page.wait_for_timeout(1500)
            # capturar tabla visible
            texto = page.evaluate("""(sucName) => {
                // Buscar tabs activas y la tabla asociada
                const tables = document.querySelectorAll('table');
                for (const t of tables) {
                    const rect = t.getBoundingClientRect();
                    if (rect.height > 0 && t.innerText.includes('NÚMERO DE TICKETS') || t.innerText.includes('Número de tickets')) {
                        return t.innerText;
                    }
                }
                return '';
            }""", name)
            # parse
            m = re.search(r"(\d[\d,]*)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)", texto)
            if m:
                tickets = int(m.group(1).replace(",", ""))
                ticket_prom = float(m.group(2).replace(",", ""))
                subtotal = float(m.group(3).replace(",", ""))
                descuentos = float(m.group(4).replace(",", ""))
                impuestos = float(m.group(5).replace(",", ""))
                total = float(m.group(6).replace(",", ""))
                con_propina = float(m.group(7).replace(",", ""))
                resultados[name] = {
                    "tickets": tickets,
                    "ticket_promedio": ticket_prom,
                    "subtotal": subtotal,
                    "descuentos": descuentos,
                    "impuestos": impuestos,
                    "total": total,
                    "con_propina": con_propina,
                }
                print(f"{name:20s}: {tickets:5d} tickets, prom ${ticket_prom:>7.2f}, TOTAL ${total:>12,.2f}", flush=True)
            else:
                print(f"{name}: no parse (texto:{texto[:200]!r})", flush=True)
                resultados[name] = {"raw": texto}
        except Exception as e:
            print(f"{name}: ERROR {e}", flush=True)
            resultados[name] = {"error": str(e)}

    total_venta = sum(r.get("total", 0) for r in resultados.values() if isinstance(r.get("total"), (int, float)))
    total_tickets = sum(r.get("tickets", 0) for r in resultados.values() if isinstance(r.get("tickets"), int))
    print(f"\n{'='*60}", flush=True)
    print(f"TOTAL 6 SUCURSALES junio 2026: ${total_venta:,.2f}  ({total_tickets:,} tickets)", flush=True)

    OUT.write_text(json.dumps({"mes": "junio 2026", "sucursales": resultados, "total": total_venta, "tickets": total_tickets}, indent=2, ensure_ascii=False))
    print(f"Guardado en {OUT}", flush=True)

    browser.close()
