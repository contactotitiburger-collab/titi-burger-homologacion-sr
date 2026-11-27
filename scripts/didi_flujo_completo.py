#!/usr/bin/env python3
"""Login DiDi + aceptar rol + explorar finanzas todo en 1 flujo."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

creds = json.loads(Path("/home/tito/.openclaw/credentials/didi_restaurantes/creds.json").read_text())
SCREEN = Path("/home/tito/.openclaw/screens_didi")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="es-MX",
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page = ctx.new_page()

    # 1) LOGIN
    page.goto("https://www.didi-food.com/es-MX/manager", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(3000)
    page.locator('input[placeholder*="Número" i]').first.type(creds["user_phone"], delay=60)
    page.locator('input[type="password"]').first.type(creds["password"], delay=60)
    page.wait_for_timeout(1500)
    page.locator("div.button.actived").first.click()
    page.wait_for_timeout(6000)

    # 2) ACEPTAR ROL (Superadministrador seleccionado por default)
    try:
        aceptar = page.locator("button:has-text('Aceptar')").first
        aceptar.click(timeout=8000)
        print("Aceptar ✓", flush=True)
    except Exception as e:
        print(f"Sin modal Aceptar: {e}", flush=True)

    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(6000)

    # 3) Cerrar modal bienvenida
    try:
        skip = page.locator("text=Saltar").or_(page.locator("text=Skip")).first
        skip.click(timeout=5000)
        page.wait_for_timeout(2000)
        print("Saltar guía ✓", flush=True)
    except:
        pass

    page.screenshot(path=str(SCREEN / "didi_dashboard_ok.png"), full_page=True)
    print(f"URL: {page.url}", flush=True)

    # Navegar a Finanzas y Reportes
    for seccion, arch in [("Finanzas", "finanzas"), ("Tiendas", "tiendas"), ("Descargar reportes", "reportes")]:
        try:
            page.locator(f"text={seccion}").first.click(timeout=5000)
            page.wait_for_timeout(5000)
            page.screenshot(path=str(SCREEN / f"didi_{arch}.png"), full_page=True)
            (SCREEN / f"didi_{arch}.html").write_text(page.content())
            print(f"→ {seccion}: {page.url}", flush=True)
        except Exception as e:
            print(f"  {seccion} err: {e}", flush=True)

    # 4) Explorar sidebar completo
    print("\n=== TEXTOS visibles del sidebar (izquierda) ===")
    left_texts = page.evaluate("""() => {
        // Elementos en la columna izquierda (x < 250)
        const results = new Set();
        document.querySelectorAll('a, span, div, li').forEach(e => {
            const rect = e.getBoundingClientRect();
            const t = (e.textContent||'').trim();
            if (rect.x < 250 && rect.width < 250 && rect.height > 15 && rect.height < 60
                && t.length > 2 && t.length < 30 && e.children.length < 5) {
                results.add(t);
            }
        });
        return [...results];
    }""")
    for t in left_texts:
        print(f"  {t}", flush=True)

    # 5) Guardar todo el HTML del dashboard
    (SCREEN / "didi_dashboard_ok.html").write_text(page.content())

    # 6) Buscar tiendas / stores
    print("\n=== Info del dashboard visible ===")
    dash_texts = page.evaluate("""() => {
        return [...document.querySelectorAll('*')]
            .filter(e => e.children.length === 0 && (e.textContent||'').trim())
            .map(e => (e.textContent||'').trim())
            .filter(t => t.length > 2 && t.length < 200)
            .slice(0, 60);
    }""")
    for t in dash_texts[:40]:
        print(f"  {t}", flush=True)

    # Guardar cookies actualizadas
    cookies = ctx.cookies()
    Path("/home/tito/.openclaw/credentials/didi_restaurantes/cookies.json").write_text(json.dumps(cookies))

    browser.close()
