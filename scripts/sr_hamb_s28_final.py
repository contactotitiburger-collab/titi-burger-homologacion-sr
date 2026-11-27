#!/usr/bin/env python3
"""S28 Montejano hamburguesas — sube la Cantidad con el botón '+' (widget touchspin, paso 5)."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/nomina/sr_hamb_montejano_s28.txt")
SUC = "12764"; TARGET = 200

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_context(viewport={"width":1800,"height":1400}).new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2000)
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    page.locator('#FechaInicial').fill('06/07/2026')
    page.locator('#FechaFinal').fill('13/07/2026')
    # subir Cantidad con el botón '+' (btn-increment), paso 5, hasta TARGET
    inc = page.locator('button.btn-increment, .input-group-append button, button:has-text("+")').first
    clicks=0
    while clicks < 60:
        val = page.evaluate("() => { const c=document.querySelector('#NumElementosTop'); return c?parseInt(c.value||'0'):0; }")
        if val >= TARGET: break
        try: inc.click()
        except Exception as e:
            print("click + falló:", str(e)[:80]); break
        clicks += 1
        page.wait_for_timeout(60)
    val = page.evaluate("() => { const c=document.querySelector('#NumElementosTop'); return c?c.value:'?'; }")
    print(f"Cantidad final: {val} (tras {clicks} clicks al '+')", flush=True)

    page.evaluate("""(id)=>{const sel=document.querySelector('#ListaEmpresas');
        if(sel){for(const o of sel.options)o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));if(window.jQuery)window.jQuery(sel).val([id]).trigger('change');}}""", SUC)
    page.wait_for_timeout(1500)
    page.locator('#ActualizarReporte').first.click(force=True)
    got=False
    try:
        page.wait_for_selector("table tbody tr td", timeout=150000); got=True
    except Exception: pass
    page.wait_for_timeout(8000)
    print("resultados renderizaron:", got, flush=True)
    # MOSTRAR TODAS LAS FILAS (quitar paginación del DataTable)
    page.evaluate("""() => {
      try {
        if (window.jQuery && jQuery.fn.dataTable) {
          jQuery('table').each(function(){ try{ jQuery(this).DataTable().page.len(-1).draw(false); }catch(e){} });
        }
      } catch(e){}
      document.querySelectorAll('select').forEach(s=>{
        const opts=Array.from(s.options).map(o=>o.value);
        if(opts.includes('-1')||opts.includes('100')||/length/i.test(s.name||'')){
          s.value = opts.includes('-1') ? '-1' : opts.filter(v=>!isNaN(parseInt(v))).sort((a,b)=>parseInt(b)-parseInt(a))[0];
          s.dispatchEvent(new Event('change',{bubbles:true}));
          if(window.jQuery) jQuery(s).trigger('change');
        }
      });
    }""")
    page.wait_for_timeout(6000)
    nfilas = page.evaluate("() => document.querySelectorAll('table tbody tr').length")
    print("filas en tabla tras 'mostrar todas':", nfilas, flush=True)
    tabs = page.eval_on_selector_all("table", "els => els.map(t=>t.innerText)")
    OUT.write_text("\n\n===TABLE===\n\n".join(tabs))
    b.close()

BURGER_KW=("CLASICA","DOBLE CARNE","WESTERN","HAWAIANA","TOCINO","CALIFORNIA","DOBLE QUESO","LOW CARB","PECHUGA","COMBO")
EXCL=("PAPAS","BEBIDA","REFRESCO"," AGUA","AROS","ROOT","ORDEN","EXTRA","SALSA","MALTEAD","POSTRE","PROMOCION DUO","COCA","JAMAICA")
rows=[]
for line in OUT.read_text().split("\n"):
    L=line.strip()
    m=re.match(r"^(\d{4,5})[\s\t]+(.+?)[\s\t]+([\d,]+\.\d{2})", L)
    if m: rows.append((m.group(1),m.group(2).strip(),float(m.group(3).replace(",",""))))
print(f"\nfilas producto detectadas: {len(rows)}")
tot=0; burg=[]
for cl,name,q in rows:
    up=name.upper()
    if any(k in up for k in BURGER_KW) and not any(k in up for k in EXCL):
        burg.append((name,q)); tot+=q
for name,q in sorted(burg,key=lambda x:-x[1]): print(f"  {int(q):>5}  {name}")
print(f"\n>>> TOTAL hamburguesas S28 Montejano: {int(tot)}  (de {len(burg)} líneas)")
if tot>700: print(f">>> Bono Tata S28 = ({int(tot)}-700)x5 = ${int((tot-700)*5)}")
else: print(f">>> {int(tot)} <= 700 -> sin bono producción esa semana")
