#!/usr/bin/env python3
"""Escanea el portal SR nube buscando CUALQUIER enlace/reporte de formas de pago."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
URLS = [
    "https://admin.softrestaurant.com/",
    "https://admin.softrestaurant.com/Analytics/ReportesVentas",
    "https://admin.softrestaurant.com/analytics/Settings/Dashboard",
]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width":1600,"height":1200}).new_page()
    pg.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    pg.evaluate("AbrirModal()"); pg.wait_for_timeout(1500)
    pg.locator('input[type="email"]').first.fill(CREDS["user"])
    pg.locator('input[type="password"]').first.fill(CREDS["password"])
    pg.locator('button[type="submit"]').first.click()
    pg.wait_for_load_state("networkidle", timeout=45000); pg.wait_for_timeout(2500)

    vistos = set()
    for u in URLS:
        try:
            pg.goto(u, wait_until="networkidle", timeout=45000); pg.wait_for_timeout(2500)
        except Exception as e:
            print(f"  (no cargó {u}: {e})"); continue
        links = pg.evaluate("""() => {
            const out=[];
            for (const a of document.querySelectorAll('a,button,[role=menuitem]')) {
                const t=(a.innerText||'').trim(); const h=a.getAttribute('href')||'';
                if(t) out.push(t+' || '+h);
            }
            return out;
        }""")
        for l in links:
            low = l.lower()
            if any(k in low for k in ["pago","forma","efectivo","tarjeta","payment"]):
                if l not in vistos:
                    vistos.add(l); print("   HIT:", l)
    if not vistos:
        print("   NINGÚN enlace de formas de pago en el portal nube.")
    b.close()
