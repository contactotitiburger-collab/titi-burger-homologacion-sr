#!/usr/bin/env python3
"""Probar si el state.json de Uber Merchants sigue autenticado."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREEN = Path("/home/tito/.openclaw/screens_uber"); SCREEN.mkdir(exist_ok=True)
state = "/home/tito/.openclaw/credentials/uber_merchants/state.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        storage_state=state,
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX", timezone_id="America/Tijuana",
    )
    page = ctx.new_page()
    page.goto("https://merchants.ubereats.com/manager", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(9000)
    print("URL:", page.url, flush=True)
    print("TITLE:", page.title(), flush=True)
    page.screenshot(path=str(SCREEN / "state_test.png"), full_page=True)
    txt = page.evaluate("() => document.body.innerText")
    Path("/home/tito/.openclaw/data/uber_state_test.txt").write_text(txt)
    logged = "login" not in page.url.lower() and "auth" not in page.url.lower()
    print("LOGGED_IN_GUESS:", logged, flush=True)
    print("FIRST 600 CHARS:\n", txt[:600], flush=True)
    browser.close()
