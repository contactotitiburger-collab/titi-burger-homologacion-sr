#!/usr/bin/env python3
"""
Baja ventas por hora (reporte 15) mes por mes para Villas del Rey y San Marcos,
últimos 12 meses.
"""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT_DIR = Path("/home/tito/.openclaw/data/sr_ventas_hora_12m")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUCS = {
    "22871": "SAN_MARCOS",
    "26983": "VILLAS_DEL_REY",
}

# 24 meses (jul 2024 → jun 2026)
MESES = []
for y in [2024, 2025, 2026]:
    for m in range(1, 13):
        if y == 2024 and m < 7: continue
        if y == 2026 and m > 6: continue
        last = 31 if m in (1,3,5,7,8,10,12) else 30 if m != 2 else 29 if y % 4 == 0 else 28
        MESES.append((f"{y}-{m:02d}", f"01/{m:02d}/{y}", f"{last:02d}/{m:02d}/{y}"))


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
        resultados[suc_nombre] = {}
        for mes_key, desde, hasta in MESES:
            out_txt = OUT_DIR / f"{suc_nombre}_{mes_key}.txt"
            if out_txt.exists() and out_txt.stat().st_size > 500:
                # ya lo tengo — parsear
                pass
            else:
                print(f"\n{suc_nombre} — {mes_key} ({desde} a {hasta})", flush=True)
                page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/15",
                          wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(2500)
                page.locator('#FechaInicial').fill(desde)
                page.locator('#FechaFinal').fill(hasta)
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
                page.wait_for_timeout(15000)
                try:
                    page.select_option('select[name*="length"]', "100")
                    page.wait_for_timeout(2000)
                except Exception:
                    pass
                text = page.evaluate("() => document.body.innerText")
                out_txt.write_text(text)

            # Parsear
            text = out_txt.read_text()
            horas = {}
            total = 0.0
            for line in text.split("\n"):
                m = re.match(r"(\d{2}):\d{2}:\d{2}\s*-\s*\d{2}:\d{2}:\d{2}\s+\d+\s+\d+\s+\$[\d,]+\.\d{2}\s+\$([\d,]+\.\d{2})",
                             line.strip())
                if m:
                    h = int(m.group(1))
                    v = float(m.group(2).replace(",",""))
                    horas[h] = v
                    total += v
            resultados[suc_nombre][mes_key] = {"total": total, "horas": horas}
            print(f"  → {suc_nombre} {mes_key}: ${total:,.0f}", flush=True)

    browser.close()

    Path("/tmp/ventas_12m.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    print(f"\n✅ Guardado /tmp/ventas_12m.json")
    print(f"\nResumen totales:")
    for suc, meses in resultados.items():
        print(f"\n{suc}:")
        for mk, d in sorted(meses.items()):
            print(f"  {mk}: ${d['total']:,.0f}")
