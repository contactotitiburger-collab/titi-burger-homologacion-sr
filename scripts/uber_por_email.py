#!/usr/bin/env python3
"""Login Uber — pedir código por email (click en Más opciones)."""
import json, time, imaplib, email, re
from email.header import decode_header
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/uber_merchants/creds.json").read_text())
yahoo = json.loads(Path("/home/tito/.openclaw/credentials/yahoo/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_uber")

def buscar_codigo_uber_email(desde_ts=None):
    """Busca en Yahoo el correo de Uber MÁS RECIENTE con código; opcionalmente después de desde_ts."""
    import email.utils
    M = imaplib.IMAP4_SSL(yahoo["imap_host"], yahoo["imap_port"])
    M.login(yahoo["user"], yahoo["password"])
    M.select("Inbox", readonly=True)
    typ, ids = M.search(None, 'FROM "admin@uber.com"', 'SUBJECT "verification"')
    result = None
    if ids[0]:
        for mid in sorted(ids[0].split(), key=lambda x: int(x), reverse=True):
            typ, data = M.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            date_str = msg.get("Date","")
            try:
                msg_ts = email.utils.parsedate_to_datetime(date_str).timestamp()
            except: continue
            if desde_ts and msg_ts < desde_ts:
                continue
            body = ""
            for p in msg.walk():
                if p.get_content_type() == "text/plain":
                    body += p.get_payload(decode=True).decode(errors="replace")
                elif p.get_content_type() == "text/html":
                    from bs4 import BeautifulSoup
                    body += BeautifulSoup(p.get_payload(decode=True), "html.parser").get_text(separator=" ")
            m = re.search(r"\b(\d{4})\b", body)
            if m:
                result = m.group(1)
                break
    M.logout()
    return result

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
    print(f"URL: {page.url}", flush=True)

    # Estamos en la pantalla SMS — click "Más opciones"
    try:
        page.locator("text=Más opciones").first.click()
        print("Click 'Más opciones'", flush=True)
        page.wait_for_timeout(4000)
        page.screenshot(path=str(SCREEN / "mas_opciones.png"), full_page=True)
        (SCREEN / "mas_opciones.html").write_text(page.content())
    except Exception as ex:
        print(f"Más opciones err: {ex}", flush=True)

    # Ver qué opciones hay
    opts = page.eval_on_selector_all(
        "*",
        """els => [...new Set(els.filter(e => e.children.length === 0)
                    .map(e => e.textContent.trim())
                    .filter(t => /correo|email|llamada|voice|reenviar|texto|whatsapp/i.test(t) && t.length < 100))]"""
    )
    print("=== Opciones ===")
    for o in opts:
        print(f"  {o}", flush=True)

    # Click "Correo electrónico"
    try:
        page.locator("text=Correo electrónico").first.click(timeout=5000)
        print("Click 'Correo electrónico'", flush=True)
        page.wait_for_timeout(6000)
    except Exception as ex:
        print(f"Sin correo elec: {ex}", flush=True)

    # Ahora click "Inicia sesión con tu contraseña" — SALTAMOS el código de email
    try:
        page.locator("text=Inicia sesión con tu contraseña").first.click(timeout=10000)
        print("Click 'Inicia sesión con tu contraseña' — saltamos código", flush=True)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(SCREEN / "post_pwd_choice.png"), full_page=True)
    except Exception as ex:
        print(f"Sin atajo password: {ex}", flush=True)

    # Skip código — vamos directo a password
    codigo = None
    # Si estamos en pantalla de password, meter directo
    if page.locator('input[type="password"]').count() > 0:
        print("En pantalla de password", flush=True)
        pwd = page.locator('input[type="password"]').first
        pwd.click(); pwd.type(creds["password"], delay=100)
        page.wait_for_timeout(2500)
        try:
            page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=10000)
            page.locator("#forward-button").click()
            print("Password + Siguiente", flush=True)
        except: pass
        page.wait_for_load_state("domcontentloaded", timeout=45000)
        page.wait_for_timeout(10000)
        page.screenshot(path=str(SCREEN / "logged_in.png"), full_page=True)
        (SCREEN / "logged_in.html").write_text(page.content())
        print(f"FINAL URL: {page.url}", flush=True)
        print(f"Title: {page.title()}", flush=True)
        ctx.storage_state(path="/home/tito/.openclaw/credentials/uber_merchants/state.json")

    if False:  # bloque deshabilitado, ya no usamos código
        # Focus en el primer input y usar keyboard (Uber usa React con listeners)
        page.locator("#EMAIL_OTP_CODE-0").focus()
        page.wait_for_timeout(500)
        # Escribir cada dígito con press
        for digit in codigo:
            page.keyboard.press(digit)
            page.wait_for_timeout(250)
        page.wait_for_timeout(2500)

        # Password
        page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=10000)
        page.locator("#forward-button").click()
        page.wait_for_timeout(6000)

        if page.locator('input[type="password"]').count() > 0:
            pwd = page.locator('input[type="password"]').first
            pwd.click(); pwd.type(creds["password"], delay=100)
            page.wait_for_timeout(2500)
            page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=10000)
            page.locator("#forward-button").click()
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(10000)

        page.screenshot(path=str(SCREEN / "logged_in.png"), full_page=True)
        (SCREEN / "logged_in.html").write_text(page.content())
        print(f"FINAL URL: {page.url}", flush=True)
        ctx.storage_state(path="/home/tito/.openclaw/credentials/uber_merchants/state.json")
    else:
        print("Sin código en el correo tras 90s", flush=True)

    browser.close()
