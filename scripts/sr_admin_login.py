#!/usr/bin/env python3
"""Login a SR Admin y captura dashboard post-login."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
SCREEN_DIR = Path("/home/tito/.openclaw/sr_admin_screens")
SCREEN_DIR.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
    print(f"Landing OK: {page.title()}", flush=True)

    # Abrir modal de login (js: AbrirModal())
    page.evaluate("AbrirModal()")
    page.wait_for_timeout(1500)
    page.screenshot(path=str(SCREEN_DIR / "02_login_modal.png"), full_page=True)

    # Buscar el input de correo y password (varios selectores)
    # Del HTML inicial vimos "hidencorreo" y modal se abre por JS. Vamos a ver el HTML actual.
    (SCREEN_DIR / "02_login_modal.html").write_text(page.content())

    # Intentar llenar el form del modal. Probar varios selectores comunes.
    filled = False
    for user_sel, pass_sel in [
        ('input[type="email"]', 'input[type="password"]'),
        ('#correo', '#password'),
        ('#txtCorreo', '#txtPassword'),
        ('#Correo', '#Password'),
        ('input[name="correo"]', 'input[name="password"]'),
        ('input[name="Correo"]', 'input[name="Password"]'),
    ]:
        try:
            if page.locator(user_sel).count() and page.locator(pass_sel).count():
                page.locator(user_sel).first.fill(CREDS["user"])
                page.locator(pass_sel).first.fill(CREDS["password"])
                print(f"Rellené usando {user_sel} / {pass_sel}", flush=True)
                filled = True
                break
        except Exception as e:
            print(f"Fallo {user_sel}: {e}", flush=True)

    if not filled:
        print("No pude encontrar selectores. Guardando HTML para inspección.", flush=True)
        browser.close()
        raise SystemExit(1)

    # Buscar botón de submit
    for btn_sel in [
        'button:has-text("Iniciar")',
        'button:has-text("Ingresar")',
        'button[type="submit"]',
        'input[type="submit"]',
        'a:has-text("Iniciar")',
    ]:
        try:
            if page.locator(btn_sel).count():
                page.locator(btn_sel).first.click()
                print(f"Click submit: {btn_sel}", flush=True)
                break
        except Exception as e:
            pass

    # Esperar navegación post-login
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    print(f"URL post-login: {page.url}", flush=True)
    print(f"Title post-login: {page.title()}", flush=True)
    page.screenshot(path=str(SCREEN_DIR / "03_dashboard.png"), full_page=True)
    (SCREEN_DIR / "03_dashboard.html").write_text(page.content())
    print(f"Dashboard capturado", flush=True)

    browser.close()
print("OK", flush=True)
