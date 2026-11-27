#!/usr/bin/env python3
"""Reutilizar sesión DiDi (cookies guardadas) y explorar Finanzas."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
cookies = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/cookies.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
    )
    ctx.add_cookies(cookies)
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    # Ir al dashboard
    page.goto("https://www.didi-food.com/es-MX/manager/overview", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(5000)

    # Cerrar modal de bienvenida si aparece
    try:
        skip_btn = page.locator("text=Saltar guía").or_(page.locator("button:has-text('Cerrar')")).first
        if skip_btn.count():
            skip_btn.click()
            page.wait_for_timeout(2000)
    except: pass

    page.screenshot(path=str(SCREEN / "didi_dashboard_clean.png"), full_page=True)

    # Encontrar menú de finanzas
    menu_items = page.eval_on_selector_all(
        "a, li, span, div",
        """els => els.filter(e => {
            const t = (e.textContent||'').trim();
            return t.length > 2 && t.length < 40 &&
                   /finanzas|pagos|ingresos|comisión|estado.*cuenta/i.test(t) &&
                   e.children.length < 5;
        }).map(e => ({tag: e.tagName, text: e.textContent.trim().slice(0,50)})).slice(0,20)"""
    )
    print("=== Enlaces de Finanzas / Ingresos ===")
    for m in menu_items:
        print(f"  {m}", flush=True)

    # Click en "Finanzas" del sidebar
    try:
        finanzas = page.locator("text=Finanzas").first
        finanzas.click(timeout=5000)
        page.wait_for_timeout(4000)
        page.screenshot(path=str(SCREEN / "didi_finanzas.png"), full_page=True)
        print(f"Click Finanzas → {page.url}", flush=True)
        (SCREEN / "didi_finanzas.html").write_text(page.content())
    except Exception as e:
        print(f"Sin Finanzas: {e}", flush=True)

    # Explorar todo el sidebar
    sidebar = page.eval_on_selector_all(
        ".menu-item, li[role='menuitem'], nav a, aside a, [class*='sidebar'] a, [class*='menu'] a",
        """els => [...new Set(els.map(e => e.textContent.trim().slice(0,40)).filter(t => t))]"""
    )
    print("\n=== SIDEBAR ===")
    for s in sidebar[:30]:
        print(f"  {s}", flush=True)

    browser.close()
