#!/usr/bin/env python3
"""Diagnóstico: por qué el reporte 7 no rendea. Captura consola, red, selección real."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SUC = "12764"
console_msgs=[]; responses=[]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width":1800,"height":1400}, accept_downloads=True)
    page = ctx.new_page()
    page.on("console", lambda m: console_msgs.append(f"{m.type}: {m.text[:200]}"))
    page.on("response", lambda r: responses.append((r.status, r.url[:130])) if ("reporte" in r.url.lower() or "consult" in r.url.lower() or "product" in r.url.lower() or "analytics" in r.url.lower()) else None)

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
    page.evaluate("""() => {const c=document.querySelector('#NumElementosTop');
        if(c){const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
        s.call(c,'2000');c.dispatchEvent(new Event('input',{bubbles:true}));c.dispatchEvent(new Event('change',{bubbles:true}));}}""")
    page.evaluate("""(id)=>{const sel=document.querySelector('#ListaEmpresas');
        if(sel){for(const o of sel.options)o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));if(window.jQuery)window.jQuery(sel).val([id]).trigger('change');}}""", SUC)
    page.wait_for_timeout(1500)

    # ¿qué quedó realmente seleccionado y qué valen los inputs?
    estado = page.evaluate("""() => {
        const sel=document.querySelector('#ListaEmpresas');
        const selected = sel ? Array.from(sel.selectedOptions).map(o=>o.value+':'+o.text) : 'NO-SEL';
        const fi=document.querySelector('#FechaInicial');
        const ff=document.querySelector('#FechaFinal');
        const cant=document.querySelector('#NumElementosTop');
        const btn=document.querySelector('#ActualizarReporte');
        return {empresas_seleccionadas: selected,
                fechaIni: fi?fi.value:'?', fechaFin: ff?ff.value:'?',
                cantidad: cant?cant.value:'?',
                btnExiste: !!btn, btnDisabled: btn?btn.disabled:'?'};
    }""")
    print("=== ESTADO ANTES DE CONSULTAR ===")
    print(json.dumps(estado, ensure_ascii=False, indent=1))

    console_msgs.clear(); responses.clear()
    page.locator('#ActualizarReporte').first.click(force=True)
    page.wait_for_timeout(45000)

    # ¿hay resultados? ¿hay mensaje de error/toast?
    post = page.evaluate("""() => {
        const filas = document.querySelectorAll('table tbody tr').length;
        const cuerpo = document.body.innerText;
        const toast = Array.from(document.querySelectorAll('.toast, .alert, .swal2-popup, [role=alert]')).map(e=>e.innerText).join(' | ');
        return {filas_tabla: filas,
                menciona_sin_datos: /no hay|sin datos|no se encontr|sin resultados/i.test(cuerpo),
                toast: toast.slice(0,300)};
    }""")
    print("\n=== DESPUÉS DE CONSULTAR (45s) ===")
    print(json.dumps(post, ensure_ascii=False, indent=1))
    print("\n=== RESPUESTAS DE RED (reporte) ===")
    for st,url in responses[:15]: print(f"  {st}  {url}")
    print("\n=== CONSOLA (errores) ===")
    for m in console_msgs[:15]:
        if m.startswith(("error","warning")): print("  "+m)
    page.screenshot(path="/home/tito/.openclaw/data/nomina/sr_diag.png", full_page=True)
    b.close()
