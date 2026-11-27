#!/usr/bin/env python3
"""Login Uber Merchants (password path, fallback código email) y guardar state."""
import json, time, imaplib, email, re
from email.header import decode_header
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/uber_merchants/creds.json").read_text())
yahoo = json.loads(Path("/home/tito/.openclaw/credentials/yahoo/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_uber"); SCREEN.mkdir(exist_ok=True)
STATE = "/home/tito/.openclaw/credentials/uber_merchants/state.json"

def codigo_email(since_ts):
    for _ in range(18):  # ~90s
        time.sleep(5)
        try:
            M = imaplib.IMAP4_SSL(yahoo["imap_host"], yahoo["imap_port"])
            M.login(yahoo["user"], yahoo["password"])
            M.select("Inbox", readonly=True)
            for frm in ['admin@uber.com','noreply@uber.com','uber.com']:
                typ, ids = M.search(None, 'FROM', frm)
                if not ids[0]: continue
                for mid in sorted(ids[0].split(), key=lambda x:int(x), reverse=True)[:5]:
                    typ, data = M.fetch(mid, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    import email.utils
                    try: ts = email.utils.parsedate_to_datetime(msg.get("Date","")).timestamp()
                    except: continue
                    if ts < since_ts: continue
                    body=""
                    for p in msg.walk():
                        if p.get_content_type()=="text/plain":
                            body += p.get_payload(decode=True).decode(errors="replace")
                        elif p.get_content_type()=="text/html":
                            from bs4 import BeautifulSoup
                            body += BeautifulSoup(p.get_payload(decode=True),"html.parser").get_text(" ")
                    m = re.search(r"\b(\d{4})\b", body)
                    if m:
                        M.logout(); return m.group(1)
            M.logout()
        except Exception as e:
            print("imap err", e, flush=True)
    return None

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(viewport={"width":1600,"height":1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX", timezone_id="America/Tijuana")
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()
    page.goto("https://merchants.ubereats.com/manager", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    t0 = time.time()

    e = page.locator('input#PHONE_NUMBER_or_EMAIL_ADDRESS').first
    e.click(); e.type(creds["user"], delay=90)
    page.wait_for_timeout(1500)
    try:
        page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=12000)
        page.locator("#forward-button").click()
    except Exception as ex: print("fwd1", ex, flush=True)
    page.wait_for_timeout(6000)
    print("URL after email:", page.url, flush=True)

    # try password shortcut
    for label in ["Más opciones","Correo electrónico","Inicia sesión con tu contraseña"]:
        try:
            page.locator(f"text={label}").first.click(timeout=6000)
            print("click", label, flush=True); page.wait_for_timeout(4000)
        except Exception as ex: print("no", label, str(ex)[:60], flush=True)

    codigo=None
    if page.locator('input[type="password"]').count() > 0:
        pwd = page.locator('input[type="password"]').first
        pwd.click(); pwd.type(creds["password"], delay=90)
        page.wait_for_timeout(1500)
        try:
            page.wait_for_function("() => { const b=document.querySelector('#forward-button'); return b && !b.disabled; }", timeout=10000)
            page.locator("#forward-button").click(); print("password submitted", flush=True)
        except Exception as ex: print("pwdsubmit", ex, flush=True)
        page.wait_for_timeout(8000)

    # If code screen appears (OTP inputs)
    if page.locator('[id^="EMAIL_OTP_CODE"]').count() > 0 or "code" in page.url.lower():
        print("OTP screen, fetching email code...", flush=True)
        codigo = codigo_email(t0)
        print("codigo:", codigo, flush=True)
        if codigo:
            try:
                page.locator('[id^="EMAIL_OTP_CODE"]').first.focus()
                for d in codigo:
                    page.keyboard.press(d); page.wait_for_timeout(200)
                page.wait_for_timeout(3000)
                if page.locator("#forward-button").count()>0:
                    try: page.locator("#forward-button").click()
                    except: pass
            except Exception as ex: print("otp fill", ex, flush=True)
            page.wait_for_timeout(8000)

    page.wait_for_timeout(4000)
    print("FINAL URL:", page.url, flush=True)
    print("TITLE:", page.title(), flush=True)
    page.screenshot(path=str(SCREEN/"login_final.png"), full_page=True)
    if "auth.uber" not in page.url:
        ctx.storage_state(path=STATE)
        print("STATE SAVED — LOGGED IN", flush=True)
    else:
        print("STILL AT LOGIN", flush=True)
    browser.close()
