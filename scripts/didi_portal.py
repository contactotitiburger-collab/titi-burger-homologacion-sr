#!/usr/bin/env python3
"""Entrar al portal DiDi Restaurantes y explorar."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")
SCREEN.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    # Portal DiDi Merchant (login típico)
    URLS = [
        "https://d.didiglobal.com/",
        "https://web.didiglobal.com/mx/food/restaurantes/",
        "https://mx.didiglobal.com/",
    ]

    for url in URLS:
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            print(f"→ {url}", flush=True)
            print(f"  URL final: {page.url}", flush=True)
            print(f"  Título: {page.title()}", flush=True)
            # Buscar link de login
            login_links = page.eval_on_selector_all(
                "a",
                """els => els.filter(e => /iniciar sesi|ingresar|login|acceder|entrar|merchant|comerciant/i.test(e.textContent + " " + (e.href||"")))
                                .map(e => ({text: e.textContent.trim().slice(0,50), href: e.href}))
                                .slice(0, 8)"""
            )
            for L in login_links:
                print(f"  LINK: {L['text']!r} → {L['href']}", flush=True)
            page.screenshot(path=str(SCREEN / f"landing_{url.replace('://','_').replace('/','_')[:50]}.png"), full_page=True)
        except Exception as e:
            print(f"  ERR: {e}", flush=True)

    browser.close()
