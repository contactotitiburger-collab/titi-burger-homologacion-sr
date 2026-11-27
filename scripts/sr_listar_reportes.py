#!/usr/bin/env python3
"""Lista los reportes disponibles en SR Admin (nombre + link) para ubicar Formas de Pago."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1600, "height": 1200}).new_page()
    pg.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    pg.evaluate("AbrirModal()"); pg.wait_for_timeout(1500)
    pg.locator('input[type="email"]').first.fill(CREDS["user"])
    pg.locator('input[type="password"]').first.fill(CREDS["password"])
    pg.locator('button[type="submit"]').first.click()
    pg.wait_for_load_state("networkidle", timeout=45000); pg.wait_for_timeout(2500)

    pg.goto("https://admin.softrestaurant.com/Analytics/ReportesVentas",
            wait_until="networkidle", timeout=45000)
    pg.wait_for_timeout(3000)
    items = pg.evaluate("""() => {
        const out = [];
        for (const a of document.querySelectorAll('a')) {
            const href = a.getAttribute('href') || '';
            const txt = (a.innerText || '').trim();
            if (href.includes('Consultar/') && txt) out.push(txt + '  ->  ' + href);
        }
        return out;
    }""")
    print("=== REPORTES DISPONIBLES ===", flush=True)
    for it in items:
        print(it, flush=True)
    b.close()
