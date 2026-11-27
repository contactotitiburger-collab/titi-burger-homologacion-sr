#!/usr/bin/env python3
"""Genera el Excel del presupuesto mayo 2026 y lo sube a Drive."""
import json
import io
from datetime import date
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
OUT_XLSX = Path("/home/tito/.openclaw/data/Presupuesto Mayo 2026.xlsx")
OUT_XLSX.parent.mkdir(parents=True, exist_ok=True)

# ============ GENERAR EXCEL ============
wb = Workbook()

# --- Estilos ---
title_font = Font(name="Arial", size=16, bold=True, color="FFFFFF")
title_fill = PatternFill("solid", fgColor="C0392B")
header_font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="34495E")
subheader_font = Font(name="Arial", size=11, bold=True)
subheader_fill = PatternFill("solid", fgColor="F5CBA7")
total_font = Font(name="Arial", size=12, bold=True)
total_fill_verde = PatternFill("solid", fgColor="A9DFBF")
total_fill_rojo = PatternFill("solid", fgColor="F5B7B1")
thin = Side(border_style="thin", color="BDC3C7")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

def money(cell): cell.number_format = '"$"#,##0.00'
def h1(cell):
    cell.font = title_font; cell.fill = title_fill
    cell.alignment = Alignment(horizontal="center", vertical="center")
def h2(cell):
    cell.font = header_font; cell.fill = header_fill
    cell.alignment = Alignment(horizontal="center")
def cat(cell):
    cell.font = subheader_font; cell.fill = subheader_fill

# ============ HOJA 1: RESUMEN ============
ws = wb.active
ws.title = "Resumen"
ws.column_dimensions["A"].width = 42
ws.column_dimensions["B"].width = 18
ws.column_dimensions["C"].width = 60

ws.merge_cells("A1:C1")
ws["A1"] = "PRESUPUESTO MAYO 2026 — TITI BURGER"
h1(ws["A1"])
ws.row_dimensions[1].height = 28

ws["A3"] = "Fuente venta:"; ws["B3"] = "Soft Restaurant Admin"; ws["C3"] = "consultado 10-jul-2026"
ws["A4"] = "Fuente gasto:"; ws["B4"] = "Cuadro semanal Titi Burger"; ws["C4"] = "fotos 10-jul-2026"
for r in [3, 4]:
    ws.cell(row=r, column=1).font = Font(bold=True)

# INGRESOS
ws["A6"] = "INGRESOS"; h2(ws["A6"]); ws.merge_cells("A6:C6")
ingresos = [
    ("FOVISSTE (L Montejano)", 811648.50, "1,996 tickets promedio $335.52"),
    ("MONTECARLO", 575401.00, "1,706 tickets promedio $336.74"),
    ("SAN MARCOS", 181616.87, "594 tickets promedio $303.13"),
    ("HACIENDA DEL RÍO", 235110.00, "702 tickets promedio $321.41"),
    ("VILLAS DEL REY", 174494.00, "578 tickets promedio $299.90"),
    ("Cine Curto (ESTIMADO — licencia SR vencida)", 175000.00, "sin datos reales; estimado conservador"),
]
for i, (concepto, monto, nota) in enumerate(ingresos, start=7):
    ws.cell(row=i, column=1, value=concepto)
    c = ws.cell(row=i, column=2, value=monto); money(c)
    ws.cell(row=i, column=3, value=nota)

total_ingresos_row = 7 + len(ingresos)
ws.cell(row=total_ingresos_row, column=1, value="TOTAL INGRESOS").font = total_font
c = ws.cell(row=total_ingresos_row, column=2, value=f"=SUM(B7:B{total_ingresos_row-1})"); money(c); c.font = total_font; c.fill = total_fill_verde
ws.cell(row=total_ingresos_row, column=1).fill = total_fill_verde

# EGRESOS
egresos_start = total_ingresos_row + 3
ws.cell(row=egresos_start, column=1, value="EGRESOS"); h2(ws.cell(row=egresos_start, column=1))
ws.merge_cells(f"A{egresos_start}:C{egresos_start}")

egresos = [
    ("Nómina + IMSS + Fonacot + Infonavit", 693900, "sueldos $442k + IMSS/Infonavit $142k + Fonacot $41.9k + IMSS Herrería $22k"),
    ("Rentas 6 sucursales", 348600, "Cine Curto $73k, Hacienda $43k, Montecarlo $43k, San Marcos $47k, Fovissste/Pachelli $38k"),
    ("Retiro personal Don Titi ('Otros $60k/sem')", 259800, "nómina personal — usualmente American Express"),
    ("Proveedores comida", 200000, "Costalonorte $42k/sem, Bimbo, Bona (carne), Islas (pollo), Julián, Kowi, verduras QM, Parra"),
    ("Gasolina", 151500, "$35k/sem — mensajero + rancho (revisar consumo)"),
    ("Andrónica préstamos Santander (mensual)", 137000, "Crédito simple $45k + Cuenta revolvente $92k (revolvente BLOQUEADA por atrasos)"),
    ("Carbón", 58200, "$13.4k/sem"),
    ("Refrescos y bebidas", 56000, "Coca $5.5k + Peñafiel $3.5k + Pepsi $4k + Quevedo $5.5k semanal"),
    ("Fijos: luz + agua + gas", 28900, "CFE $23.5k + CESPM $13.4k /2 + Ecogas $6.9k (bimestrales prorrateados)"),
    ("Abogado Luis", 10800, "$2.5k/sem"),
    ("Mantenimiento varios", 10000, "Casa Acero, Casa Carpintero, MJ Machine, Halcón"),
    ("Sistemas — SR Admin licencias", 5561, "6 sucursales × $926.84 (incluye Cine Curto que no está pagada)"),
    ("Otros personales/varios mezclados", 110000, "Hipoteca Titi, CFE casa, Ecogas casa, Liverpool, Carola, Arándano, botellas, hielos"),
]
for i, (concepto, monto, nota) in enumerate(egresos, start=egresos_start+1):
    ws.cell(row=i, column=1, value=concepto)
    c = ws.cell(row=i, column=2, value=monto); money(c)
    ws.cell(row=i, column=3, value=nota)

total_egresos_row = egresos_start + 1 + len(egresos)
ws.cell(row=total_egresos_row, column=1, value="TOTAL EGRESOS").font = total_font
c = ws.cell(row=total_egresos_row, column=2, value=f"=SUM(B{egresos_start+1}:B{total_egresos_row-1})"); money(c); c.font = total_font; c.fill = total_fill_rojo
ws.cell(row=total_egresos_row, column=1).fill = total_fill_rojo

# BALANCE
balance_row = total_egresos_row + 3
ws.cell(row=balance_row, column=1, value="BALANCE MAYO 2026").font = title_font
ws.cell(row=balance_row, column=1).fill = title_fill
c = ws.cell(row=balance_row, column=2, value=f"=B{total_ingresos_row}-B{total_egresos_row}"); money(c); c.font = title_font; c.fill = title_fill

ws.cell(row=balance_row+1, column=1, value="(negativo = déficit; positivo = utilidad)").font = Font(italic=True, size=10)

# ============ HOJA 2: DETALLE VENTAS ============
ws2 = wb.create_sheet("Ventas por sucursal")
ws2.column_dimensions["A"].width = 25
for c in ["B","C","D","E","F","G"]: ws2.column_dimensions[c].width = 15

ws2.merge_cells("A1:G1")
ws2["A1"] = "VENTAS MAYO 2026 — DESGLOSE POR SUCURSAL"
h1(ws2["A1"])

headers = ["Sucursal", "Tickets", "Ticket prom", "Subtotal", "Descuentos", "Impuestos", "TOTAL"]
for i, hd in enumerate(headers, start=1):
    c = ws2.cell(row=3, column=i, value=hd); h2(c)

data_ventas = json.loads(Path("/home/tito/.openclaw/data/ventas_mayo_2026.json").read_text())
row = 4
for name, r in data_ventas["sucursales"].items():
    ws2.cell(row=row, column=1, value=name)
    if "tickets" in r:
        ws2.cell(row=row, column=2, value=r["tickets"])
        c = ws2.cell(row=row, column=3, value=r["ticket_promedio"]); money(c)
        c = ws2.cell(row=row, column=4, value=r["subtotal"]); money(c)
        c = ws2.cell(row=row, column=5, value=r["descuentos"]); money(c)
        c = ws2.cell(row=row, column=6, value=r["impuestos"]); money(c)
        c = ws2.cell(row=row, column=7, value=r["total"]); money(c); c.font = Font(bold=True)
    else:
        ws2.cell(row=row, column=2, value="🔴 Sin datos — licencia SR vencida")
    row += 1

# Total
c = ws2.cell(row=row, column=1, value="TOTAL 5 SUCURSALES"); c.font = total_font; c.fill = total_fill_verde
c = ws2.cell(row=row, column=2, value=data_ventas["total_tickets"]); c.font = total_font
c = ws2.cell(row=row, column=7, value=data_ventas["total_venta"]); money(c); c.font = total_font; c.fill = total_fill_verde

# ============ HOJA 3: NOTAS ============
ws3 = wb.create_sheet("Notas")
ws3.column_dimensions["A"].width = 110
notas = [
    "PRESUPUESTO MAYO 2026 — NOTAS METODOLÓGICAS",
    "",
    "FUENTE INGRESOS:",
    "• Consulta directa al panel de Soft Restaurant Admin (admin.softrestaurant.com), reporte 'Ventas mensuales' con las 6 sucursales.",
    "• Cine Curto NO reporta al cloud porque la licencia de SR está sin pagar → cifra estimada conservadora de $175,000.",
    "",
    "FUENTE EGRESOS:",
    "• Hoja de gastos semanales de Titi Burger (fotos enviadas por Rafael el 10-jul-2026, 12:57).",
    "• Total semanal ≈ $538,319. Mensualizado ×4.33 semanas/mes.",
    "• Ajuste: Andrónica NO es semanal ($45.5k/sem estimado inicial) — es MENSUAL: crédito simple $45k + revolvente $92k = $137k/mes.",
    "",
    "AJUSTES Y OBSERVACIONES:",
    "1. La cuenta revolvente Santander ($92k/mes) está BLOQUEADA por atrasos — no está disponible como línea de crédito.",
    "2. Gasolina $151k/mes parece alta para 6 sucursales fijas; posible carga del rancho o vehículos personales.",
    "3. Retiro personal de Don Titi $260k/mes se registra como 'Otros gastos' — es la nómina personal, usualmente destinada a AmEx.",
    "4. Rubros mezclados personal/negocio: Hipoteca Titi, CFE casa Titi, Liverpool Titi, Carola, Arándano.",
    "5. IMSS/Infonavit: 2 registros patronales — TALLER DE HERRERIA (3 cotizantes, $22k/mes) + LONCHERIA TAQUERIA (25 cotizantes, $120k/mes).",
    "",
    "PENDIENTES DE INCORPORAR:",
    "• Comisiones reales de Uber Eats / Rappi / DiDi Food (requiere acceso a los portales de cada app o a las liquidaciones).",
    "• Confirmar venta real de Cine Curto (reactivar licencia SR permitiría verlo).",
    "• Monto exacto de mesada Don Titi (¿es igual a los $60k 'Otros' o es adicional?).",
    "• Aguinaldo/vacaciones/bonos anuales fuera de la nómina semanal.",
]
for i, txt in enumerate(notas, start=1):
    c = ws3.cell(row=i, column=1, value=txt)
    if i == 1: c.font = Font(bold=True, size=14, color="C0392B")
    elif txt.endswith(":"): c.font = Font(bold=True, size=11)

wb.save(OUT_XLSX)
print(f"Excel guardado: {OUT_XLSX}", flush=True)

# ============ SUBIR A DRIVE ============
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)

TITI_BURGER_FOLDER = "1IA2SK-S0LsCnUvO-ubDQBce0zyPCS9sJ"

def find_or_create_folder(name, parent):
    r = d.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{name}' and '{parent}' in parents and trashed=false",
        fields="files(id,name)", pageSize=5,
    ).execute()
    if r.get("files"):
        return r["files"][0]["id"]
    folder = d.files().create(body={
        "name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent],
    }, fields="id").execute()
    print(f"Creada carpeta: {name}  id={folder['id']}", flush=True)
    return folder["id"]

# Estructura: Titi Burger / Titi Burger - Presupuesto / 2026
presupuesto_id = find_or_create_folder("Titi Burger - Presupuesto", TITI_BURGER_FOLDER)
anio_id = find_or_create_folder("2026", presupuesto_id)

# Subir como Google Sheets
file_name = "Presupuesto Mayo 2026"
media = MediaFileUpload(str(OUT_XLSX),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)
# Ver si ya existe
existing = d.files().list(
    q=f"name='{file_name}' and '{anio_id}' in parents and trashed=false",
    fields="files(id)"
).execute().get("files", [])
if existing:
    file_id = existing[0]["id"]
    d.files().update(fileId=file_id, media_body=media).execute()
    print(f"Actualizado: {file_name} (id={file_id})", flush=True)
else:
    file_meta = {
        "name": file_name, "parents": [anio_id],
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }
    f = d.files().create(body=file_meta, media_body=media, fields="id,webViewLink").execute()
    print(f"Subido: {file_name}", flush=True)
    print(f"Link: {f.get('webViewLink')}", flush=True)
