#!/usr/bin/env python3
"""Reporte food cost + gastos junio 2026 desde 2 fuentes:
- Yahoo IMAP (titiburger_cordova@yahoo.com.mx)
- Gmail Andrónica OAuth (andronica.bautista2022@gmail.com)

Baja adjuntos XML/PDF de junio 2026, parsea CFDI, clasifica por categoría,
genera Excel con reporte y lo sube a Drive/Indicadores Don Titi.
"""
import base64
import email
import imaplib
import json
import re
import time
from collections import defaultdict
from datetime import date, datetime
from email import policy
from email.header import decode_header
from pathlib import Path
import xml.etree.ElementTree as ET

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ---- Config ----
OUT_XML = Path.home() / ".openclaw/data/facturas_junio_2026"
OUT_XML.mkdir(parents=True, exist_ok=True)
OUT_XLSX = Path.home() / ".openclaw/workspace/apps_delivery/Food cost junio 2026.xlsx"
LOG = Path.home() / ".openclaw/logs/food_cost_junio.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

# Clasificación por keyword en emisor / RFC / email
CLASIFICACION = [
    # (categoria, subcat, patrones)
    ("FOOD", "Carne — Bona/Distribuidora",   ["bona", "gargu", "garcia guillen", "mayorista"]),
    ("FOOD", "Carne — Julián/otros",         ["julian", "carniceria", "casa carp", "cahr530914", "campos herrera"]),
    ("FOOD", "Tocino — Kowi",                ["kowi", "kochi", "yuexian"]),
    ("FOOD", "Pollo — Islas",                ["islas", "avicola", "pollo"]),
    ("FOOD", "Supermercado (Smart)",         ["smart", "smart-and-final"]),
    ("FOOD", "Punto de Venta Gran Vía",      ["puntodeventagranvia", "gran via"]),
    ("FOOD", "Refrescos / bebidas",          ["coca-cola", "coca cola", "cocacola", "pepsi", "arca continental"]),
    ("FOOD", "Empaques / desechables",       ["empaque", "desechable"]),
    ("FOOD", "Otros insumos",                ["carboneria", "pueblo viejo", "expresion"]),

    ("SERVICIOS", "Gas Ecogas",              ["ecogas", "sempraglobal"]),
    ("SERVICIOS", "Luz CFE",                 ["cfe", "comision federal"]),
    ("SERVICIOS", "Agua Mexicali (CESPM)",   ["cespm", "comision estatal de servicios"]),
    ("SERVICIOS", "Internet / teléfono",     ["telnor", "telcel", "att-mail", "att.com.mx", "internet"]),

    ("GASOLINA", "El Rey",                   ["el rey", "elrey", "combustibles el rey"]),
    ("GASOLINA", "Petro Seven",              ["petro seven", "petro-7"]),
    ("GASOLINA", "Otras gasolineras",        ["gasolinera"]),

    ("HONORARIOS", "Contable / abogado",     ["decono", "facturama", "gruposago", "capacitacion"]),

    ("OTROS", "Rentas / instituciones",      ["paccelli", "institucion", "arrendamiento"]),
    ("OTROS", "Autos / vehículos",           ["velocity", "vehiculos"]),
]

RESUMEN = defaultdict(lambda: {"count": 0, "total": 0.0, "detalles": []})
TODOS = []


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def clasificar(emisor: str, from_email: str = "") -> tuple[str, str]:
    texto = (emisor + " " + from_email).lower()
    for cat, sub, patrones in CLASIFICACION:
        if any(p in texto for p in patrones):
            return cat, sub
    return "OTROS", "Sin clasificar"


def parse_xml_cfdi(xml_bytes: bytes, source: str, from_email: str) -> dict | None:
    try:
        text = xml_bytes.decode("utf-8", errors="ignore")
        text = text.lstrip("﻿")  # quitar BOM si aplica
        root = ET.fromstring(text)
    except Exception as e:
        return None

    # namespace del cfd/cfdi
    tag = root.tag
    total = root.get("Total") or root.get("total")
    subtotal = root.get("SubTotal") or root.get("subtotal")
    fecha = root.get("Fecha") or root.get("fecha")
    tipo = root.get("TipoDeComprobante") or root.get("tipoDeComprobante") or ""
    if not total:
        return None
    try:
        total = float(total)
    except:
        return None
    # solo Ingresos (I) → factura de venta hacia nosotros
    if tipo and tipo.upper() not in ("I", "INGRESO"):
        return None
    emisor_nombre = ""
    emisor_rfc = ""
    receptor_rfc = ""
    for child in root:
        low = child.tag.lower()
        if low.endswith("emisor"):
            emisor_nombre = child.get("Nombre") or child.get("nombre") or ""
            emisor_rfc = child.get("Rfc") or child.get("rfc") or ""
        elif low.endswith("receptor"):
            receptor_rfc = child.get("Rfc") or child.get("rfc") or ""

    cat, sub = clasificar(emisor_nombre, from_email)
    return {
        "source": source,
        "fecha": fecha,
        "total": total,
        "subtotal": float(subtotal) if subtotal else None,
        "tipo": tipo,
        "emisor_nombre": emisor_nombre,
        "emisor_rfc": emisor_rfc,
        "receptor_rfc": receptor_rfc,
        "from_email": from_email,
        "categoria": cat,
        "subcategoria": sub,
    }


def guardar_hallazgo(h):
    key = f"{h['categoria']}  ·  {h['subcategoria']}"
    RESUMEN[key]["count"] += 1
    RESUMEN[key]["total"] += h["total"]
    RESUMEN[key]["detalles"].append(h)
    TODOS.append(h)


def procesar_yahoo():
    log("=== YAHOO ===")
    creds = json.loads((Path.home()/".openclaw/credentials/yahoo/creds.json").read_text())
    M = imaplib.IMAP4_SSL(creds.get("imap_host") or "imap.mail.yahoo.com")
    M.login(creds.get("user") or creds.get("email"), creds.get("app_password") or creds.get("password"))

    typ, folders = M.list()
    carpetas = [f.decode().split(' "/" ')[-1].strip().strip('"') for f in folders]
    log(f"Carpetas: {len(carpetas)}")

    procesados = 0
    for carp in carpetas:
        try:
            M.select(f'"{carp}"', readonly=True)
            typ, data = M.search(None, 'SINCE 01-Jun-2026 BEFORE 01-Jul-2026')
            ids = data[0].split() if data and data[0] else []
            if not ids:
                continue
            log(f"[Yahoo:{carp}] {len(ids)} correos junio")
            for uid in ids:
                try:
                    typ, d = M.fetch(uid, "(BODY.PEEK[])")
                    if not d or not d[0]:
                        continue
                    raw = d[0][1]
                    msg = email.message_from_bytes(raw, policy=policy.default)
                    from_email = msg.get("From", "").lower()
                    for part in msg.walk():
                        fname = part.get_filename() or ""
                        try:
                            fname_dec = "".join(
                                t.decode(e or "utf-8", errors="ignore") if isinstance(t, bytes) else t
                                for t, e in decode_header(fname)
                            )
                        except:
                            fname_dec = fname
                        if not fname_dec.lower().endswith(".xml"):
                            continue
                        contenido = part.get_payload(decode=True)
                        if not contenido:
                            continue
                        safe = re.sub(r"[^\w.-]", "_", fname_dec)[:60]
                        dest = OUT_XML / f"yahoo__{uid.decode()}__{safe}"
                        dest.write_bytes(contenido)
                        h = parse_xml_cfdi(contenido, "Yahoo", from_email)
                        if h:
                            guardar_hallazgo(h)
                            procesados += 1
                except Exception as e:
                    continue
        except Exception as e:
            log(f"[Yahoo:{carp}] ERROR carpeta: {e}")
    M.logout()
    log(f"Yahoo: {procesados} facturas parseadas")


def procesar_andronica():
    log("=== GMAIL ANDRÓNICA ===")
    TOK = json.loads((Path.home()/".openclaw/credentials/google/oauth/andronica_tokens.json").read_text())
    creds = Credentials(token=TOK["token"], refresh_token=TOK["refresh_token"], token_uri=TOK["token_uri"],
        client_id=TOK["client_id"], client_secret=TOK["client_secret"], scopes=TOK["scopes"])
    if not creds.valid:
        creds.refresh(Request())
    svc = build("gmail", "v1", credentials=creds)

    # búsqueda de facturas junio
    query = "after:2026/06/01 before:2026/07/01 (factura OR CFDI OR recibo OR invoice OR comprobante)"
    msg_ids = []
    token = None
    while True:
        r = svc.users().messages().list(userId="me", q=query, maxResults=500, pageToken=token).execute()
        msg_ids.extend(m["id"] for m in r.get("messages", []))
        token = r.get("nextPageToken")
        if not token:
            break
    log(f"Gmail Andrónica: {len(msg_ids)} correos a procesar")

    procesados = 0
    for i, mid in enumerate(msg_ids):
        try:
            msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            from_email = headers.get("from", "").lower()

            # recorrer partes buscando XMLs
            def walk_parts(part):
                if part.get("filename", "").lower().endswith(".xml"):
                    body = part.get("body", {})
                    att_id = body.get("attachmentId")
                    if att_id:
                        att = svc.users().messages().attachments().get(
                            userId="me", messageId=mid, id=att_id).execute()
                        data = att.get("data", "")
                        if data:
                            contenido = base64.urlsafe_b64decode(data)
                            safe = re.sub(r"[^\w.-]", "_", part["filename"])[:60]
                            dest = OUT_XML / f"gmail__{mid}__{safe}"
                            dest.write_bytes(contenido)
                            h = parse_xml_cfdi(contenido, "Gmail-Andronica", from_email)
                            if h:
                                guardar_hallazgo(h)
                                return 1
                for sp in part.get("parts", []):
                    if walk_parts(sp):
                        return 1
                return 0

            proc = walk_parts(msg.get("payload", {}))
            if proc:
                procesados += 1
            if (i + 1) % 25 == 0:
                log(f"  … {i+1}/{len(msg_ids)}  (parseados: {procesados})")
        except Exception as e:
            continue
    log(f"Gmail Andrónica: {procesados} facturas parseadas")


def generar_excel():
    log("=== GENERANDO EXCEL ===")
    wb = Workbook()

    # ---- Hoja Resumen ----
    ws = wb.active
    ws.title = "Resumen"
    ws.sheet_view.showGridLines = False
    for i, w in enumerate([3, 32, 20, 12, 14, 3], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    F_TIT = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    F_HDR = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    F_LBL = Font(name="Calibri", size=10, bold=True, color="1F3864")
    F_NUM = Font(name="Calibri", size=10)
    F_TOT = Font(name="Calibri", size=11, bold=True)
    FILL_TIT = PatternFill("solid", fgColor="1F3864")
    FILL_HDR = PatternFill("solid", fgColor="2E5C99")
    FILL_LBL = PatternFill("solid", fgColor="D9E2F3")
    FILL_TOT = PatternFill("solid", fgColor="FFE699")
    B = Side(style="thin", color="BFBFBF")
    BORDE = Border(left=B, right=B, top=B, bottom=B)

    ws.merge_cells("B2:E2")
    c = ws.cell(2, 2, "FOOD COST + GASTOS · JUNIO 2026")
    c.font = F_TIT; c.fill = FILL_TIT
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 32

    ws.merge_cells("B3:E3")
    c = ws.cell(3, 3-1, f"Fuente: Yahoo + Gmail Andrónica  ·  Generado {datetime.now().strftime('%d-%b-%Y %H:%M')}")
    c.font = Font(name="Calibri", size=10, italic=True, color="595959")
    c.alignment = Alignment(horizontal="center")

    # Headers
    for i, h in enumerate(["Categoría · Subcategoría", "Emisores", "Facturas", "Total $"], start=2):
        c = ws.cell(5, i, h); c.font = F_HDR; c.fill = FILL_HDR; c.border = BORDE
        c.alignment = Alignment(horizontal="center", vertical="center")

    fila = 6
    orden_cat = ["FOOD", "SERVICIOS", "GASOLINA", "HONORARIOS", "OTROS"]
    totales_cat = defaultdict(float)
    for cat in orden_cat:
        rows_cat = [(k, v) for k, v in RESUMEN.items() if k.startswith(cat)]
        if not rows_cat:
            continue
        # header categoría
        ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=5)
        c = ws.cell(fila, 2, cat); c.font = F_LBL; c.fill = FILL_LBL
        c.alignment = Alignment(horizontal="left", indent=1)
        fila += 1
        for k, v in sorted(rows_cat, key=lambda x: -x[1]["total"]):
            emisores_unicos = len(set(d["emisor_nombre"] for d in v["detalles"]))
            ws.cell(fila, 2, "  " + k.split("·")[1].strip()).font = F_NUM
            ws.cell(fila, 3, emisores_unicos).font = F_NUM
            ws.cell(fila, 3).alignment = Alignment(horizontal="center")
            ws.cell(fila, 4, v["count"]).font = F_NUM
            ws.cell(fila, 4).alignment = Alignment(horizontal="center")
            c = ws.cell(fila, 5, v["total"]); c.font = F_NUM
            c.number_format = '"$"#,##0.00'; c.alignment = Alignment(horizontal="right")
            for co in (2, 3, 4, 5):
                ws.cell(fila, co).border = BORDE
            totales_cat[cat] += v["total"]
            fila += 1
        # subtotal categoría
        c = ws.cell(fila, 2, f"  Total {cat}"); c.font = F_TOT; c.fill = FILL_TOT
        c = ws.cell(fila, 5, totales_cat[cat]); c.font = F_TOT; c.fill = FILL_TOT
        c.number_format = '"$"#,##0.00'; c.alignment = Alignment(horizontal="right")
        ws.cell(fila, 3).fill = FILL_TOT; ws.cell(fila, 4).fill = FILL_TOT
        for co in (2, 3, 4, 5):
            ws.cell(fila, co).border = BORDE
        fila += 2

    # TOTAL GENERAL
    ws.cell(fila, 2, "TOTAL GENERAL").font = F_TIT
    ws.cell(fila, 2).fill = FILL_TIT
    total_gen = sum(totales_cat.values())
    c = ws.cell(fila, 5, total_gen); c.font = F_TIT; c.fill = FILL_TIT
    c.number_format = '"$"#,##0.00'; c.alignment = Alignment(horizontal="right")
    ws.cell(fila, 3).fill = FILL_TIT; ws.cell(fila, 4).fill = FILL_TIT
    ws.row_dimensions[fila].height = 26
    fila_total = fila
    fila += 2

    # Pie de categorías
    ws.cell(fila, 2, "Categoría").font = F_LBL
    ws.cell(fila, 5, "Total").font = F_LBL
    fila_pie_ini = fila + 1
    for cat in orden_cat:
        if totales_cat[cat] > 0:
            fila += 1
            ws.cell(fila, 2, cat).font = F_NUM
            c = ws.cell(fila, 5, totales_cat[cat]); c.font = F_NUM
            c.number_format = '"$"#,##0.00'; c.alignment = Alignment(horizontal="right")
    fila_pie_fin = fila

    pie = PieChart()
    pie.title = "Distribución de gasto — junio 2026"
    labels = Reference(ws, min_col=2, min_row=fila_pie_ini, max_row=fila_pie_fin)
    data = Reference(ws, min_col=5, min_row=fila_pie_ini, max_row=fila_pie_fin)
    pie.add_data(data, titles_from_data=False)
    pie.set_categories(labels)
    pie.dataLabels = DataLabelList(showPercent=True)
    pie.height = 10; pie.width = 15
    ws.add_chart(pie, "G5")

    # ---- Hoja Detalle ----
    ws2 = wb.create_sheet("Detalle")
    ws2.sheet_view.showGridLines = False
    for i, w in enumerate([3, 12, 32, 15, 20, 12, 14, 14, 3], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w
    ws2.merge_cells("B2:H2")
    c = ws2.cell(2, 2, "DETALLE POR FACTURA · Junio 2026"); c.font = F_TIT; c.fill = FILL_TIT
    c.alignment = Alignment(horizontal="center", vertical="center"); ws2.row_dimensions[2].height = 28

    for i, h in enumerate(["Fecha", "Emisor", "RFC", "Categoría", "Fuente", "Subtotal", "Total"], start=2):
        c = ws2.cell(4, i, h); c.font = F_HDR; c.fill = FILL_HDR; c.border = BORDE
        c.alignment = Alignment(horizontal="center")

    fila = 5
    for h in sorted(TODOS, key=lambda x: (x["categoria"], -x["total"])):
        ws2.cell(fila, 2, (h["fecha"] or "")[:10]).font = F_NUM
        ws2.cell(fila, 3, h["emisor_nombre"][:40]).font = F_NUM
        ws2.cell(fila, 4, h["emisor_rfc"]).font = F_NUM
        ws2.cell(fila, 5, h["subcategoria"]).font = F_NUM
        ws2.cell(fila, 6, h["source"]).font = F_NUM
        if h["subtotal"] is not None:
            c = ws2.cell(fila, 7, h["subtotal"]); c.number_format = '"$"#,##0.00'; c.font = F_NUM
        c = ws2.cell(fila, 8, h["total"]); c.number_format = '"$"#,##0.00'; c.font = F_NUM
        for co in range(2, 9):
            ws2.cell(fila, co).border = BORDE
        fila += 1

    wb.save(OUT_XLSX)
    log(f"Excel: {OUT_XLSX}")


def subir_a_drive():
    log("=== SUBIENDO A DRIVE ===")
    TOK = json.loads((Path.home()/".openclaw/credentials/google/oauth/tito_tokens.json").read_text())
    creds = Credentials(token=TOK["token"], refresh_token=TOK["refresh_token"], token_uri=TOK["token_uri"],
        client_id=TOK["client_id"], client_secret=TOK["client_secret"], scopes=TOK["scopes"])
    if not creds.valid: creds.refresh(Request())
    from googleapiclient.http import MediaFileUpload
    svc = build("drive", "v3", credentials=creds)

    FOLDER = "1RpTEYh-rBrJO0Vd9URLO8xd1GXfyuqO3"  # Indicadores Don Titi
    NAME = "Food cost - Junio 2026"

    q = f"'{FOLDER}' in parents and name = '{NAME}' and trashed=false"
    r = svc.files().list(q=q, fields="files(id)").execute()
    for f in r.get("files", []):
        svc.files().update(fileId=f["id"], body={"trashed": True}).execute()

    media = MediaFileUpload(str(OUT_XLSX),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    metadata = {"name": NAME, "parents": [FOLDER],
                "mimeType": "application/vnd.google-apps.spreadsheet"}
    f = svc.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    log(f"Drive: {f['webViewLink']}")
    return f["webViewLink"]


def notificar_wa(link: str, total: float, n: int):
    top5 = sorted(RESUMEN.items(), key=lambda x: -x[1]["total"])[:5]
    lineas = [f"  ${v['total']:,.0f} — {k.split('·')[1].strip()}" for k, v in top5]
    resumen = "\n".join(lineas)
    msg = f"""Ya está el reporte de food cost + gastos junio 2026.

Total detectado: ${total:,.0f}  ({n} facturas)

Top 5 rubros:
{resumen}

Está en Drive · Indicadores Don Titi como 'Food cost - Junio 2026'."""
    import subprocess
    subprocess.run(["openclaw", "message", "send",
                    "--channel", "whatsapp",
                    "--target", "+5216861445614",
                    "--message", msg], check=False)


def main():
    log("### FOOD COST JUNIO 2026 · arranque ###")
    procesar_yahoo()
    procesar_andronica()
    total = sum(v["total"] for v in RESUMEN.values())
    n = sum(v["count"] for v in RESUMEN.values())
    log(f"TOTAL: ${total:,.2f}  ({n} facturas)")
    if n == 0:
        log("No hay facturas parseadas. Aborto.")
        return
    generar_excel()
    link = subir_a_drive()
    notificar_wa(link, total, n)
    log("### FIN ###")


if __name__ == "__main__":
    main()
