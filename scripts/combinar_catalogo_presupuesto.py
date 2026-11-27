#!/usr/bin/env python3
"""Combina Catálogo de Gastos + Presupuesto Mayo 2026 en un solo Excel.
- Mantiene el Catálogo detallado como hoja principal (los rubros del Presupuesto son sumas
  de los rubros individuales del Catálogo, así que no se duplican).
- Añade las 3 hojas del Presupuesto Mayo (Resumen agregado, Ventas por sucursal, Notas)
  como vistas complementarias.
- Sube a Drive · Titi Burger · Titiburger las originales (nivel raíz).
"""
import json
from pathlib import Path
from datetime import datetime
from copy import copy

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CATALOGO_SRC = Path("/home/tito/.openclaw/data/Catálogo de Gastos - Titi Burger.xlsx")
PRESUPUESTO_SRC = Path("/home/tito/.openclaw/data/Presupuesto Mayo 2026.xlsx")
OUT = Path("/home/tito/.openclaw/workspace/apps_delivery/Catálogo de Gastos - Titi Burger.xlsx")


def copy_cell_style(src_cell, dst_cell):
    if src_cell.has_style:
        dst_cell.font = copy(src_cell.font)
        dst_cell.fill = copy(src_cell.fill)
        dst_cell.border = copy(src_cell.border)
        dst_cell.alignment = copy(src_cell.alignment)
        dst_cell.number_format = src_cell.number_format


def copy_sheet(src_ws, dst_wb, new_title):
    dst_ws = dst_wb.create_sheet(new_title)
    for r in range(1, src_ws.max_row + 1):
        for c in range(1, src_ws.max_column + 1):
            src_cell = src_ws.cell(r, c)
            dst_cell = dst_ws.cell(r, c, src_cell.value)
            copy_cell_style(src_cell, dst_cell)
        if src_ws.row_dimensions[r].height:
            dst_ws.row_dimensions[r].height = src_ws.row_dimensions[r].height
    for col_letter, dim in src_ws.column_dimensions.items():
        if dim.width:
            dst_ws.column_dimensions[col_letter].width = dim.width
    # merges
    for mr in src_ws.merged_cells.ranges:
        dst_ws.merge_cells(str(mr))
    dst_ws.sheet_view.showGridLines = src_ws.sheet_view.showGridLines
    return dst_ws


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # arrancar desde el Catálogo (copia completa)
    cat_wb = load_workbook(CATALOGO_SRC)
    # renombrar hoja principal para claridad
    hoja_cat = cat_wb.active
    hoja_cat.title = "Catálogo detallado"

    # Añadir portada al inicio
    portada = cat_wb.create_sheet("Portada", 0)
    portada.sheet_view.showGridLines = False
    portada.column_dimensions["A"].width = 3
    portada.column_dimensions["B"].width = 90

    F_TIT = Font(name="Calibri", size=18, bold=True, color="FFFFFF")
    F_SUB = Font(name="Calibri", size=13, bold=True, color="1F3864")
    F_TXT = Font(name="Calibri", size=11)
    F_NOTA = Font(name="Calibri", size=10, italic=True, color="595959")
    FILL_TIT = PatternFill("solid", fgColor="1F3864")
    FILL_SUB = PatternFill("solid", fgColor="D9E2F3")
    LEFT = Alignment(horizontal="left", vertical="center", indent=1)
    CENTER = Alignment(horizontal="center", vertical="center")

    portada.merge_cells("B2:B2")
    c = portada.cell(2, 2, "CATÁLOGO DE GASTOS · TITI BURGER"); c.font = F_TIT; c.fill = FILL_TIT; c.alignment = CENTER
    portada.row_dimensions[2].height = 34

    c = portada.cell(4, 2, "Contenido de este Excel")
    c.font = F_SUB; c.fill = FILL_SUB; c.alignment = LEFT
    portada.row_dimensions[4].height = 22

    contenido = [
        "1. Catálogo detallado — todos los rubros individuales con monto, frecuencia, tipo y estado",
        "2. Presupuesto Mayo 2026 — vista agregada (bloques grandes) del mismo dato",
        "3. Ventas Mayo por sucursal — venta real desde Soft Restaurant",
        "4. Notas Mayo — observaciones y pendientes",
    ]
    for i, t in enumerate(contenido):
        c = portada.cell(5 + i, 2, t); c.font = F_TXT; c.alignment = LEFT

    c = portada.cell(11, 2, "Cómo leerlo")
    c.font = F_SUB; c.fill = FILL_SUB; c.alignment = LEFT
    portada.row_dimensions[11].height = 22

    lectura = [
        "• Los rubros del Presupuesto Mayo son SUMAS de los rubros individuales del Catálogo (no duplicados).",
        "• Ejemplo: Presupuesto dice 'Rentas 6 sucursales $348,600' → en Catálogo cada renta está línea por línea.",
        "• Estados: CONFIRMADO = verificado por Don Titi/Nancy. PENDIENTE = falta confirmar.",
        "• Tipos: FIJO = mismo monto/mes · VARIABLE = depende de venta · PERIÓDICO = repite no exacto · EXTRAORDINARIO = ocasional.",
    ]
    for i, t in enumerate(lectura):
        c = portada.cell(12 + i, 2, t); c.font = F_TXT; c.alignment = LEFT

    c = portada.cell(18, 2, f"Consolidado {datetime.now().strftime('%d de %B de %Y')} · Fuentes: Catálogo (10-jul) + Presupuesto Mayo (10-jul)")
    c.font = F_NOTA; c.alignment = LEFT

    # Copiar hojas del Presupuesto
    pres_wb = load_workbook(PRESUPUESTO_SRC)
    for src_title, dst_title in [
        ("Resumen", "Presupuesto Mayo — Resumen"),
        ("Ventas por sucursal", "Ventas Mayo por sucursal"),
        ("Notas", "Notas Mayo"),
    ]:
        if src_title in pres_wb.sheetnames:
            copy_sheet(pres_wb[src_title], cat_wb, dst_title)

    cat_wb.save(OUT)
    print(f"Guardado: {OUT}")
    return OUT


def subir_a_drive(archivo):
    print("=== SUBIENDO A DRIVE ===")
    TOK = json.loads(Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json").read_text())
    creds = Credentials(token=TOK["token"], refresh_token=TOK["refresh_token"], token_uri=TOK["token_uri"],
        client_id=TOK["client_id"], client_secret=TOK["client_secret"], scopes=TOK["scopes"])
    if not creds.valid:
        creds.refresh(Request())
    svc = build("drive", "v3", credentials=creds)

    # Titi Burger · Titiburger las originales (raíz)
    FOLDER = "1Bql9OzXtZ_OBNikYF3KEr0qJUA83f-U2"
    NAME = "Catálogo de Gastos - Titi Burger"

    q = f"'{FOLDER}' in parents and name = '{NAME}' and trashed=false"
    r = svc.files().list(q=q, fields="files(id)").execute()
    for f in r.get("files", []):
        svc.files().update(fileId=f["id"], body={"trashed": True}).execute()
        print(f"  papelera: {f['id']}")

    media = MediaFileUpload(str(archivo),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    meta = {"name": NAME, "parents": [FOLDER],
            "mimeType": "application/vnd.google-apps.spreadsheet"}
    f = svc.files().create(body=meta, media_body=media, fields="id,webViewLink,name").execute()
    print(f"OK Drive: {f['webViewLink']}")
    return f["webViewLink"]


if __name__ == "__main__":
    archivo = main()
    link = subir_a_drive(archivo)
    print(f"\nLINK: {link}")
