#!/usr/bin/env python3
"""Reporte junio 2026 · SOLO DATOS COMPROBABLES

Rafael pidió (16-jul-2026):
- Ventas Soft Restaurant (panel oficial)
- Facturas CFDI (Yahoo + Gmail Andrónica)
- Método Meza / Excel Elías (30% Uber, 20% DiDi, 27% Rappi + IVA + retenciones PF)

EXCLUIDO: cualquier dato que solo diga Nancy verbalmente (nómina reportada,
préstamos Andrónica, retiro Don Titi al Amex, rentas no facturadas).

Salida:
- ~/.openclaw/workspace/apps_delivery/Reporte junio 2026 comprobable.xlsx
- Sube a Drive · Indicadores Don Titi
- WhatsApp a Rafael con resumen y link
"""
import base64
import email
import imaplib
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime
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
from googleapiclient.http import MediaFileUpload

# ---- Config ----
DATA = Path.home() / ".openclaw/data"
OUT_XML = Path.home() / ".openclaw/data/facturas_junio_2026"
OUT_XML.mkdir(parents=True, exist_ok=True)
OUT_XLSX = Path.home() / ".openclaw/workspace/apps_delivery/Reporte junio 2026 comprobable.xlsx"
LOG = Path.home() / ".openclaw/logs/reporte_junio.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

CATEGORIAS = [
    ("FOOD_COST", "Carne — Bona / Distribuidoras",   ["bona", "gargu", "garcia guillen", "mayorista"]),
    ("FOOD_COST", "Carne — Otros carniceros",        ["julian", "carniceria", "casa carp", "campos herrera", "cahr530914"]),
    ("FOOD_COST", "Tocino — Kowi",                   ["kowi", "kochi", "yuexian"]),
    ("FOOD_COST", "Pollo",                           ["islas", "avicola", "pollo"]),
    ("FOOD_COST", "Supermercado Smart & Final",      ["smart"]),
    ("FOOD_COST", "Punto de Venta Gran Vía",         ["puntodeventagranvia", "gran via"]),
    ("FOOD_COST", "Bebidas / refrescos",             ["coca-cola", "coca cola", "cocacola", "pepsi", "arca continental"]),
    ("FOOD_COST", "Otros insumos",                   ["carboneria", "pueblo viejo", "expresion", "empaque", "desechable"]),

    ("SERVICIOS", "Gas Ecogas",                      ["ecogas", "sempraglobal"]),
    ("SERVICIOS", "Luz CFE",                         ["cfe", "comision federal"]),
    ("SERVICIOS", "Agua Mexicali (CESPM)",           ["cespm", "comision estatal de servicios"]),
    ("SERVICIOS", "Internet / teléfono",             ["telnor", "telcel", "att-mail", "att.com.mx"]),

    ("GASOLINA", "El Rey",                           ["el rey", "elrey", "combustibles el rey"]),
    ("GASOLINA", "Petro Seven",                      ["petro seven", "petro-7"]),
    ("GASOLINA", "Otras gasolineras",                ["gasolinera"]),

    ("HONORARIOS_ADMIN", "Contable / abogado",       ["decono", "facturama", "gruposago", "capacitacion", "contalink"]),

    ("RENTAS_FACTURADAS", "Rentas (con CFDI)",       ["paccelli", "institucion", "arrendamiento"]),
    ("OTROS", "Sin clasificar",                      []),
]

RESUMEN = defaultdict(lambda: {"count": 0, "total": 0.0, "detalles": []})
TODOS_XML = []


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def clasificar(emisor: str, from_email: str = "") -> tuple[str, str]:
    texto = (emisor + " " + from_email).lower()
    for cat, sub, patrones in CATEGORIAS:
        if patrones and any(p in texto for p in patrones):
            return cat, sub
    return "OTROS", "Sin clasificar"


def parse_cfdi(xml_bytes: bytes, source: str, from_email: str) -> dict | None:
    try:
        text = xml_bytes.decode("utf-8", errors="ignore").lstrip("﻿")
        root = ET.fromstring(text)
    except Exception:
        return None

    total = root.get("Total") or root.get("total")
    subtotal = root.get("SubTotal") or root.get("subtotal")
    fecha = root.get("Fecha") or root.get("fecha")
    tipo = (root.get("TipoDeComprobante") or root.get("tipoDeComprobante") or "").upper()
    if not total:
        return None
    try:
        total = float(total)
    except:
        return None
    if tipo and tipo not in ("I", "INGRESO"):
        return None
    emisor_nombre = emisor_rfc = ""
    for child in root:
        low = child.tag.lower()
        if low.endswith("emisor"):
            emisor_nombre = child.get("Nombre") or child.get("nombre") or ""
            emisor_rfc = child.get("Rfc") or child.get("rfc") or ""
    cat, sub = clasificar(emisor_nombre, from_email)
    return {
        "source": source,
        "fecha": (fecha or "")[:10],
        "total": total,
        "subtotal": float(subtotal) if subtotal else None,
        "emisor_nombre": emisor_nombre,
        "emisor_rfc": emisor_rfc,
        "from_email": from_email,
        "categoria": cat,
        "subcategoria": sub,
    }


def guardar(h):
    RESUMEN[(h["categoria"], h["subcategoria"])]["count"] += 1
    RESUMEN[(h["categoria"], h["subcategoria"])]["total"] += h["total"]
    RESUMEN[(h["categoria"], h["subcategoria"])]["detalles"].append(h)
    TODOS_XML.append(h)


# ==========================================================
def procesar_yahoo():
    log("=== YAHOO ===")
    creds = json.loads((Path.home()/".openclaw/credentials/yahoo/creds.json").read_text())
    M = imaplib.IMAP4_SSL(creds.get("imap_host") or "imap.mail.yahoo.com")
    M.login(creds.get("user") or creds.get("email"), creds.get("app_password") or creds.get("password"))
    typ, folders = M.list()
    carpetas = [f.decode().split(' "/" ')[-1].strip().strip('"') for f in folders]
    proc = 0
    for carp in carpetas:
        try:
            M.select(f'"{carp}"', readonly=True)
            typ, data = M.search(None, 'SINCE 01-Jun-2026 BEFORE 01-Jul-2026')
            ids = data[0].split() if data and data[0] else []
            for uid in ids:
                try:
                    typ, d = M.fetch(uid, "(BODY.PEEK[])")
                    if not d or not d[0]: continue
                    msg = email.message_from_bytes(d[0][1], policy=policy.default)
                    from_email = msg.get("From", "").lower()
                    for part in msg.walk():
                        fname = part.get_filename() or ""
                        try:
                            fname = "".join(t.decode(e or "utf-8", errors="ignore") if isinstance(t, bytes) else t
                                            for t, e in decode_header(fname))
                        except: pass
                        if not fname.lower().endswith(".xml"): continue
                        contenido = part.get_payload(decode=True)
                        if not contenido: continue
                        safe = re.sub(r"[^\w.-]", "_", fname)[:60]
                        (OUT_XML / f"yahoo__{uid.decode()}__{safe}").write_bytes(contenido)
                        h = parse_cfdi(contenido, "Yahoo", from_email)
                        if h:
                            guardar(h); proc += 1
                except Exception:
                    continue
        except Exception as e:
            log(f"[Yahoo:{carp}] ERROR: {e}")
    M.logout()
    log(f"Yahoo: {proc} facturas CFDI parseadas")


def procesar_andronica():
    log("=== GMAIL ANDRÓNICA ===")
    TOK = json.loads((Path.home()/".openclaw/credentials/google/oauth/andronica_tokens.json").read_text())
    creds = Credentials(token=TOK["token"], refresh_token=TOK["refresh_token"], token_uri=TOK["token_uri"],
        client_id=TOK["client_id"], client_secret=TOK["client_secret"], scopes=TOK["scopes"])
    if not creds.valid: creds.refresh(Request())
    svc = build("gmail","v1", credentials=creds)

    query = "after:2026/06/01 before:2026/07/01"
    ids = []; token = None
    while True:
        r = svc.users().messages().list(userId="me", q=query, maxResults=500, pageToken=token).execute()
        ids.extend(m["id"] for m in r.get("messages", []))
        token = r.get("nextPageToken")
        if not token: break
    log(f"Gmail Andrónica: revisando {len(ids)} correos de junio")

    proc = 0
    for i, mid in enumerate(ids):
        try:
            msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            from_email = headers.get("from", "").lower()

            def walk(part):
                nonlocal proc
                if part.get("filename", "").lower().endswith(".xml"):
                    body = part.get("body", {})
                    att_id = body.get("attachmentId")
                    if att_id:
                        att = svc.users().messages().attachments().get(
                            userId="me", messageId=mid, id=att_id).execute()
                        data = att.get("data", "")
                        if data:
                            try:
                                contenido = base64.urlsafe_b64decode(data)
                                safe = re.sub(r"[^\w.-]", "_", part["filename"])[:60]
                                (OUT_XML / f"gmail__{mid}__{safe}").write_bytes(contenido)
                                h = parse_cfdi(contenido, "Gmail-Andronica", from_email)
                                if h:
                                    guardar(h); proc += 1
                            except: pass
                for sp in part.get("parts", []):
                    walk(sp)

            walk(msg.get("payload", {}))
            if (i+1) % 50 == 0:
                log(f"  Gmail: {i+1}/{len(ids)}  (CFDI parseados: {proc})")
        except Exception:
            continue
    log(f"Gmail Andrónica: {proc} facturas CFDI parseadas")


# ==========================================================
def generar_excel():
    log("=== GENERANDO EXCEL ===")

    # Datos SR y apps junio 2026 (comprobables)
    ventas12 = json.loads((DATA / "ventas_12m_por_sucursal.json").read_text())["meses"]
    didi_jun = json.loads((DATA / "didi_junio_2026.json").read_text())
    ventas_jun = ventas12["2026-06"]
    SUCURSALES = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
    DIDI_MAP = {"FOVISSTE": "L Montejano", "MONTECARLO": "Montecarlo",
                "SAN MARCOS": "San Marcos", "HACIENDA DEL RÍO": "Hda del Río",
                "CURTO": "Curto", "VILLAS DEL REY": "Villas del Rey"}

    # Método Meza PF
    def neto_pf(bruto, comision_pct):
        com = bruto * comision_pct
        iva_com = com * 0.16
        iva_ret = bruto * 0.08
        isr_ret = bruto * 0.025
        return {"bruto": bruto, "comision": com, "iva_com": iva_com,
                "iva_ret": iva_ret, "isr_ret": isr_ret,
                "total_dedu": com + iva_com + iva_ret + isr_ret,
                "neto": bruto - com - iva_com - iva_ret - isr_ret}

    wb = Workbook()

    # ---- Estilos ----
    F_TIT = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    F_SUB = Font(name="Calibri", size=12, bold=True, color="1F3864")
    F_HDR = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    F_LBL = Font(name="Calibri", size=10, bold=True, color="1F3864")
    F_NUM = Font(name="Calibri", size=10)
    F_TOT = Font(name="Calibri", size=11, bold=True)
    F_KPI_V = Font(name="Calibri", size=18, bold=True, color="1F3864")
    F_KPI_L = Font(name="Calibri", size=10, bold=True, color="595959")
    F_NEG = Font(name="Calibri", size=18, bold=True, color="C00000")
    FILL_TIT = PatternFill("solid", fgColor="1F3864")
    FILL_HDR = PatternFill("solid", fgColor="2E5C99")
    FILL_LBL = PatternFill("solid", fgColor="D9E2F3")
    FILL_TOT = PatternFill("solid", fgColor="FFE699")
    FILL_KPI = PatternFill("solid", fgColor="E7E6E6")
    FILL_OK  = PatternFill("solid", fgColor="C6EFCE")
    FILL_ROJO= PatternFill("solid", fgColor="FFC7CE")
    B_LADO = Side(style="thin", color="BFBFBF")
    BORDE = Border(left=B_LADO, right=B_LADO, top=B_LADO, bottom=B_LADO)
    RIGHT = Alignment(horizontal="right")
    CENTER = Alignment(horizontal="center", vertical="center")

    def moneda(cell): cell.number_format = '"$"#,##0.00'; cell.alignment = RIGHT

    # =========== HOJA DASHBOARD ===========
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_view.showGridLines = False
    for i, w in enumerate([3, 24, 16, 16, 16, 16, 16, 3], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.merge_cells("B2:G2")
    c = ws.cell(2, 2, "TITI BURGER · Reporte Junio 2026 · Solo datos comprobables")
    c.font = F_TIT; c.fill = FILL_TIT; c.alignment = CENTER; ws.row_dimensions[2].height = 32

    ws.merge_cells("B3:G3")
    c = ws.cell(3, 2, f"Fuentes: Soft Restaurant panel · Portales apps · CFDIs Yahoo+Gmail Andrónica  ·  {datetime.now().strftime('%d-%b-%Y %H:%M')}")
    c.font = Font(name="Calibri", size=10, italic=True, color="595959"); c.alignment = CENTER

    # KPIs
    venta_sr = sum(v.get("subtotal", 0) for v in ventas_jun.values() if isinstance(v, dict))
    didi_bruto = didi_jun["total_bruto"]
    didi_meza = neto_pf(didi_bruto, 0.20)
    gastos_cfdi = sum(v["total"] for v in RESUMEN.values())
    ingresos = venta_sr + didi_meza["neto"]  # solo comprobables
    utilidad_visible = ingresos - gastos_cfdi

    def kpi(ws, r, c, label, val, neg=False):
        ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c+1)
        ws.merge_cells(start_row=r+1, start_column=c, end_row=r+1, end_column=c+1)
        l = ws.cell(r, c, label); l.font = F_KPI_L; l.fill = FILL_KPI; l.alignment = CENTER
        v = ws.cell(r+1, c, val); v.font = F_NEG if neg else F_KPI_V
        v.fill = FILL_KPI; v.alignment = CENTER; v.number_format = '"$"#,##0'
        ws.row_dimensions[r].height = 20; ws.row_dimensions[r+1].height = 32

    kpi(ws, 5, 2, "Venta SR (subtotal)", venta_sr)
    kpi(ws, 5, 4, "Neto apps (DiDi PF)", didi_meza["neto"])
    kpi(ws, 5, 6, "Gastos con CFDI",     gastos_cfdi)

    kpi(ws, 8, 2, "Ingreso comprobable", ingresos)
    kpi(ws, 8, 4, "Gasto comprobable",   gastos_cfdi)
    kpi(ws, 8, 6, "Diferencia visible",  utilidad_visible, neg=(utilidad_visible < 0))

    # Nota
    ws.merge_cells("B11:G11")
    c = ws.cell(11, 2, "Este 'diferencia visible' NO es la utilidad real — faltan por sumar nómina, préstamos, "
                        "rentas no facturadas y retiros personales. Aquí solo entra lo que tiene comprobante fiscal o portal oficial.")
    c.font = Font(name="Calibri", size=9, italic=True, color="595959"); c.alignment = Alignment(wrap_text=True)
    ws.row_dimensions[11].height = 32

    # ---- Ventas SR por sucursal ----
    ws.merge_cells("B13:G13")
    c = ws.cell(13, 2, "1. VENTAS SOFT RESTAURANT — Junio 2026"); c.font = F_SUB; c.fill = FILL_LBL
    c.alignment = Alignment(horizontal="left", indent=1); ws.row_dimensions[13].height = 22

    for i, h in enumerate(["Sucursal", "Tickets", "Subtotal", "Descuentos", "Impuestos", "Total"], start=2):
        cell = ws.cell(14, i, h); cell.font = F_HDR; cell.fill = FILL_HDR; cell.border = BORDE; cell.alignment = CENTER
    fila = 15; fila_ini_sr = fila
    for suc in SUCURSALES:
        v = ventas_jun.get(suc, {})
        ws.cell(fila, 2, suc).font = F_LBL
        ws.cell(fila, 3, v.get("tickets", 0)).alignment = CENTER
        for i, k in enumerate(["subtotal", "descuentos", "impuestos", "total_venta"], start=4):
            c = ws.cell(fila, i, v.get(k, 0)); moneda(c)
        for co in range(2, 8): ws.cell(fila, co).border = BORDE
        fila += 1
    c = ws.cell(fila, 2, "TOTAL"); c.font = F_TOT; c.fill = FILL_TOT
    ws.cell(fila, 3, f"=SUM(C{fila_ini_sr}:C{fila-1})").alignment = CENTER; ws.cell(fila, 3).font = F_TOT; ws.cell(fila, 3).fill = FILL_TOT
    for i in range(4, 8):
        col = get_column_letter(i)
        c = ws.cell(fila, i, f"=SUM({col}{fila_ini_sr}:{col}{fila-1})"); moneda(c); c.font = F_TOT; c.fill = FILL_TOT
    for co in range(2, 8): ws.cell(fila, co).border = BORDE
    fila += 2

    # ---- Método Meza aplicado a apps ----
    ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=7)
    c = ws.cell(fila, 2, "2. MÉTODO MEZA (Excel Elías) — Apps de junio"); c.font = F_SUB; c.fill = FILL_LBL
    c.alignment = Alignment(horizontal="left", indent=1); ws.row_dimensions[fila].height = 22
    fila += 1
    for i, h in enumerate(["App", "Bruto", "% Comisión", "IVA + Retenciones", "Neto PF (real)"], start=2):
        cell = ws.cell(fila, i, h); cell.font = F_HDR; cell.fill = FILL_HDR; cell.border = BORDE; cell.alignment = CENTER
    fila += 1
    for app_name, bruto, pct in [("DiDi", didi_bruto, 0.20), ("Uber", None, 0.30), ("Rappi", None, 0.27)]:
        if bruto:
            m = neto_pf(bruto, pct)
            ws.cell(fila, 2, app_name).font = F_LBL
            moneda(ws.cell(fila, 3, m["bruto"]))
            c = ws.cell(fila, 4, pct); c.number_format = "0.0%"; c.alignment = RIGHT
            moneda(ws.cell(fila, 5, m["total_dedu"]))
            c = ws.cell(fila, 6, m["neto"]); moneda(c); c.font = F_TOT; c.fill = FILL_OK
        else:
            ws.cell(fila, 2, app_name).font = F_LBL
            c = ws.cell(fila, 3, "Bruto pendiente"); c.font = Font(name="Calibri", size=9, italic=True, color="C00000")
            c = ws.cell(fila, 4, pct); c.number_format = "0.0%"; c.alignment = RIGHT
            ws.cell(fila, 5, "—").alignment = CENTER
            ws.cell(fila, 6, "—").alignment = CENTER
        for co in range(2, 7): ws.cell(fila, co).border = BORDE
        fila += 1

    fila += 1

    # ---- Gastos con CFDI (resumen) ----
    ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=7)
    c = ws.cell(fila, 2, "3. GASTOS CON CFDI — Facturas junio (Yahoo + Gmail Andrónica)")
    c.font = F_SUB; c.fill = FILL_LBL
    c.alignment = Alignment(horizontal="left", indent=1); ws.row_dimensions[fila].height = 22
    fila += 1
    for i, h in enumerate(["Categoría · Subcategoría", "# Facturas", "# Emisores", "Total"], start=2):
        cell = ws.cell(fila, i, h); cell.font = F_HDR; cell.fill = FILL_HDR; cell.border = BORDE; cell.alignment = CENTER
    fila += 1
    orden = ["FOOD_COST", "SERVICIOS", "GASOLINA", "HONORARIOS_ADMIN", "RENTAS_FACTURADAS", "OTROS"]
    totales_cat = defaultdict(float)
    for cat in orden:
        rows = sorted([(k, v) for k, v in RESUMEN.items() if k[0] == cat], key=lambda x: -x[1]["total"])
        if not rows: continue
        for k, v in rows:
            ws.cell(fila, 2, f"  {k[0]}  ·  {k[1]}").font = F_NUM
            ws.cell(fila, 3, v["count"]).alignment = CENTER
            ws.cell(fila, 4, len(set(d["emisor_nombre"] for d in v["detalles"]))).alignment = CENTER
            c = ws.cell(fila, 5, v["total"]); moneda(c)
            for co in range(2, 6): ws.cell(fila, co).border = BORDE
            totales_cat[cat] += v["total"]
            fila += 1
        # subtotal categoría
        c = ws.cell(fila, 2, f"  Subtotal {cat}"); c.font = F_TOT; c.fill = FILL_TOT
        ws.cell(fila, 3).fill = FILL_TOT; ws.cell(fila, 4).fill = FILL_TOT
        c = ws.cell(fila, 5, totales_cat[cat]); moneda(c); c.font = F_TOT; c.fill = FILL_TOT
        for co in range(2, 6): ws.cell(fila, co).border = BORDE
        fila += 1

    # TOTAL GENERAL CFDIs
    c = ws.cell(fila, 2, "TOTAL GASTOS COMPROBADOS"); c.font = F_TIT; c.fill = FILL_TIT
    for co in range(3, 5): ws.cell(fila, co).fill = FILL_TIT
    c = ws.cell(fila, 5, sum(totales_cat.values())); moneda(c); c.font = F_TIT; c.fill = FILL_TIT
    ws.row_dimensions[fila].height = 26
    fila += 2

    # =========== HOJA: DETALLE FACTURAS ===========
    ws2 = wb.create_sheet("Detalle facturas")
    ws2.sheet_view.showGridLines = False
    for i, w in enumerate([3, 12, 38, 15, 25, 15, 14, 14, 32, 3], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w
    ws2.merge_cells("B2:I2")
    c = ws2.cell(2, 2, f"DETALLE POR FACTURA CFDI · Junio 2026 · {len(TODOS_XML)} facturas")
    c.font = F_TIT; c.fill = FILL_TIT; c.alignment = CENTER; ws2.row_dimensions[2].height = 28

    for i, h in enumerate(["Fecha", "Emisor", "RFC emisor", "Categoría · Sub", "Fuente", "Subtotal", "Total", "Correo origen"], start=2):
        c = ws2.cell(4, i, h); c.font = F_HDR; c.fill = FILL_HDR; c.border = BORDE; c.alignment = CENTER
    fila = 5
    for h in sorted(TODOS_XML, key=lambda x: (x["categoria"], x["fecha"], -x["total"])):
        ws2.cell(fila, 2, h["fecha"]).font = F_NUM
        ws2.cell(fila, 3, h["emisor_nombre"][:60]).font = F_NUM
        ws2.cell(fila, 4, h["emisor_rfc"]).font = F_NUM
        ws2.cell(fila, 5, f"{h['categoria']} · {h['subcategoria']}").font = F_NUM
        ws2.cell(fila, 6, h["source"]).font = F_NUM
        if h["subtotal"] is not None:
            c = ws2.cell(fila, 7, h["subtotal"]); moneda(c)
        c = ws2.cell(fila, 8, h["total"]); moneda(c)
        ws2.cell(fila, 9, h["from_email"][:40]).font = F_NUM
        for co in range(2, 10): ws2.cell(fila, co).border = BORDE
        fila += 1

    # =========== HOJA: EMISORES ===========
    ws3 = wb.create_sheet("Emisores")
    ws3.sheet_view.showGridLines = False
    for i, w in enumerate([3, 38, 15, 12, 14, 3], start=1):
        ws3.column_dimensions[get_column_letter(i)].width = w
    ws3.merge_cells("B2:E2")
    c = ws3.cell(2, 2, "GASTO POR EMISOR · Junio 2026"); c.font = F_TIT; c.fill = FILL_TIT
    c.alignment = CENTER; ws3.row_dimensions[2].height = 28

    for i, h in enumerate(["Emisor", "RFC", "# Facturas", "Total"], start=2):
        c = ws3.cell(4, i, h); c.font = F_HDR; c.fill = FILL_HDR; c.border = BORDE; c.alignment = CENTER

    # agrupar por emisor
    por_emisor = defaultdict(lambda: {"count": 0, "total": 0.0, "rfc": ""})
    for h in TODOS_XML:
        key = h["emisor_nombre"]
        por_emisor[key]["count"] += 1
        por_emisor[key]["total"] += h["total"]
        por_emisor[key]["rfc"] = h["emisor_rfc"]

    fila = 5
    for emisor, v in sorted(por_emisor.items(), key=lambda x: -x[1]["total"]):
        ws3.cell(fila, 2, emisor[:60]).font = F_NUM
        ws3.cell(fila, 3, v["rfc"]).font = F_NUM
        ws3.cell(fila, 4, v["count"]).alignment = CENTER
        c = ws3.cell(fila, 5, v["total"]); moneda(c)
        for co in range(2, 6): ws3.cell(fila, co).border = BORDE
        fila += 1

    wb.save(OUT_XLSX)
    log(f"Excel guardado: {OUT_XLSX}")
    return sum(totales_cat.values()), venta_sr, didi_meza["neto"]


def subir_a_drive():
    log("=== SUBIENDO A DRIVE ===")
    TOK = json.loads((Path.home()/".openclaw/credentials/google/oauth/tito_tokens.json").read_text())
    creds = Credentials(token=TOK["token"], refresh_token=TOK["refresh_token"], token_uri=TOK["token_uri"],
        client_id=TOK["client_id"], client_secret=TOK["client_secret"], scopes=TOK["scopes"])
    if not creds.valid: creds.refresh(Request())
    svc = build("drive", "v3", credentials=creds)
    FOLDER = "1RpTEYh-rBrJO0Vd9URLO8xd1GXfyuqO3"
    NAME = "Reporte junio 2026 (solo comprobables)"
    q = f"'{FOLDER}' in parents and name = '{NAME}' and trashed=false"
    r = svc.files().list(q=q, fields="files(id)").execute()
    for f in r.get("files", []):
        svc.files().update(fileId=f["id"], body={"trashed": True}).execute()
    media = MediaFileUpload(str(OUT_XLSX),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    metadata = {"name": NAME, "parents": [FOLDER],
                "mimeType": "application/vnd.google-apps.spreadsheet"}
    f = svc.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    log(f"Drive link: {f['webViewLink']}")
    return f["webViewLink"]


def notificar_wa(link, gastos_cfdi, venta_sr, neto_didi):
    top = sorted(RESUMEN.items(), key=lambda x: -x[1]["total"])[:5]
    top_lineas = "\n".join(f"  ${v['total']:>10,.0f}  {k[1]}" for k, v in top)
    utilidad = (venta_sr + neto_didi) - gastos_cfdi
    msg = f"""🍔 Reporte junio 2026 (solo comprobables) LISTO.

INGRESOS
  Venta SR: ${venta_sr:,.0f}
  Neto DiDi (Meza PF): ${neto_didi:,.0f}
  Uber + Rappi: pendiente bruto
GASTOS con CFDI: ${gastos_cfdi:,.0f}  ({len(TODOS_XML)} facturas)

DIFERENCIA visible: ${utilidad:,.0f}
(no incluye nómina, préstamos, rentas sin CFDI, ni retiro Amex)

Top 5 rubros:
{top_lineas}

Drive → Indicadores Don Titi:
{link}"""
    subprocess.run(["openclaw", "message", "send",
                    "--channel", "whatsapp",
                    "--target", "+5216861445614",
                    "--message", msg], check=False)
    log("WA enviado a Rafael")


def main():
    log("### REPORTE JUNIO 2026 · SOLO COMPROBABLES ###")
    procesar_yahoo()
    procesar_andronica()
    if not TODOS_XML:
        log("Sin CFDIs. Aborto.")
        return
    log(f"Total CFDIs: {len(TODOS_XML)}")
    gastos, venta_sr, neto_didi = generar_excel()
    link = subir_a_drive()
    notificar_wa(link, gastos, venta_sr, neto_didi)
    log("### FIN ###")


if __name__ == "__main__":
    main()
