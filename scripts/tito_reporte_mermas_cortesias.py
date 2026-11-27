#!/usr/bin/env python3
"""Reporte diario de mermas y cortesías por carreta para Don Titi.
Mismo estilo visual que tito_reporte_diario_donTiti.py (mismo pastel/tabla), datos de
sr_mermas_cortesias.py (conexión SQL directa a cada sucursal, misma que el inventario/formas de pago).
"""
import json, sys, argparse, subprocess, time
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, "/home/tito/.openclaw/scripts")
from tito_reporte_diario_donTiti import fuente, _pastel, COLORES
import sr_mermas_cortesias as smc

OUT = Path("/home/tito/.openclaw/data/reportes_diarios")
OUT.mkdir(parents=True, exist_ok=True)
LOG = Path("/home/tito/.openclaw/logs/reporte_mermas_cortesias.log")
RAFAEL_WA = "+5216861445614"
DON_TITI_WA = "+5216861131003"
MARCO_WA = "+5216861606069"

# Reactivado 21-sep-2026: Rafael confirmó que la merma se captura por traspaso al almacén de
# MERMAS (ver sr_mermas_cortesias.py). Solo Hacienda y Cine Curto tienen esa bodega.
MOSTRAR_MERMA = True


def log(msg):
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea)
    with LOG.open("a") as f:
        f.write(linea + "\n")


def dibujar(desglose, fecha_dt, ruta):
    datos = [(n, d) for n, d in desglose.items() if d and "_error" not in d]
    tot_cort = sum(d["cortesias"] for _, d in datos)
    tot_merma_n = sum(d["merma_n"] for _, d in datos)

    W, H = 1100, 1500
    img = Image.new("RGB", (W, H), (248, 249, 250))
    dr = ImageDraw.Draw(img)

    titulo = "Cortesías y mermas" if MOSTRAR_MERMA else "Cortesías"
    dr.rectangle([0, 0, W, 155], fill=(30, 36, 46))
    dr.text((W // 2, 55), titulo, font=fuente(46, True), fill="white", anchor="mm")
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    sub = f"{dias[fecha_dt.weekday()]} {fecha_dt.day} de {meses[fecha_dt.month-1]} de {fecha_dt.year}"
    dr.text((W // 2, 110), sub, font=fuente(26), fill=(170, 178, 189), anchor="mm")

    if MOSTRAR_MERMA:
        r = 175
        cy = 400
        cxL, cxR = 300, 800
        dr.text((cxL, 190), "Cortesías por carreta", font=fuente(24, True), fill=(90, 96, 105), anchor="mm")
        dr.text((cxR, 190), "Mermas por carreta", font=fuente(24, True), fill=(90, 96, 105), anchor="mm")

        cort_items = [(d["cortesias"], COLORES[i % len(COLORES)]) for i, (n, d) in enumerate(datos) if d["cortesias"] > 0]
        if cort_items:
            _pastel(dr, cort_items, cxL, cy, r)
        else:
            dr.ellipse([cxL - r, cy - r, cxL + r, cy + r], outline=(200, 205, 212), width=3)
            dr.text((cxL, cy), "sin cortesías", font=fuente(24), fill=(160, 166, 175), anchor="mm")

        merma_items = [(d["merma_n"], COLORES[i % len(COLORES)]) for i, (n, d) in enumerate(datos) if d["merma_n"] > 0]
        if merma_items:
            _pastel(dr, merma_items, cxR, cy, r)
        else:
            dr.ellipse([cxR - r, cy - r, cxR + r, cy + r], outline=(200, 205, 212), width=3)
            dr.text((cxR, cy), "sin traspasos", font=fuente(24), fill=(160, 166, 175), anchor="mm")

        y = cy + r + 40
    else:
        dr.text((W // 2, 190), "Cortesías por carreta", font=fuente(24, True), fill=(90, 96, 105), anchor="mm")
        cort_items = [(d["cortesias"], COLORES[i % len(COLORES)]) for i, (n, d) in enumerate(datos) if d["cortesias"] > 0]
        if cort_items:
            _pastel(dr, cort_items, W // 2, 460, 220)
        else:
            dr.ellipse([W // 2 - 220, 240, W // 2 + 220, 680], outline=(200, 205, 212), width=3)
            dr.text((W // 2, 460), "sin cortesías", font=fuente(28), fill=(160, 166, 175), anchor="mm")
        y = 730

    col_carreta = 70
    col_cort = 610
    col_merma = 1030
    col_final = col_merma if MOSTRAR_MERMA else col_cort
    dr.text((col_carreta, y), "Carreta", font=fuente(20, True), fill=(120, 128, 138))
    dr.text((col_cort, y), "Cortesías", font=fuente(20, True), fill=(120, 128, 138), anchor="ra")
    if MOSTRAR_MERMA:
        dr.text((col_merma, y), "Merma", font=fuente(20, True), fill=(120, 128, 138), anchor="ra")
    y += 10
    dr.line([col_carreta, y + 28, col_final, y + 28], fill=(210, 215, 222), width=1)
    y += 40

    for i, (nombre, d) in enumerate(datos):
        dr.ellipse([col_carreta, y + 8, col_carreta + 22, y + 30], fill=COLORES[i % len(COLORES)])
        dr.text((col_carreta + 30, y + 6), nombre, font=fuente(27, True), fill=(35, 40, 48))
        dr.text((col_cort, y + 8), f"${d['cortesias']:,.0f}", font=fuente(25), fill=(70, 76, 86), anchor="ra")
        if MOSTRAR_MERMA:
            if smc.MERMAS_ALMACEN.get(nombre):
                etq_merma = f"{d['merma_n']} traspaso(s)"
            else:
                etq_merma = "sin bodega"
            dr.text((col_merma, y + 8), etq_merma, font=fuente(22), fill=(70, 76, 86), anchor="ra")
        y += 65

    faltantes = [n for n, d in desglose.items() if not d or "_error" in d]
    if faltantes:
        y += 10
        dr.text((col_carreta, y), "sin conectar aún: " + ", ".join(faltantes),
                font=fuente(18), fill=(150, 120, 60))
        y += 30

    y += 20
    dr.line([col_carreta, y, col_final, y], fill=(180, 185, 195), width=2)
    y += 30
    dr.text((col_carreta, y), "TOTAL", font=fuente(38, True), fill=(35, 40, 48))
    dr.text((col_cort, y + 4), f"${tot_cort:,.0f}", font=fuente(38, True), fill=(35, 40, 48), anchor="ra")
    if MOSTRAR_MERMA:
        dr.text((col_merma, y + 4), f"{tot_merma_n}", font=fuente(38, True), fill=(35, 40, 48), anchor="ra")

    img.save(ruta, quality=92)
    return tot_cort, tot_merma_n


def texto_wa(desglose, fecha_dt, tot_cort, tot_merma_n):
    titulo = "Cortesías y mermas" if MOSTRAR_MERMA else "Cortesías"
    lineas = [f"{titulo} — {fecha_dt.day}/{fecha_dt.month}/{fecha_dt.year}", ""]
    for nombre, d in sorted(desglose.items(), key=lambda x: -(x[1]["cortesias"] if x[1] and "_error" not in x[1] else -1)):
        if not d or "_error" in d:
            lineas.append(f"{nombre}: sin datos")
            continue
        linea = f"{nombre}: cortesías ${d['cortesias']:,.0f}"
        if MOSTRAR_MERMA:
            if smc.MERMAS_ALMACEN.get(nombre):
                linea += f" · merma {d['merma_n']} traspaso(s)"
                if d.get("ajuste_n"):
                    linea += f" (+{d['ajuste_n']} ajuste de inventario, no es merma)"
            else:
                linea += " · merma: sin bodega configurada"
        lineas.append(linea)
        for nota in d.get("merma_notas", []):
            lineas.append(f"    · {nota}")
    lineas.append("")
    lineas.append(f"TOTAL cortesías: ${tot_cort:,.0f}")
    if MOSTRAR_MERMA:
        lineas.append(f"TOTAL merma: {tot_merma_n} traspaso(s) (no se encontró el valor en pesos en Soft Restaurant, solo el registro)")
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
    a = ap.parse_args()

    fecha_dt = (datetime.now() - timedelta(days=1)).date() if not a.fecha else \
        datetime.strptime(a.fecha, "%Y-%m-%d").date()

    log(f"=== Reporte mermas/cortesías {fecha_dt} · enviar={a.enviar} ===")
    desglose = smc.datos_dia(fecha_dt)
    for n, d in desglose.items():
        log(f"  {n}: {d}")

    ruta = OUT / f"mermascortesias_{fecha_dt}.jpg"
    tot_cort, tot_merma_n = dibujar(desglose, datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day), ruta)
    log(f"  imagen: {ruta}")

    msg = texto_wa(desglose, datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day), tot_cort, tot_merma_n)
    if a.enviar == "rafael":
        mandar_wa(RAFAEL_WA, "Borrador del reporte de mermas/cortesías. Si algo está mal, dime antes "
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
