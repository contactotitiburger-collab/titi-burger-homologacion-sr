#!/usr/bin/env python3
"""Abre el portal DiDi Food Restaurantes y captura la landing."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREEN_DIR = Path("/home/tito/.openclaw/screens_didi")
SCREEN_DIR.mkdir(exist_ok=True)

URLS = [
    "https://web.didiglobal.com/mx/food/restaurantes/",
    "https://d-food.didiglobal.com/",  # portal login típico
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    for i, url in enumerate(URLS, start=1):
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            print(f"[{i}] {url} → status ok", flush=True)
            print(f"    Final URL: {page.url}", flush=True)
            print(f"    Title: {page.title()}", flush=True)
            page.screenshot(path=str(SCREEN_DIR / f"didi_{i}.png"), full_page=True)

            # Buscar link de "Iniciar sesión" / "Inicia sesión" / "Login"
            login_links = page.eval_on_selector_all(
                "a",
                """els => els.filter(e => /iniciar sesi|inicia sesi|login|acceder|entrar/i.test(e.textContent))
                                .map(e => ({text: e.textContent.trim(), href: e.href}))
                                .slice(0, 5)"""
            )
            for L in login_links:
                print(f"    LOGIN LINK: {L}", flush=True)
        except Exception as e:
            print(f"[{i}] {url} → ERROR: {e}", flush=True)
    browser.close()
