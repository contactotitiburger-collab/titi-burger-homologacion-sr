#!/usr/bin/env python3
"""Reporte diario de ventas por carreta para Don Titi."""
import json, sys, argparse, subprocess, math, re, time
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

sys.path.insert(0, "/home/tito/.openclaw/scripts")
try:
    from tito_formaspago_dia import formas_pago_dia
except Exception:
    formas_pago_dia = None

# Colores por categoría de forma de pago (pastel derecho)
COLOR_FP = {
    "Efectivo": (39, 174, 96), "Tarjeta": (41, 128, 185), "Rappi": (226, 74, 62),
    "DiDi": (243, 156, 18), "Uber": (44, 62, 80), "Otros": (149, 165, 166),
}

CREDS = json.loads(Path("/home/tito/.openclaw/credentials/sr_admin/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/reportes_diarios")
OUT.mkdir(parents=True, exist_ok=True)
LOG = Path("/home/tito/.openclaw/logs/reporte_diario.log")
RAFAEL_WA = "+5216861445614"
DON_TITI_WA = "+5216861131003"
MARCO_WA = "+5216861606069"
SUCS = {
    "12764": "L Montejano",
    "13056": "Montecarlo",
    "22980": "Hacienda del Río",
    "22871": "San Marcos",
    "23032": "Cine Curto",
    "26983": "Villas del Rey",
}
COLORES = [(226,74,62),(243,156,18),(39,174,96),(41,128,185),(142,68,173),(26,188,156)]


def log(msg):
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea)
    with LOG.open("a") as f:
        f.write(linea + "\n")


def scrape_dia(page, suc_id, fecha):
    """Venta de una sucursal en un día. Devuelve (tickets, total) o (0, 0)."""
    d = datetime.strptime(fecha, "%d/%m/%Y")
    fecha_fin = (d + timedelta(days=1)).strftime("%d/%m/%Y")
    for intento in range(3):
        try:
            page.goto("https://admin.softrestaurant.com/analytics/reportes/Consultar/1",
                      wait_until="domcontentloaded", timeout=60000)
            break
        except Exception as e:
            if intento == 2:
                raise
            log(f"  goto falló (intento {intento+1}/3): {e} — reintentando")
            page.wait_for_timeout(5000)
    page.wait_for_timeout(2500)
    for campo, val in (("#FechaInicial", fecha), ("#FechaFinal", fecha_fin)):
        page.evaluate("""([sel,v])=>{const el=document.querySelector(sel);
            el.value=v; el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true})); el.blur&&el.blur();}""",
            [campo, val])
    page.wait_for_timeout(300)
    page.evaluate(
        """(id)=>{const sel=document.querySelector('#ListaEmpresas');
        for(const o of sel.options) o.selected=(o.value===id);
        sel.dispatchEvent(new Event('change',{bubbles:true}));
        if(window.jQuery) window.jQuery(sel).trigger('change');}""", suc_id)
    page.wait_for_timeout(600)
    page.locator("#ActualizarReporte").first.click()
    try:
        page.wait_for_selector("#ExportarExcel", state="visible", timeout=180000)
    except Exception:
        log(f"  timeout en {SUCS.get(suc_id, suc_id)} — se reporta en cero")
        return 0, 0.0
    page.wait_for_timeout(3000)
    texto = page.evaluate("""() => {
        for (const t of document.querySelectorAll('table')) {
            const s = t.innerText || '';
            // el portal cambi\u00f3 el encabezado a "N\u00daMERO DE TICKETS" (con acento);
            // "MERO DE TICKETS" en may\u00fasculas cubre NUMERO / N\u00daMERO / N\u00famero
            if ((s.toUpperCase()).includes('MERO DE TICKETS')) return s;
        }
        return '';
    }""")
    m = re.search(r"(\d[\d,]*)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)\s*\$([\d,\.]+)", texto)
    if not m:
        log(f"  sin tabla de resumen en {SUCS.get(suc_id, suc_id)} — se reporta en cero")
        return 0, 0.0
    tickets = int(m.group(1).replace(",", ""))
    total = float(m.group(6).replace(",", ""))
    return tickets, total


def sacar_ventas(fecha, fecha_ly):
    hoy, pasado = {}, {}
    with sync_playwright() as p:
        nav = p.chromium.launch(headless=True)
        page = nav.new_page()
        page.goto(CREDS["panel"], wait_until="networkidle", timeout=45000)
        page.evaluate("AbrirModal()")
        page.wait_for_timeout(1500)
        page.locator('input[type="email"]').first.fill(CREDS["user"])
        page.locator('input[type="password"]').first.fill(CREDS["password"])
        page.locator('button[type="submit"]').first.click()
        page.wait_for_load_state("networkidle", timeout=45000)
        page.wait_for_timeout(2500)
        for sid, nombre in SUCS.items():
            t, v = scrape_dia(page, sid, fecha)
            hoy[nombre] = {"tickets": t, "total": v}
            log(f"  {nombre}: {t} tickets · ${v:,.2f}")
        for sid, nombre in SUCS.items():
            _, v = scrape_dia(page, sid, fecha_ly)
            pasado[nombre] = v
            log(f"  {nombre} (año pasado): ${v:,.2f}")
        nav.close()
    return hoy, pasado



def fuente(tam, negrita=False):
    base = "/usr/share/fonts/truetype/dejavu/DejaVuSans"
    ruta = f"{base}-Bold.ttf" if negrita else f"{base}.ttf"
    try:
        return ImageFont.truetype(ruta, tam)
    except OSError:
        return ImageFont.load_default()


def _pastel(dr, items, cx, cy, r, umbral=16):
    """Dibuja un pastel. items = [(valor, color)]. Etiqueta % dentro de rebanadas grandes."""
    total = sum(v for v, _ in items)
    ang = -90.0
    for valor, color in items:
        barrido = valor / total * 360 if total else 0
        dr.pieslice([cx - r, cy - r, cx + r, cy + r], ang, ang + barrido,
                    fill=color, outline="white", width=3)
        if barrido >= umbral:
            med = math.radians(ang + barrido / 2)
            tx = cx + math.cos(med) * r * 0.62
            ty = cy + math.sin(med) * r * 0.62
            etq = f"{valor / total * 100:.0f}%"
            fz = max(20, int(r * 0.12))
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                dr.text((tx + ox, ty + oy), etq, font=fuente(fz, True), fill="black", anchor="mm")
            dr.text((tx, ty), etq, font=fuente(fz, True), fill="white", anchor="mm")
        ang += barrido


def dibujar(hoy, pasado, fecha, ruta, formas=None):
    datos = sorted(hoy.items(), key=lambda x: -x[1]["total"])
    datos = [(n, d) for n, d in datos if d["total"] > 0]
    total = sum(d["total"] for _, d in datos)
    total_ly = sum(pasado.get(n, 0) for n, _ in datos)

    dos_pasteles = bool(formas) and formas.get("total_sql", 0) > 0
    W, H = 1100, (1660 if dos_pasteles else 1500)
    img = Image.new("RGB", (W, H), (248, 249, 250))
    dr = ImageDraw.Draw(img)

    # 1. Header oscuro (30,36,46)
    dr.rectangle([0, 0, W, 155], fill=(30, 36, 46))
    dr.text((W // 2, 55), "Ventas por carreta", font=fuente(46, True), fill="white", anchor="mm")
    d = datetime.strptime(fecha, "%d/%m/%Y")
    dias  = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    sub = f"{dias[d.weekday()]} {d.day} de {meses[d.month-1]} de {d.year}"
    dr.text((W // 2, 110), sub, font=fuente(26), fill=(170, 178, 189), anchor="mm")

    if dos_pasteles:
        # 2a. DOS pasteles lado a lado: ventas (izq) y formas de pago (der)
        r = 175
        cy = 400
        cxL, cxR = 300, 800
        dr.text((cxL, 190), "Por carreta", font=fuente(24, True), fill=(90, 96, 105), anchor="mm")
        dr.text((cxR, 190), "Por forma de pago", font=fuente(24, True), fill=(90, 96, 105), anchor="mm")
        _pastel(dr, [(dd["total"], COLORES[i % len(COLORES)]) for i, (n, dd) in enumerate(datos)],
                cxL, cy, r)
        # El pastel solo dibuja rebanadas con venta (>0)
        fp = [(k, v) for k, v in formas["agg"].items() if v > 0]
        _pastel(dr, [(v, COLOR_FP.get(k, (150, 150, 150))) for k, v in fp], cxR, cy, r)
        # Leyenda: SIEMPRE muestra Efectivo/Tarjeta/Rappi/DiDi/Uber (0% si no hubo);
        # "Otros" solo si tuvo venta.
        tot_fp = formas["total_sql"]
        orden_leg = ["Efectivo", "Tarjeta", "Rappi", "DiDi", "Uber"]
        if formas["agg"].get("Otros", 0) > 0:
            orden_leg.append("Otros")
        ly_y = cy + r + 30
        for k in orden_leg:
            v = formas["agg"].get(k, 0)
            pct = v / tot_fp * 100 if tot_fp else 0
            gris = v <= 0
            dr.rectangle([620, ly_y + 4, 640, ly_y + 24],
                         fill=(210, 214, 218) if gris else COLOR_FP.get(k, (150, 150, 150)))
            dr.text((650, ly_y), f"{k}", font=fuente(21, True),
                    fill=(160, 166, 172) if gris else (45, 50, 58))
            dr.text((1000, ly_y + 2), f"${v:,.0f}  ({pct:.0f}%)",
                    font=fuente(20), fill=(160, 166, 172) if gris else (70, 76, 86), anchor="ra")
            ly_y += 30
        # Nota de cobertura (honestidad): qué carretas no entraron y por qué
        ly_y += 10
        # apagadas = conectadas pero apagadas al medir → FALTÓ ese día: nota NOTABLE
        if formas.get("apagadas"):
            falto = ", ".join(formas["apagadas"])
            txt = f"FALTÓ HOY:  {falto}"
            f2 = fuente(22, True)
            bb = dr.textbbox((0, 0), txt, font=f2)
            wtxt = bb[2] - bb[0]
            x0, x1 = cxR - wtxt // 2 - 18, cxR + wtxt // 2 + 18
            dr.rectangle([x0, ly_y, x1, ly_y + 40], fill=(255, 220, 220), outline=(200, 60, 55), width=2)
            dr.text((cxR, ly_y + 20), txt, font=f2, fill=(190, 35, 35), anchor="mm")
            ly_y += 52
        # sin_sql = nunca conectadas (Montejano/Montecarlo): nota chica, es lo esperado
        if formas.get("sin_sql"):
            dr.text((cxR, ly_y + 6), f"sin conectar aún: {', '.join(formas['sin_sql'])}",
                    font=fuente(16), fill=(150, 120, 60), anchor="mm")
            ly_y += 24
        y = max(790, ly_y + 20)
    else:
        # 2b. UN pastel centrado con PORCENTAJES dentro de cada rebanada
        _pastel(dr, [(dd["total"], COLORES[i % len(COLORES)]) for i, (n, dd) in enumerate(datos)],
                W // 2, 440, 255)
        y = 750

    # 3. Tabla: Carreta | Venta | Del total | vs anio pasado
    col_carreta = 70
    col_venta   = 510
    col_del_tot = 680
    col_vs_ly   = 1060

    # Encabezados
    dr.text((col_carreta, y), "Carreta",      font=fuente(20, True), fill=(120, 128, 138))
    dr.text((col_venta,   y), "Venta",        font=fuente(20, True), fill=(120, 128, 138), anchor="ra")
    dr.text((col_del_tot, y), "Del total",    font=fuente(20, True), fill=(120, 128, 138), anchor="ra")
    dr.text((col_vs_ly,   y), "vs año pasado", font=fuente(20, True), fill=(120, 128, 138), anchor="ra")
    y += 10
    dr.line([col_carreta, y + 28, col_vs_ly, y + 28], fill=(210, 215, 222), width=1)
    y += 40

    # Filas de datos
    for i, (nombre, dd) in enumerate(datos):
        dr.ellipse([col_carreta, y + 8, col_carreta + 22, y + 30],
                   fill=COLORES[i % len(COLORES)])
        dr.text((col_carreta + 30, y + 6), nombre, font=fuente(27, True), fill=(35, 40, 48))
        dr.text((col_venta, y + 8), f"${dd['total']:,.0f}",
                font=fuente(25), fill=(70, 76, 86), anchor="ra")
        pct_tot = dd["total"] / total * 100 if total else 0
        dr.text((col_del_tot, y + 8), f"{pct_tot:.1f}%",
                font=fuente(25), fill=(70, 76, 86), anchor="ra")
        ly = pasado.get(nombre, 0)
        if ly > 0:
            cambio_pct = (dd["total"] - ly) / ly * 100
            signo = "+" if cambio_pct >= 0 else ""
            col_vs = (39, 150, 90) if cambio_pct >= 0 else (200, 60, 55)
            etq_ly = f"{signo}{cambio_pct:.0f}% (${ly:,.0f})"
            dr.text((col_vs_ly, y + 8), etq_ly, font=fuente(22, True), fill=col_vs, anchor="ra")
        else:
            dr.text((col_vs_ly, y + 8), "sin dato", font=fuente(22), fill=(160, 166, 175), anchor="ra")
        y += 65

    # 4. Separador horizontal
    y += 10
    dr.line([col_carreta, y, col_vs_ly, y], fill=(180, 185, 195), width=2)
    y += 30

    # 5. Fila TOTAL — el monto va VERDE si vendió más que el año pasado, ROJO si menos
    if total_ly > 0:
        cambio_total = (total - total_ly) / total_ly * 100
        col_total = (39, 150, 90) if total >= total_ly else (200, 55, 50)
    else:
        col_total = (35, 40, 48)  # sin comparación: neutro
    dr.text((col_carreta, y), "TOTAL", font=fuente(38, True), fill=(35, 40, 48))
    dr.text((col_venta, y + 4), f"${total:,.0f}", font=fuente(38, True), fill=col_total, anchor="ra")
    if total_ly > 0:
        signo = "+" if cambio_total >= 0 else ""
        etq_total = f"{signo}{cambio_total:.0f}% vs {d.year - 1}"
        dr.text((col_vs_ly, y + 8), etq_total, font=fuente(28, True), fill=col_total, anchor="ra")

    img.save(ruta, quality=92)
    return total, total_ly


def texto_wa(hoy, pasado, fecha, total, total_ly, formas=None):
    d = datetime.strptime(fecha, "%d/%m/%Y")
    d_ly = d - timedelta(days=364)  # mismo día de la semana del año pasado
    dias_cortos = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    etq_ly_fecha = f"{dias_cortos[d_ly.weekday()]} {d_ly.day}/{d_ly.month}/{d_ly.year}"
    lineas = [f"Ventas de ayer — {d.day}/{d.month}/{d.year}", ""]
    for nombre, dd in sorted(hoy.items(), key=lambda x: -x[1]["total"]):
        if dd["total"] <= 0:
            continue
        ly = pasado.get(nombre, 0)
        if ly > 0:
            dif = dd["total"] - ly
            comp = f"  (año pasado ${ly:,.0f}, {"+" if dif>=0 else "-"}${abs(dif):,.0f})"
        else:
            comp = ""
        lineas.append(f"{nombre}: ${dd['total']:,.0f}{comp}")
    lineas.append("")
    if total_ly > 0:
        dif = total - total_ly
        lineas.append(f"TOTAL hoy: ${total:,.0f}")
        lineas.append(f"Mismo día año pasado ({etq_ly_fecha}): ${total_ly:,.0f}")
        lineas.append(f"Diferencia: {"+" if dif>=0 else "-"}${abs(dif):,.0f}")
    else:
        lineas.append(f"TOTAL hoy: ${total:,.0f}")

    # Bloque de formas de pago (solo carretas con SQL conectado)
    if formas and formas.get("total_sql", 0) > 0:
        tot_fp = formas["total_sql"]
        lineas.append("")
        lineas.append("Formas de pago:")
        orden = ["Efectivo", "Tarjeta", "Rappi", "DiDi", "Uber"]
        if formas["agg"].get("Otros", 0) > 0:
            orden.append("Otros")
        for cat in orden:
            monto = formas["agg"].get(cat, 0)
            pct = monto / tot_fp * 100 if tot_fp else 0
            lineas.append(f"{cat}: ${monto:,.0f} ({pct:.0f}%)")
        cubiertas = [n for n, _ in formas.get("cubiertas", [])]
        if cubiertas:
            lineas.append(f"(carretas medidas: {', '.join(cubiertas)})")
        if formas.get("sin_sql"):
            lineas.append(f"(sin conectar aún: {', '.join(formas['sin_sql'])})")
        if formas.get("apagadas"):
            lineas.append(f"(apagadas al medir: {', '.join(formas['apagadas'])})")
    return "\n".join(lineas)


def mandar_wa(numero, mensaje, imagen=None, intentos=3):
    if imagen:
        imagen = Path(imagen).resolve()
    cmd = ["openclaw", "message", "send", "--channel", "whatsapp",
           "--target", numero, "--message", mensaje]
    if imagen:
        cmd += ["--media", str(imagen)]
    ultimo_err = ""
    for i in range(1, intentos + 1):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            log(f"  enviado a {numero}" + (f" (intento {i})" if i > 1 else ""))
            return True
        ultimo_err = r.stderr.strip()[:200]
        log(f"  intento {i}/{intentos} falló mandando a {numero}: {ultimo_err}")
        if i < intentos:
            time.sleep(5)
    log(f"  ERROR mandando a {numero} tras {intentos} intentos: {ultimo_err}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    ap.add_argument("--enviar", choices=["rafael", "donTiti", "ambos", "ninguno"], default="ninguno")
    ap.add_argument("--con-formaspago", action="store_true",
                    help="agrega el segundo pastel de formas de pago (SQL local por carreta)")
    a = ap.parse_args()

    fecha = a.fecha or (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    d = datetime.strptime(fecha, "%d/%m/%Y")
    # Comparar contra el MISMO día de la semana del año pasado: 52 semanas exactas
    # (364 días) atrás siempre cae en el mismo día de semana (lunes vs lunes).
    fecha_ly = (d - timedelta(days=364)).strftime("%d/%m/%Y")

    log(f"=== Reporte {fecha} (comparando contra {fecha_ly}) · enviar={a.enviar} ===")
    hoy, pasado = sacar_ventas(fecha, fecha_ly)

    if sum(v["total"] for v in hoy.values()) <= 0:
        log("SIN VENTAS — no se manda nada. Revisar el portal.")
        mandar_wa(RAFAEL_WA, f"El reporte diario del {fecha} salió en ceros. "
                             "No lo mandé a Don Titi. Hay que revisar Soft Restaurant.")
        return 1

    formas = None
    if a.con_formaspago and formas_pago_dia:
        try:
            formas = formas_pago_dia(d.strftime("%Y-%m-%d"))
            log(f"  formas de pago: cubiertas={len(formas['cubiertas'])} "
                f"faltan={formas['faltantes']} total_sql=${formas['total_sql']:,.0f}")
        except Exception as e:
            log(f"  formas de pago no disponibles: {e}")
            formas = None

    ruta = OUT / f"ventas_{d:%Y-%m-%d}.jpg"
    total, total_ly = dibujar(hoy, pasado, fecha, ruta, formas)
    (OUT / f"ventas_{d:%Y-%m-%d}.json").write_text(
        json.dumps({"fecha": fecha, "hoy": hoy, "año_pasado": pasado}, ensure_ascii=False, indent=1))
    log(f"  imagen: {ruta}")

    msg = texto_wa(hoy, pasado, fecha, total, total_ly, formas)
    if a.enviar == "rafael":
        mandar_wa(RAFAEL_WA, "Borrador del reporte para Don Titi. Si algo está mal, dime antes "
                             "de las 12.\n\n" + msg, ruta)
    elif a.enviar == "donTiti":
        mandar_wa(DON_TITI_WA, msg, ruta)
        mandar_wa(MARCO_WA, msg, ruta)
    elif a.enviar == "ambos":
        mandar_wa(DON_TITI_WA, msg, ruta)
        mandar_wa(RAFAEL_WA, msg, ruta)
        mandar_wa(MARCO_WA, msg, ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
