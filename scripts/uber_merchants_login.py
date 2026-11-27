#!/usr/bin/env python3
"""Login Uber Merchants + explorar."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/uber_merchants/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_uber")
SCREEN.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    page.goto("https://merchants.ubereats.com/manager", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)
    page.screenshot(path=str(SCREEN / "01_landing.png"), full_page=True)
    print(f"URL landing: {page.url}", flush=True)
    print(f"Title: {page.title()}", flush=True)

    # Inspeccionar inputs
    inputs = page.eval_on_selector_all(
        "input",
        "els => els.map(e => ({type: e.type||'', name: e.name||'', id: e.id||'', placeholder: e.placeholder||''}))"
    )
    print("=== Inputs ===")
    for i in inputs[:10]:
        print(f"  {i}", flush=True)

    # Rellenar correo con delay lento y forzar eventos
    email_input = page.locator('input#PHONE_NUMBER_or_EMAIL_ADDRESS, input[name="email"]').first
    email_input.click()
    email_input.type(creds["user"], delay=100)
    page.wait_for_timeout(2500)
    print(f"Email rellenado: {creds['user']}", flush=True)

    # Esperar que el botón se habilite y darle click
    page.wait_for_function("() => { const b = document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=15000)
    page.locator("#forward-button").click()
    page.wait_for_timeout(6000)
    page.screenshot(path=str(SCREEN / "02_after_email.png"), full_page=True)
    print(f"URL post email: {page.url}", flush=True)

    # Rellenar password
    try:
        pwd = page.locator('input[type="password"]').first
        pwd.type(creds["password"], delay=60)
        print("Password rellenada", flush=True)
        page.wait_for_timeout(1500)
    except Exception as e:
        print(f"Sin password: {e}", flush=True)

    # Click Sign In
    try:
        page.locator("button:has-text('Sign in'), button:has-text('Continu'), button[type='submit']").first.click()
        page.wait_for_load_state("networkidle", timeout=45000)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREEN / "03_after_pwd.png"), full_page=True)
        print(f"URL post pwd: {page.url}", flush=True)
        print(f"Title: {page.title()}", flush=True)
    except Exception as e:
        print(f"Sin btn sign in: {e}", flush=True)

    # Guardar cookies
    Path("/home/tito/.openclaw/credentials/uber_merchants/cookies.json").write_text(json.dumps(ctx.cookies()))
    (SCREEN / "03_after_pwd.html").write_text(page.content())

    browser.close()
