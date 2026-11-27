#!/usr/bin/env python3
"""Vuelca la tabla COMPLETA de PRODUCTOS MÁS VENDIDOS (reporte 7) para un rango.
Modelado sobre el flujo que ya funcionó (sr_admin_productos_apps.py)."""
import json, sys, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
DL = Path("/home/tito/.openclaw/data/productos_export")
DL.mkdir(parents=True, exist_ok=True)

INI = sys.argv[1] if len(sys.argv) > 1 else "01/08/2026"
FIN = sys.argv[2] if len(sys.argv) > 2 else "31/08/2026"
TAG = sys.argv[3] if len(sys.argv) > 3 else "ago2026"
IDS = ["12764", "13056", "22871", "22980", "23032", "26983"]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_context(viewport={"width": 1800, "height": 1400}).new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2500)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    # fechas con eventos input+change+blur (igual que el reporte diario que SÍ funciona)
    for campo, val in (("#FechaInicial", INI), ("#FechaFinal", FIN)):
        page.evaluate("""([sel,v])=>{const el=document.querySelector(sel);
            if(!el) return; el.value=v;
            el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true}));
            el.blur&&el.blur();}""", [campo, val])
    page.evaluate("""()=>{const cant=document.querySelector('input[type=number]');
        if(cant){cant.value='1';
            cant.dispatchEvent(new Event('input',{bubbles:true}));
            cant.dispatchEvent(new Event('change',{bubbles:true}));}}""")
    page.evaluate("""(ids)=>{const sel=document.querySelector('#ListaEmpresas');
        if(!sel) return;
        for(const o of sel.options) o.selected=ids.includes(o.value);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery) window.jQuery(sel).trigger('change');}""", IDS)
    page.wait_for_timeout(1000)
    try: page.locator('#ActualizarReporte').first.click()
    except Exception:
        try: page.locator('text="Consultar"').first.click()
        except Exception: pass
    # esperar como el script que funcionaba
    try: page.wait_for_load_state("networkidle", timeout=120000)
    except Exception: pass
    page.wait_for_timeout(35000)

    # intentar mostrar 100 por pagina
    try:
        page.select_option("select[name$='_length'], select.form-control", "100")
        page.wait_for_timeout(3000)
    except Exception: pass

    # extraer todas las filas de la tabla principal (DataTables suele tener todo en el DOM)
    filas = page.evaluate("""() => {
        const out = [];
        for (const t of document.querySelectorAll('table')) {
            for (const tr of t.querySelectorAll('tr')) {
                const cells = [...tr.querySelectorAll('td,th')].map(c => c.innerText.trim());
                if (cells.length) out.push(cells);
            }
        }
        return out;
    }""")
    (DL / f"productos_{TAG}_filas.json").write_text(json.dumps(filas, ensure_ascii=False))
    print(f"filas extraidas: {len(filas)}", flush=True)

    # sumar app vs total directamente aqui
    APP = re.compile(r"\b(UBER|DIDI|RAPPI)\b", re.I)
    def num(s):
        s = re.sub(r"[^\d.\-]", "", s or "")
        try: return float(s)
        except: return 0.0
    tot_app = 0.0; tot_all = 0.0; n_app = 0
    ejemplos = []
    for row in filas:
        # buscar fila con descripcion + un TOTAL $ al final
        joined = " ".join(row)
        if "$" not in joined: continue
        # la ultima celda con $ suele ser TOTAL
        money = [num(c) for c in row if "$" in c]
        if not money: continue
        total = money[-1]
        desc = " ".join(c for c in row if "$" not in c)
        if not desc: continue
        tot_all += total
        if APP.search(desc):
            tot_app += total; n_app += 1
            if len(ejemplos) < 8: ejemplos.append((desc[:40], total))
    print(f"\nSUMA productos APP (UBER/DIDI/RAPPI): ${tot_app:,.2f}  ({n_app} productos)", flush=True)
    print(f"SUMA productos TOTAL (todas las filas): ${tot_all:,.2f}", flush=True)
    if tot_all>0:
        print(f"% APP ≈ {100*tot_app/tot_all:.1f}%   |   % FÍSICA ≈ {100*(1-tot_app/tot_all):.1f}%", flush=True)
    print("ejemplos app:", ejemplos, flush=True)
    b.close()
