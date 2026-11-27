#!/usr/bin/env python3
"""Verifica hamburguesas vendidas en Montejano (FOVISSTE 12764) — S29 (13-20 jul 2026).
Reporte 7 (productos vendidos). Vuelca todo y suma líneas tipo hamburguesa/combo."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/nomina/sr_hamburguesas_montejano_s29.txt")
SUC = "12764"  # FOVISSTE / Montejano = Área A

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
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('#FechaInicial').fill('13/07/2026')
    page.locator('#FechaFinal').fill('20/07/2026')
    # Cantidad: setear a 500 de forma robusta (click, seleccionar todo, teclear)
    try:
        ci = page.locator('#NumElementosTop')
        ci.click()
        page.keyboard.press("Control+A")
        page.keyboard.type("500")
        page.keyboard.press("Tab")
    except Exception as e:
        print("cantidad click/type fallo:", e)
    val = page.evaluate("() => {const c=document.querySelector('#NumElementosTop'); return c? c.value : 'NO-INPUT';}")
    print("Cantidad tras teclear:", val, flush=True)
    # Empresa: seleccionar en el <select> y disparar todos los eventos posibles (select2/jQuery)
    page.evaluate("""(id)=>{const sel=document.querySelector('#ListaEmpresas');
        if(sel){for(const o of sel.options)o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery){window.jQuery(sel).val([id]).trigger('change');}}}""", SUC)
    page.wait_for_timeout(1500)
    # Click Consultar de forma robusta
    btn = page.locator('#ActualizarReporte, input[value="Consultar"], button:has-text("Consultar"), a:has-text("Consultar")').first
    btn.scroll_into_view_if_needed()
    btn.click(force=True)
    # Esperar a que aparezca la tabla de resultados (fila con datos) hasta 150s
    got=False
    try:
        page.wait_for_selector("table tbody tr td", timeout=150000)
        got=True
    except Exception:
        pass
    page.wait_for_timeout(8000)
    if got:
        try:
            page.select_option('select[name*="length"]', "-1"); page.wait_for_timeout(4000)
        except Exception:
            try: page.select_option('select[name*="length"]', "100"); page.wait_for_timeout(4000)
            except Exception: pass
    page.screenshot(path="/home/tito/.openclaw/data/nomina/sr_montejano_s29.png", full_page=True)
    tables = page.eval_on_selector_all("table", "els => els.map(t => t.innerText)")
    body = page.evaluate("() => document.body.innerText")
    OUT.write_text(("GOT_TABLE=%s\n\n"%got) + "\n\n===TABLE===\n\n".join(tables) + "\n\n===BODY===\n\n" + body)
    browser.close()

# Parseo: filas "NOMBRE   cantidad   $importe ..."
rows=[]
for line in text.split("\n"):
    L=line.strip()
    m=re.match(r"^(0?1?\d{3,5}\s+)?([A-ZÁÉÍÓÚÑ#0-9][A-ZÁÉÍÓÚÑ#0-9\s\-\.\/\(\)\+]+?)\s+([\d,]+(?:\.\d+)?)\s+\$", L)
    if m:
        rows.append((m.group(2).strip(), float(m.group(3).replace(",",""))))

BURGER_KW=("CLASICA","DOBLE CARNE","WESTERN","HAWAIANA","TOCINO","CALIFORNIA",
           "DOBLE QUESO","LOW CARB","PECHUGA","COMBO","CARNE","QUESO")
EXCLUDE_KW=("PAPAS","BEBIDA","REFRESCO","AGUA","ORDEN","EXTRA","ADICIONAL","SALSA")
burgers=[]; total=0
for name,q in rows:
    up=name.upper()
    if any(k in up for k in BURGER_KW) and not any(k in up for k in EXCLUDE_KW):
        burgers.append((name,q)); total+=q

print(f"Filas producto detectadas: {len(rows)}")
print(f"Líneas tipo hamburguesa/combo: {len(burgers)}")
print("--- detalle ---")
for name,q in sorted(burgers,key=lambda x:-x[1]):
    print(f"  {int(q):>5}  {name}")
print(f"\nTOTAL hamburguesas (heurística): {int(total)}")
json.dump({"total":total,"burgers":burgers,"n_rows":len(rows)},
          open("/home/tito/.openclaw/data/nomina/sr_hamburguesas_montejano_s29.json","w"),
          ensure_ascii=False, indent=1)
