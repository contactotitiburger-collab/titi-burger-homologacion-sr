#!/usr/bin/env python3
"""Dashboard mayo 2026 — forzar rango con click en Actualizar y esperar bien."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")

IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 2400})
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(3000)

    page.goto("https://admin.softrestaurant.com/Dashboard", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)

    # Setear inputs de fecha directo, disparando eventos correctos
    page.evaluate("""() => {
        try {
            const f1 = document.querySelector('#FechaInicial') || document.querySelector('input[name="FechaInicial"]');
            const f2 = document.querySelector('#FechaFinal') || document.querySelector('input[name="FechaFinal"]');
            if (f1) { f1.value = '01/05/2026'; f1.dispatchEvent(new Event('change')); f1.dispatchEvent(new Event('blur')); }
            if (f2) { f2.value = '31/05/2026'; f2.dispatchEvent(new Event('change')); f2.dispatchEvent(new Event('blur')); }
        } catch(e){}
    }""")
    page.wait_for_timeout(1000)

    # Click botón Actualizar (el verde)
    for sel in ['#Actualizar', 'button:has-text("Actualizar")', 'text="Actualizar"']:
        try:
            btn = page.locator(sel).first
            if btn.count():
                btn.click()
                print(f"Click en {sel}", flush=True)
                break
        except Exception as e:
            print(f"  {sel}: {e}", flush=True)

    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(10000)
    page.screenshot(path=str(SCREEN_DIR / "25_dashboard_mayo_v2.png"), full_page=True)
    (SCREEN_DIR / "25_dashboard_mayo_v2.html").write_text(page.content())

    # Extraer todo el texto y buscar las secciones importantes
    text_all = page.evaluate("() => document.body.innerText")
    print("--- BUSCANDO Ventas por servicio / formas de pago ---", flush=True)
    lines = text_all.split("\n")
    for i, line in enumerate(lines):
        if any(k in line for k in ["Ventas por", "UBER", "RAPPI", "DIDI", "DOMICILIO", "RAPIDO", "COMEDOR"]):
            # imprimir contexto de las siguientes 6 líneas
            context = " | ".join(lines[i:i+8])
            print(f"  {context[:250]}", flush=True)

    browser.close()
