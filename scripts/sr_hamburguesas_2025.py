#!/usr/bin/env python3
"""Baja productos vendidos por sucursal en 2025 completo — filtra hamburguesas."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT_DIR = Path("/home/tito/.openclaw/data/sr_hamburguesas_2025")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUCS = {
    "12764":"FOVISSTE",
    "13056":"MONTECARLO",
    "22871":"SAN MARCOS",
    "22980":"HACIENDA DEL RIO",
    "23032":"CURTO",
    "26983":"VILLAS DEL REY",
}

def login(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
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

    resultados = {}
    for suc_id, suc_nombre in SUCS.items():
        print(f"\n=== {suc_nombre} — año 2025 ===", flush=True)
        page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
                  wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)
        page.locator('#FechaInicial').fill('01/07/2025')
        page.locator('#FechaFinal').fill('31/07/2025')
        # cantidad al máx
        page.evaluate("""() => {
            const c = document.querySelector('#NumElementosTop');
            if (c) {
                const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                s.call(c, '2000');
                c.dispatchEvent(new Event('input', {bubbles: true}));
                c.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""")
        # sucursal
        page.evaluate("""(id) => {
            const sel = document.querySelector('#ListaEmpresas');
            if (sel) {
                for (const opt of sel.options) opt.selected = (opt.value === id);
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
            }
        }""", suc_id)
        page.wait_for_timeout(1000)
        page.locator('#ActualizarReporte').first.click()
        page.wait_for_load_state("networkidle", timeout=120000)
        page.wait_for_timeout(20000)
        try:
            page.select_option('select[name*="length"]', "100")
            page.wait_for_timeout(3000)
        except Exception:
            pass

        text = page.evaluate("() => document.body.innerText")
        Path(OUT_DIR / f"{suc_nombre.replace(' ','_')}.txt").write_text(text)

        # Parsear filas: "producto  cantidad  precio..."
        # Formato típico del reporte 7: nombre y luego varios números
        hamb = []
        for line in text.split("\n"):
            L = line.strip()
            if not L: continue
            # buscar nombre con "HAMBURGUESA" (variante nombre)
            if re.search(r"(HAMBURGUES|BURGER)", L, re.IGNORECASE):
                # extraer números — el primer entero después del nombre suele ser cantidad
                # Formato ejemplo: "HAMBURGUESA SENCILLA  1,234  $12,345.00 ..."
                m = re.search(r"([A-ZÁÉÍÓÚÑ0-9\s\-\.\/\,]+?)\s+([\d,]+(?:\.\d+)?)\s+\$", L)
                if m:
                    prod = m.group(1).strip()
                    cant = float(m.group(2).replace(",",""))
                    hamb.append({"producto": prod, "cantidad": cant, "line": L[:200]})

        # Si no encontramos con esa regex, buscar todas las líneas con "HAMBURGUES"/"BURGER"
        if not hamb:
            for line in text.split("\n"):
                L = line.strip()
                if re.search(r"(HAMBURGUES|BURGER)", L, re.IGNORECASE):
                    hamb.append({"producto": L[:120], "cantidad": None, "line": L})

        print(f"  Hamburguesas encontradas: {len(hamb)}", flush=True)
        for h in hamb[:5]:
            print(f"    {h}")
        resultados[suc_nombre] = hamb

    browser.close()

    Path("/tmp/hamburguesas_2025.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    print(f"\n✅ Guardado en /tmp/hamburguesas_2025.json")
