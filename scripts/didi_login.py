#!/usr/bin/env python3
"""Login DiDi Tienda (portal merchant)."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
    page = ctx.new_page()

    page.goto("https://didi.tienda/Account/LogOn", wait_until="networkidle", timeout=45000)
    print(f"URL: {page.url}", flush=True)
    print(f"Title: {page.title()}", flush=True)
    page.screenshot(path=str(SCREEN / "didi_login_landing.png"), full_page=True)
    (SCREEN / "didi_login_landing.html").write_text(page.content())

    # Inspeccionar inputs
    inputs = page.eval_on_selector_all(
        "input, button",
        "els => els.map(e => ({tag: e.tagName, type: e.type||'', name: e.name||'', id: e.id||'', placeholder: e.placeholder||'', label: e.textContent||''}))"
    )
    for i in inputs[:20]:
        print(f"  {i}", flush=True)

    browser.close()
