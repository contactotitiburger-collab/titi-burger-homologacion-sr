#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera plantilla de Control de Pagos para Titi Burger (Excel con formulas)."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

# --- Paleta Titi Burger (misma que Orden de Compra) ---
ROJO   = "C1272D"
CARBON = "2B2B2B"
CREMA  = "FFF7EC"
AMBAR  = "F2A900"
GRIS   = "8A8A8A"
VERDE  = "2E7D32"

def fill(c): return PatternFill("solid", fgColor=c)
thin = Side(style="thin", color="D9D9D9")
box_thin = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Control de Pagos"
ws.sheet_view.showGridLines = False

# Columnas: A#  B Fecha  C Concepto  D Sucursal  E Monto  F Forma  G Estatus  H Notas
anchos = {"A": 5, "B": 12, "C": 30, "D": 15, "E": 14, "F": 15, "G": 13, "H": 26}
for col, w in anchos.items():
    ws.column_dimensions[col].width = w

# ---------- ENCABEZADO ----------
ws.merge_cells("A1:H2")
h = ws["A1"]
h.value = "TITI BURGER  🍔"
h.font = Font(name="Arial Black", size=22, bold=True, color="FFFFFF")
h.alignment = Alignment(horizontal="left", vertical="center", indent=1)
for r in (1, 2):
    for c in range(1, 9):
        ws.cell(row=r, column=c).fill = fill(ROJO)
ws.row_dimensions[1].height = 26
ws.row_dimensions[2].height = 26

ws.merge_cells("A3:F3")
sub = ws["A3"]
sub.value = "CONTROL DE PAGOS"
sub.font = Font(name="Arial", size=13, bold=True, color=CARBON)
sub.alignment = Alignment(horizontal="left", vertical="center", indent=1)
sub.fill = fill(AMBAR)
ws.merge_cells("G3:H3")
sem = ws["G3"]
sem.value = "Semana:"
sem.font = Font(name="Arial", size=11, bold=True, color=CARBON)
sem.alignment = Alignment(horizontal="right", vertical="center", indent=1)
sem.fill = fill(AMBAR)
ws.row_dimensions[3].height = 22

# ---------- CABECERA DE TABLA ----------
HEAD = 5
headers = ["#", "FECHA", "CONCEPTO", "SUCURSAL", "MONTO", "FORMA DE PAGO", "ESTATUS", "NOTAS"]
for i, txt in enumerate(headers, start=1):
    c = ws.cell(row=HEAD, column=i, value=txt)
    c.fill = fill(CARBON)
    c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.border = box_thin
ws.row_dimensions[HEAD].height = 20

N = 25
first = HEAD + 1
last  = HEAD + N

# Validaciones
dv_suc = DataValidation(type="list",
    formula1='"L Montejano,Montecarlo,Hacienda del Rio,Villas del Rey,San Marcos,Cine Curto,Oficina,General"',
    allow_blank=True)
dv_forma = DataValidation(type="list",
    formula1='"Efectivo,Bajio,Banorte,BBVA,Transferencia,Cheque,Clip"', allow_blank=True)
dv_estatus = DataValidation(type="list",
    formula1='"Pagado,Pendiente"', allow_blank=True)
for dv in (dv_suc, dv_forma, dv_estatus):
    ws.add_data_validation(dv)

for i in range(N):
    r = first + i
    ws.row_dimensions[r].height = 18
    ws.cell(row=r, column=1, value=i+1).font = Font(name="Arial", size=10, color=GRIS)
    ws.cell(row=r, column=1).alignment = Alignment(horizontal="center", vertical="center")
    fe = ws.cell(row=r, column=2); fe.number_format = "dd/mm/yyyy"
    fe.alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r, column=3).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.cell(row=r, column=4).alignment = Alignment(horizontal="center", vertical="center")
    mo = ws.cell(row=r, column=5); mo.number_format = '"$"#,##0.00'
    mo.alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(row=r, column=6).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r, column=7).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r, column=8).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    dv_suc.add(ws.cell(row=r, column=4))
    dv_forma.add(ws.cell(row=r, column=6))
    dv_estatus.add(ws.cell(row=r, column=7))
    zebra = fill(CREMA) if i % 2 else fill("FFFFFF")
    for col in range(1, 9):
        cell = ws.cell(row=r, column=col)
        cell.border = box_thin
        cell.fill = zebra

# Formato condicional: fila en ROJO si estatus = Pendiente
rojo_font = Font(color=ROJO, bold=True)
ws.conditional_formatting.add(
    f"A{first}:H{last}",
    FormulaRule(formula=[f'$G{first}="Pendiente"'], font=rojo_font))

# ---------- TOTAL GENERAL ----------
rtot = last + 1
ws.merge_cells(f"A{rtot}:D{rtot}")
lab = ws.cell(row=rtot, column=1, value="TOTAL")
lab.font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
lab.alignment = Alignment(horizontal="right", vertical="center", indent=1)
lab.fill = fill(AMBAR)
val = ws.cell(row=rtot, column=5, value=f"=SUM(E{first}:E{last})")
val.number_format = '"$"#,##0.00'
val.font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
val.alignment = Alignment(horizontal="right", vertical="center")
val.fill = fill(ROJO)
for c in range(6, 9):
    ws.cell(row=rtot, column=c).fill = fill(AMBAR)
ws.row_dimensions[rtot].height = 22

# ---------- RESUMEN (SUMIF por forma de pago y por estatus) ----------
rr = rtot + 3
ws.merge_cells(f"C{rr}:D{rr}")
t1 = ws.cell(row=rr, column=3, value="RESUMEN POR FORMA DE PAGO")
t1.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
t1.alignment = Alignment(horizontal="center", vertical="center")
t1.fill = fill(CARBON)
ws.cell(row=rr, column=3).border = box_thin
ws.cell(row=rr, column=4).border = box_thin

formas = ["Efectivo", "Bajio", "Banorte", "BBVA", "Transferencia", "Cheque", "Clip"]
for j, fp in enumerate(formas, start=1):
    row = rr + j
    a = ws.cell(row=row, column=3, value=fp)
    a.font = Font(name="Arial", size=10, color=CARBON)
    a.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    b = ws.cell(row=row, column=4,
        value=f'=SUMIF($F${first}:$F${last},C{row},$E${first}:$E${last})')
    b.number_format = '"$"#,##0.00'
    b.alignment = Alignment(horizontal="right", vertical="center")
    a.border = box_thin; b.border = box_thin

# Resumen por estatus (a la derecha)
ws.merge_cells(f"F{rr}:G{rr}")
t2 = ws.cell(row=rr, column=6, value="RESUMEN POR ESTATUS")
t2.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
t2.alignment = Alignment(horizontal="center", vertical="center")
t2.fill = fill(CARBON)
ws.cell(row=rr, column=6).border = box_thin
ws.cell(row=rr, column=7).border = box_thin
for j, (et, color) in enumerate([("Pagado", VERDE), ("Pendiente", ROJO)], start=1):
    row = rr + j
    a = ws.cell(row=row, column=6, value=et)
    a.font = Font(name="Arial", size=10, bold=True, color=color)
    a.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    b = ws.cell(row=row, column=7,
        value=f'=SUMIF($G${first}:$G${last},F{row},$E${first}:$E${last})')
    b.number_format = '"$"#,##0.00'
    b.font = Font(name="Arial", size=10, bold=True, color=color)
    b.alignment = Alignment(horizontal="right", vertical="center")
    a.border = box_thin; b.border = box_thin

# Impresion
end = rr + len(formas) + 1
ws.print_area = f"A1:H{end}"
ws.page_setup.orientation = "landscape"
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0
ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.page_margins.left = ws.page_margins.right = 0.4

out = "/mnt/c/Users/Conta/Desktop/Control de Pagos - Titi Burger.xlsx"
wb.save(out)
print("Guardado:", out)
