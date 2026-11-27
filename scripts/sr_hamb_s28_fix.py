#!/usr/bin/env python3
"""S28 Montejano hamburguesas — con Cantidad en el MÁXIMO VÁLIDO (el bug era cantidad>max)."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/nomina/sr_hamb_montejano_s28.txt")
SUC = "12764"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width":1800,"height":1400})
    page = ctx.new_page()
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000); page.wait_for_timeout(2000)
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    # leer atributos max/min del campo Cantidad
    attrs = page.evaluate("""() => {const c=document.querySelector('#NumElementosTop');
        return c?{max:c.getAttribute('max'),min:c.getAttribute('min'),val:c.value}:null;}""")
    print("NumElementosTop attrs:", attrs, flush=True)
    maxv = 100
    try:
        if attrs and attrs.get("max"): maxv=int(attrs["max"])
    except Exception: pass
    print("usando cantidad =", maxv, flush=True)

    page.locator('#FechaInicial').fill('06/07/2026')
    page.locator('#FechaFinal').fill('13/07/2026')
    page.evaluate("""(v) => {const c=document.querySelector('#NumElementosTop');
        if(c){const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
        s.call(c,String(v));c.dispatchEvent(new Event('input',{bubbles:true}));c.dispatchEvent(new Event('change',{bubbles:true}));}}""", maxv)
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
    tabs = page.eval_on_selector_all("table", "els => els.map(t=>t.innerText)")
    OUT.write_text("\n\n===TABLE===\n\n".join(tabs))
    b.close()

# sumar hamburguesas
BURGER_KW=("CLASICA","DOBLE CARNE","WESTERN","HAWAIANA","TOCINO","CALIFORNIA","DOBLE QUESO","LOW CARB","PECHUGA","COMBO")
EXCL=("PAPAS","BEBIDA","REFRESCO","AGUA","AROS","TE ","COCA","JAMAICA","ROOT","ORDEN","EXTRA","SALSA","MALTEAD","POSTRE","PROMOCION DUO")
rows=[]
for line in OUT.read_text().split("\n"):
    L=line.strip()
    m=re.match(r"^(\d{4,5})\s+(.+?)\s+([\d,]+\.\d{2})\s", L) or re.match(r"^(\d{4,5})\t(.+?)\t([\d,]+\.\d{2})", L)
    if m:
        rows.append((m.group(1),m.group(2).strip(),float(m.group(3).replace(",",""))))
print(f"\nfilas producto detectadas: {len(rows)}")
tot=0; burg=[]
for cl,name,q in rows:
    up=name.upper()
    if any(k in up for k in BURGER_KW) and not any(k in up for k in EXCL):
        burg.append((name,q)); tot+=q
for name,q in sorted(burg,key=lambda x:-x[1]): print(f"  {int(q):>5}  {name}")
print(f"\n>>> TOTAL hamburguesas S28 (Montejano): {int(tot)}")
if tot>700: print(f">>> Bono Tata S28 = ({int(tot)}-700)*5 = ${int((tot-700)*5)}")
