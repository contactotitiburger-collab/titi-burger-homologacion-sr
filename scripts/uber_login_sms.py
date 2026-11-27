#!/usr/bin/env python3
"""Login Uber Merchants con espera de código SMS."""
import json, os, time
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/uber_merchants/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_uber")
CODE_FILE = Path("/tmp/uber_sms_code.txt")
CODE_FILE.unlink(missing_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
        storage_state=str(Path("/home/tito/.openclaw/credentials/uber_merchants/state.json")) if Path("/home/tito/.openclaw/credentials/uber_merchants/state.json").exists() else None,
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    page.goto("https://merchants.ubereats.com/manager", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(4000)

    # Si ya estamos dentro (sesión guardada), salir
    if "manager" in page.url and "auth.uber.com" not in page.url:
        print(f"YA LOGUEADO: {page.url}", flush=True)
        page.screenshot(path=str(SCREEN / "already_in.png"), full_page=True)
        ctx.storage_state(path="/home/tito/.openclaw/credentials/uber_merchants/state.json")
        browser.close()
        exit(0)

    # Rellenar email
    print(f"Meto email: {creds['user']}", flush=True)
    e = page.locator('input#PHONE_NUMBER_or_EMAIL_ADDRESS').first
    e.click(); e.type(creds["user"], delay=100)
    page.wait_for_timeout(2000)
    page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=15000)
    page.locator("#forward-button").click()
    page.wait_for_timeout(5000)
    page.screenshot(path=str(SCREEN / "sms_wait.png"), full_page=True)
    print(f"Estoy en: {page.url}", flush=True)

    # Ver si pide password primero o directo SMS
    if page.locator('input[type="password"]').count() > 0:
        print("Pide PASSWORD antes", flush=True)
        pwd = page.locator('input[type="password"]').first
        pwd.type(creds["password"], delay=100)
        page.wait_for_timeout(1500)
        page.locator("#forward-button, button[type='submit']").first.click()
        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREEN / "after_pwd.png"), full_page=True)

    # Ahora la pantalla de SMS — 4 inputs
    print("Esperando código SMS. Pásame el código escribiéndolo en /tmp/uber_sms_code.txt", flush=True)
    print(f"URL actual: {page.url}", flush=True)

    # Esperar hasta que el archivo con el código aparezca (máximo 4 min)
    code = None
    for i in range(240):  # 240 seg = 4 min
        if CODE_FILE.exists():
            code = CODE_FILE.read_text().strip()
            if len(code) >= 4:
                print(f"Código recibido: {code[:4]}", flush=True)
                break
        time.sleep(1)

    if not code or len(code) < 4:
        print("TIMEOUT — no llegó código", flush=True)
        browser.close()
        exit(1)

    # Meter los 4 dígitos
    code = code[:4]
    inputs = page.query_selector_all('input[type="tel"], input[type="text"], input[maxlength="1"], input[inputmode="numeric"]')
    print(f"Inputs código encontrados: {len(inputs)}", flush=True)
    if len(inputs) >= 4:
        for i, digit in enumerate(code):
            inputs[i].click()
            inputs[i].type(digit, delay=100)
            page.wait_for_timeout(300)
    else:
        # 1 solo input probablemente
        page.keyboard.type(code, delay=100)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(SCREEN / "after_sms.png"), full_page=True)

    # Click Siguiente
    try:
        page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=10000)
        page.locator("#forward-button").click()
        print("Click Siguiente tras SMS", flush=True)
    except Exception as ex:
        print(f"btn err: {ex}", flush=True)

    page.wait_for_timeout(6000)
    page.screenshot(path=str(SCREEN / "after_sms_click.png"), full_page=True)
    print(f"URL post SMS: {page.url}", flush=True)

    # PASSWORD (viene ahora)
    if page.locator('input[type="password"]').count() > 0:
        print("Pide password", flush=True)
        pwd = page.locator('input[type="password"]').first
        pwd.click()
        pwd.type(creds["password"], delay=100)
        page.wait_for_timeout(2500)
        try:
            page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=10000)
            page.locator("#forward-button").click()
            print("Password metida + Siguiente", flush=True)
        except: pass
        page.wait_for_timeout(10000)

    page.wait_for_load_state("networkidle", timeout=60000)
    page.wait_for_timeout(6000)
    print(f"URL final: {page.url}", flush=True)
    print(f"Title: {page.title()}", flush=True)
    page.screenshot(path=str(SCREEN / "after_login.png"), full_page=True)
    (SCREEN / "after_login.html").write_text(page.content())

    ctx.storage_state(path="/home/tito/.openclaw/credentials/uber_merchants/state.json")
    print("Sesión guardada", flush=True)

    browser.close()
