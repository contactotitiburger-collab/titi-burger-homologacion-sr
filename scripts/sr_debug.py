#!/usr/bin/env python3
"""Debug: ver qué botones hay después del reporte."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400}, accept_downloads=True)
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()"); page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/7",
              wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('#FechaInicial').fill('01/07/2025')
    page.locator('#FechaFinal').fill('31/07/2025')
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    page.evaluate("""() => {
        const c = document.querySelector('#NumElementosTop');
        if (c) {
            const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            s.call(c, '500');
            c.dispatchEvent(new Event('input', {bubbles: true}));
            c.dispatchEvent(new Event('change', {bubbles: true}));
        }
    }""")
    page.evaluate("""(id) => {
        const sel = document.querySelector('#ListaEmpresas');
        if (sel) {
            for (const opt of sel.options) opt.selected = (opt.value === id);
            sel.dispatchEvent(new Event('change', {bubbles: true}));
            if (window.jQuery) window.jQuery(sel).trigger('change');
        }
    }""", "22871")
    page.wait_for_timeout(1000)
    page.locator('#ActualizarReporte').first.click()
    page.wait_for_load_state("networkidle", timeout=120000)
    page.wait_for_timeout(30000)

    # Screenshot y HTML dump
    page.screenshot(path="/tmp/sr_debug.png", full_page=True)
    Path("/tmp/sr_debug.html").write_text(page.content())
    # Ver todos los botones y links con "EXCEL", "excel", "descargar"
    text = page.evaluate("() => document.body.innerText")
    Path("/tmp/sr_debug.txt").write_text(text)

    # Buscar botones/enlaces
    btns = page.evaluate("""() => {
        const results = [];
        for (const el of document.querySelectorAll('button, a')) {
            const txt = el.innerText.trim();
            if (txt && txt.length < 40) {
                results.push({tag: el.tagName, text: txt, id: el.id, cls: el.className});
            }
        }
        return results.slice(0, 40);
    }""")
    print("BOTONES/LINKS visibles:")
    for b in btns:
        print(f"  {b['tag']} id={b['id']!r} text={b['text']!r}")
    browser.close()
