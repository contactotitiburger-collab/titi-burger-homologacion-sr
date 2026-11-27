#!/usr/bin/env python3
"""Extrae venta mensual por sucursal (carreta) para el maximo historico disponible.
Objetivo: ene-2024 -> ago-2026. Prueba tambien 2023 (si el selector lo ofrece).
Basado en sr_admin_historico_12m.py (NO modifica el original)."""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/ventas_mensual_3anios.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

EMPRESAS = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
IDS = ["12764", "13056", "22871", "22980", "23032", "26983"]

# Objetivo: probar desde 2023 hasta ago-2026. Los meses cuyo anio no exista en el
# selector se marcan "anio_no_disponible" y se continua.
MESES = []
for y in (2022, 2023, 2024, 2025):
    for m in range(1, 13):
        MESES.append((y, m))
for m in range(1, 9):  # ene..ago 2026
    MESES.append((2026, m))

# Resume: si ya existe OUT, no re-consultar meses ya guardados con datos.
YA = {}
if OUT.exists():
    try:
        _prev = json.loads(OUT.read_text())
        YA = _prev.get("meses", {})
    except Exception:
        YA = {}

def ya_tiene_datos(key):
    v = YA.get(key)
    if not isinstance(v, dict):
        return False
    # tiene datos si alguna empresa trae total, o si esta marcado anio_no_disponible
    if v.get("status") == "anio_no_disponible":
        return True
    for e in EMPRESAS:
        cell = v.get(e)
        if isinstance(cell, dict) and "total" in cell:
            return True
    return False


def find_year_select(page):
    """Devuelve (handle, valores_disponibles) del selector de anio, o (None, [])."""
    for s in page.query_selector_all("select"):
        vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
        # El selector de anio contiene anios (2024/2025/2026) y NO contiene meses (no "7")
        if any(v in vals for v in ["2024", "2025", "2026"]) and "7" not in vals:
            return s, vals
    return None, []


def set_year_month(page, year, month):
    """Setea anio y mes. Devuelve True si el anio estaba disponible, False si no."""
    ysel, yvals = find_year_select(page)
    if ysel is None or str(year) not in yvals:
        return False
    ysel.select_option(str(year))
    # Mes: selector con meses 1..12 (contiene "7" y "12", no contiene "2025")
    for s in page.query_selector_all("select"):
        vals = [o.get_attribute("value") for o in s.query_selector_all("option")]
        if "7" in vals and "12" in vals and "2025" not in vals:
            s.select_option(str(month)); break
    return True


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
                if (rect.height > 0 && (t.innerText.includes('NÚMERO DE TICKETS') || t.innerText.includes('NUMERO DE TICKETS') || t.innerText.includes('Número de tickets') || t.innerText.includes('Numero de tickets'))) {
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

    # Diagnostico: reportar anios disponibles en el selector
    _, yvals = find_year_select(page)
    anios_disp = sorted(v for v in yvals if v and v.isdigit())
    print(f"[anios disponibles en selector]: {anios_disp}", flush=True)

    resultados_por_mes = dict(YA)  # arranca con lo ya guardado (resume)

    for year, month in MESES:
        key = f"{year}-{month:02d}"
        if ya_tiene_datos(key):
            print(f"\n=== {key} === (ya extraido, skip)", flush=True)
            continue
        print(f"\n=== {key} ===", flush=True)
        try:
            ok = set_year_month(page, year, month)
            if not ok:
                print(f"  anio {year} NO disponible en selector; se omite", flush=True)
                resultados_por_mes[key] = {"status": "anio_no_disponible"}
                OUT.write_text(json.dumps({"anios_disponibles": anios_disp, "meses": resultados_por_mes}, indent=2, ensure_ascii=False))
                continue
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
            OUT.write_text(json.dumps({"anios_disponibles": anios_disp, "meses": resultados_por_mes}, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ERROR mes {key}: {e}", flush=True)
            resultados_por_mes[key] = {"error": str(e)}
            OUT.write_text(json.dumps({"anios_disponibles": anios_disp, "meses": resultados_por_mes}, indent=2, ensure_ascii=False))

    print(f"\n\n[LISTO] Guardado en {OUT}", flush=True)
    browser.close()
