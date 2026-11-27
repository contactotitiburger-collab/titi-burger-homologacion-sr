#!/usr/bin/env python3
"""Uber: Olvidé mi contraseña — pedir reset link."""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/uber_merchants/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_uber")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    page.goto("https://merchants.ubereats.com/manager", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    # Email
    e = page.locator('input#PHONE_NUMBER_or_EMAIL_ADDRESS').first
    e.click(); e.type(creds["user"], delay=100)
    page.wait_for_timeout(2000)
    page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=15000)
    page.locator("#forward-button").click()
    page.wait_for_timeout(6000)

    # Estamos en SMS → Más opciones → Correo electrónico → Inicia sesión con contraseña
    try: page.locator("text=Más opciones").first.click(timeout=8000)
    except: pass
    page.wait_for_timeout(3000)
    try: page.locator("text=Correo electrónico").first.click(timeout=5000)
    except: pass
    page.wait_for_timeout(5000)
    try: page.locator("text=Inicia sesión con tu contraseña").first.click(timeout=8000)
    except: pass
    page.wait_for_timeout(5000)
    print(f"URL en password: {page.url}", flush=True)

    # Click "Olvidé mi contraseña"
    try:
        page.locator("text=Olvidé mi contraseña").first.click(timeout=8000)
        print("Click 'Olvidé mi contraseña'", flush=True)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREEN / "reset_page.png"), full_page=True)
        (SCREEN / "reset_page.html").write_text(page.content())
        print(f"URL: {page.url}", flush=True)
    except Exception as ex:
        print(f"Sin 'Olvidé mi contraseña': {ex}", flush=True)

    # Esperar código en Yahoo
    import imaplib, email, re
    from bs4 import BeautifulSoup
    yahoo = json.loads(Path("/home/tito/.openclaw/credentials/yahoo/creds.json").read_text())

    def buscar_codigo(desde_ts):
        import email.utils
        M = imaplib.IMAP4_SSL(yahoo["imap_host"], yahoo["imap_port"])
        M.login(yahoo["user"], yahoo["password"])
        M.select("Inbox", readonly=True)
        typ, ids = M.search(None, 'FROM "admin@uber.com"')
        for mid in sorted(ids[0].split(), key=lambda x: int(x), reverse=True):
            typ, data = M.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            try:
                msg_ts = email.utils.parsedate_to_datetime(msg.get("Date","")).timestamp()
            except: continue
            if msg_ts < desde_ts: continue
            body = ""
            for pt in msg.walk():
                if pt.get_content_type() == "text/plain":
                    body += pt.get_payload(decode=True).decode(errors="replace")
                elif pt.get_content_type() == "text/html":
                    body += BeautifulSoup(pt.get_payload(decode=True), "html.parser").get_text(separator=" ")
            m = re.search(r"\b(\d{4})\b", body)
            if m:
                M.logout()
                return m.group(1)
        M.logout()
        return None

    ts_inicio = time.time() - 30
    print(f"Esperando código en Yahoo...", flush=True)
    codigo = None
    for i in range(15):
        time.sleep(10)
        c = buscar_codigo(ts_inicio)
        if c:
            codigo = c
            print(f"Código: {codigo}", flush=True)
            break

    if not codigo:
        print("No llegó código", flush=True)
        browser.close()
        exit(1)

    # Meter código con press() en cada input (dispara eventos keyboard reales)
    for i, digit in enumerate(codigo):
        input_id = f"EMAIL_OTP_CODE-{i}"
        try:
            page.locator(f"#{input_id}").press(digit)
            page.wait_for_timeout(300)
        except Exception as e:
            print(f"  press {i}: {e}", flush=True)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(SCREEN / "code_filled.png"), full_page=True)

    # Click Siguiente
    try:
        page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=15000)
        page.locator("#forward-button").click()
        print("Click Siguiente tras código", flush=True)
    except Exception as ex:
        print(f"Forward err: {ex}", flush=True)

    page.wait_for_timeout(10000)
    page.screenshot(path=str(SCREEN / "after_code_reset.png"), full_page=True)
    (SCREEN / "after_code_reset.html").write_text(page.content())
    print(f"URL: {page.url}", flush=True)

    # Ahora debería pedir NUEVA contraseña
    text = page.evaluate("() => document.body.innerText")
    print(f"\n=== Texto ===\n{text[:800]}")

    browser.close()
