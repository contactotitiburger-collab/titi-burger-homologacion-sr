#!/usr/bin/env python3
"""Ventas diarias completas Villas del Rey — período 08-jun a 10-jul."""
import json, re
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
VILLAS = "26983"

def login(page):
    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1600})
    page = ctx.new_page()
    login(page)

    # Reporte 6: Ventas diarias
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/6", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    # Ampliar rango — probar el mes de junio y julio parcial
    page.evaluate("""() => {
        const inputs = document.querySelectorAll('select');
        for (const s of inputs) {
            const vals = [...s.options].map(o => o.value);
            if (vals.includes('6') && vals.includes('7')) s.value = '6';
            if (vals.includes('2026')) s.value = '2026';
        }
    }""")
    # Sucursal Villas
    page.evaluate(f"""() => {{
        for (const sel of document.querySelectorAll('select')) {{
            const vals = [...sel.options].map(o => o.value);
            if (vals.includes('12764')) {{
                for (const opt of sel.options) opt.selected = (opt.value === '{VILLAS}');
                sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
                break;
            }}
        }}
    }}""")
    page.wait_for_timeout(1500)
    page.locator('text="Consultar"').first.click()
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(15000)

    text = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/villas_diario_junio.txt").write_text(text)
    print("=== JUNIO 2026 — VILLAS DEL REY días ===")
    for line in text.split("\n"):
        l = line.strip()
        m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}).*?\$?([\d,]+\.\d{2})", l)
        if m and "$" in l:
            print(f"  {l[:150]}")

    # Julio
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/6", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2500)
    page.evaluate("""() => {
        const inputs = document.querySelectorAll('select');
        for (const s of inputs) {
            const vals = [...s.options].map(o => o.value);
            if (vals.includes('6') && vals.includes('7')) s.value = '7';
            if (vals.includes('2026')) s.value = '2026';
        }
    }""")
    page.evaluate(f"""() => {{
        for (const sel of document.querySelectorAll('select')) {{
            const vals = [...sel.options].map(o => o.value);
            if (vals.includes('12764')) {{
                for (const opt of sel.options) opt.selected = (opt.value === '{VILLAS}');
                sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                if (window.jQuery) window.jQuery(sel).trigger('change');
                break;
            }}
        }}
    }}""")
    page.wait_for_timeout(1500)
    page.locator('text="Consultar"').first.click()
    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(15000)
    text_jul = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/villas_diario_julio.txt").write_text(text_jul)
    print("\n=== JULIO 2026 — VILLAS DEL REY días ===")
    for line in text_jul.split("\n"):
        l = line.strip()
        m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}).*?\$?([\d,]+\.\d{2})", l)
        if m and "$" in l:
            print(f"  {l[:150]}")

    browser.close()
