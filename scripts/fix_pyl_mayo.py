#!/usr/bin/env python3
"""Arregla el Excel: renombra 'P&L' a 'Ganancias y Gastos', amplía columnas, actualiza en Drive."""
import json
from pathlib import Path
from openpyxl import load_workbook
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
IN_XLSX = Path("/home/tito/.openclaw/data/P&L por Sucursal Mayo 2026.xlsx")
OUT_XLSX = Path("/home/tito/.openclaw/data/Ganancias y Gastos por Sucursal Mayo 2026.xlsx")

wb = load_workbook(IN_XLSX)

# 1. Renombrar hoja
if "P&L por Sucursal" in wb.sheetnames:
    wb["P&L por Sucursal"].title = "Ganancias y Gastos"

# 2. Ampliar columnas — de 17 a 22 para que quepan los nombres largos
ws = wb["Ganancias y Gastos"]
ws.column_dimensions["A"].width = 46
for col_letter in ["B","C","D","E","F","G","H"]:
    ws.column_dimensions[col_letter].width = 22

# 3. Cambiar título A1
ws["A1"] = "GANANCIAS Y GASTOS POR PUNTO DE VENTA — MAYO 2026"

# Guardar como nuevo archivo
wb.save(OUT_XLSX)
print(f"Guardado: {OUT_XLSX}", flush=True)

# ============ ACTUALIZAR EN DRIVE ============
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)

# 1. Borrar el archivo viejo "P&L por Sucursal Mayo 2026" (id conocido)
OLD_FILE_ID = "1ZN0SDxHAIwsYvByYJdIS3bijb1vkZcgvSQcoJ5GTHyE"
try:
    d.files().delete(fileId=OLD_FILE_ID).execute()
    print(f"Borrado archivo viejo: P&L por Sucursal Mayo 2026", flush=True)
except Exception as e:
    print(f"  (no se pudo borrar viejo: {e})", flush=True)

# 2. Renombrar la carpeta "Titi Burger - Análisis por Sucursal" a algo más simple
# En español simple: "Titi Burger - Ganancias y Gastos"
CARPETA_ID = "1HQgpreQsh9S39_7sNsPxbwzVyD21gSAm"
d.files().update(fileId=CARPETA_ID, body={"name": "Titi Burger - Ganancias y Gastos"}).execute()
print("Carpeta renombrada a: Titi Burger - Ganancias y Gastos", flush=True)

# 3. Subir el nuevo archivo con nombre simple
ANIO_ID = "1vxALi3RxnX-2ApJAVdqUhdmvmdfJimtF"
file_name = "Ganancias y Gastos por Sucursal Mayo 2026"
media = MediaFileUpload(str(OUT_XLSX),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)
f = d.files().create(body={
    "name": file_name, "parents": [ANIO_ID],
    "mimeType": "application/vnd.google-apps.spreadsheet",
}, media_body=media, fields="id,webViewLink").execute()
print(f"Subido nuevo: {file_name}", flush=True)
print(f"Link: {f.get('webViewLink')}", flush=True)
print(f"ID: {f.get('id')}", flush=True)
