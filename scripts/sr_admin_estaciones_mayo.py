#!/usr/bin/env python3
"""Ventas por estación (canal/app) — mayo 2026, todas las sucursales."""
import json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")
OUT = Path("/home/tito/.openclaw/data/ventas_estaciones_mayo_2026.json")

IDS = ["12764","13056","22871","22980","23032","26983"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1800, "height": 1400})
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.locator('input[type="email"]').first.fill(CREDS["user"])
    page.locator('input[type="password"]').first.fill(CREDS["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(2000)

    # Reporte 13 = Ventas por estación
    page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/13", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)
    (SCREEN_DIR / "22_estaciones_filtros.html").write_text(page.content())
    page.screenshot(path=str(SCREEN_DIR / "22_estaciones_filtros.png"), full_page=True)

    # Filtros — puede haber mes/año o rango de fechas
    # Los reportes de tipo "por estación" quizá usan un rango de fecha (from-to)
    # Vamos a inspeccionar qué campos hay
    fields = page.eval_on_selector_all(
        "input, select",
        "els => els.map(e => ({tag: e.tagName, type: e.type||'', name: e.name||'', id: e.id||'', val: e.value||''}))"
    )
    print("Campos del reporte 13:", flush=True)
    for f in fields[:30]:
        print(f"  {f}", flush=True)

    # Fijar rango de fechas si hay inputs date
    # Fechas mayo 2026: 2026-05-01 → 2026-05-31
    for f in fields:
        if f["type"] == "date":
            print(f"Campo date: {f['id']} / {f['name']}", flush=True)

    browser.close()
