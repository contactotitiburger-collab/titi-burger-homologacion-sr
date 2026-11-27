#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera plantilla de Orden de Compra para Titi Burger (Excel con formulas)."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

# --- Paleta Titi Burger ---
ROJO   = "C1272D"   # rojo parrilla
CARBON = "2B2B2B"   # negro carbon
CREMA  = "FFF7EC"   # crema/pan
AMBAR  = "F2A900"   # amarillo mostaza
GRIS   = "8A8A8A"

def fill(c): return PatternFill("solid", fgColor=c)
thin = Side(style="thin", color="D9D9D9")
med  = Side(style="medium", color=CARBON)
box_thin = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Orden de Compra"
ws.sheet_view.showGridLines = False

# Anchos de columna
anchos = {"A": 5, "B": 11, "C": 12, "D": 44, "E": 15, "F": 16}
for col, w in anchos.items():
    ws.column_dimensions[col].width = w

# ---------- ENCABEZADO ----------
ws.merge_cells("A1:F2")
h = ws["A1"]
h.value = "TITI BURGER  🍔"
h.font = Font(name="Arial Black", size=22, bold=True, color="FFFFFF")
h.alignment = Alignment(horizontal="left", vertical="center", indent=1)
for r in (1, 2):
    for c in range(1, 7):
        ws.cell(row=r, column=c).fill = fill(ROJO)

ws.merge_cells("A3:F3")
sub = ws["A3"]
sub.value = "ORDEN DE COMPRA"
sub.font = Font(name="Arial", size=13, bold=True, color=CARBON)
sub.alignment = Alignment(horizontal="right", vertical="center", indent=1)
sub.fill = fill(AMBAR)
ws.row_dimensions[1].height = 26
ws.row_dimensions[2].height = 26
ws.row_dimensions[3].height = 22

# ---------- DATOS DE LA ORDEN ----------
def label(cell, txt):
    c = ws[cell]; c.value = txt
    c.font = Font(name="Arial", size=9, bold=True, color=GRIS)
    c.alignment = Alignment(horizontal="left", vertical="center")

def campo(cell, merge=None, border=True):
    if merge: ws.merge_cells(merge)
    c = ws[cell]
    c.font = Font(name="Arial", size=11, color=CARBON)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    if border:
        rng = merge if merge else cell
        for row in ws[rng]:
            for cc in row:
                cc.border = Border(bottom=Side(style="thin", color=CARBON))
    return c

# Fila 5-6-7-8 : bloque izquierdo (proveedor) y derecho (folio/fecha)
label("A5", "PROVEEDOR");     campo("A6", "A6:D6")
label("A7", "CONTACTO / TEL.");campo("A8", "A8:D8")

label("E5", "FOLIO");          campo("E6", "E6:F6")
label("E7", "FECHA");          f = campo("E8", "E8:F8")
f.number_format = "dd/mm/yyyy"

# Sucursal + condiciones (fila 10-11)
label("A10", "SUCURSAL");      suc = campo("A11", "A11:C11")
label("D10", "CONDICIONES DE PAGO"); campo("D11", "D11:F11")

# Dropdown sucursales
sucursales = '"L Montejano,Montecarlo,Hacienda del Rio,Villas del Rey,San Marcos,Cine Curto"'
dv_suc = DataValidation(type="list", formula1=sucursales, allow_blank=True)
ws.add_data_validation(dv_suc); dv_suc.add(suc)

# ---------- TABLA DE PARTIDAS ----------
HEAD = 13
headers = ["#", "CANTIDAD", "UNIDAD", "DESCRIPCION DEL ARTICULO", "PRECIO UNIT.", "IMPORTE"]
for i, txt in enumerate(headers, start=1):
    c = ws.cell(row=HEAD, column=i, value=txt)
    c.fill = fill(CARBON)
    c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.border = box_thin
ws.row_dimensions[HEAD].height = 20

N = 18
first = HEAD + 1
last  = HEAD + N
dv_unidad = DataValidation(type="list",
    formula1='"Kg,Pza,Caja,Bolsa,Litro,Paq,Charola,Costal,Manojo,Docena"', allow_blank=True)
ws.add_data_validation(dv_unidad)

for i in range(N):
    r = first + i
    ws.row_dimensions[r].height = 18
    # No.
    ws.cell(row=r, column=1, value=i+1).font = Font(name="Arial", size=10, color=GRIS)
    ws.cell(row=r, column=1).alignment = Alignment(horizontal="center", vertical="center")
    # Cantidad
    ws.cell(row=r, column=2).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=r, column=2).number_format = "0.##"
    # Unidad (dropdown)
    ws.cell(row=r, column=3).alignment = Alignment(horizontal="center", vertical="center")
    dv_unidad.add(ws.cell(row=r, column=3))
    # Descripcion
    ws.cell(row=r, column=4).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    # Precio unitario
    pu = ws.cell(row=r, column=5)
    pu.number_format = '"$"#,##0.00'
    pu.alignment = Alignment(horizontal="right", vertical="center")
    # Importe = cantidad * precio
    imp = ws.cell(row=r, column=6, value=f"=IF(AND(B{r}<>\"\",E{r}<>\"\"),B{r}*E{r},\"\")")
    imp.number_format = '"$"#,##0.00'
    imp.alignment = Alignment(horizontal="right", vertical="center")
    # bordes + zebra
    zebra = fill(CREMA) if i % 2 else fill("FFFFFF")
    for col in range(1, 7):
        cell = ws.cell(row=r, column=col)
        cell.border = box_thin
        cell.fill = zebra

# ---------- TOTALES ----------
def total_row(r, etiqueta, formula, bold=False, big=False):
    ws.merge_cells(f"A{r}:D{r}")
    lab = ws.cell(row=r, column=5, value=etiqueta)
    lab.font = Font(name="Arial", size=11, bold=bold, color=CARBON)
    lab.alignment = Alignment(horizontal="right", vertical="center")
    val = ws.cell(row=r, column=6, value=formula)
    val.number_format = '"$"#,##0.00'
    val.font = Font(name="Arial", size=12 if big else 11, bold=bold,
                    color="FFFFFF" if big else CARBON)
    val.alignment = Alignment(horizontal="right", vertical="center")
    val.border = box_thin
    if big:
        val.fill = fill(ROJO)
        ws.cell(row=r, column=5).fill = fill(AMBAR)
    ws.row_dimensions[r].height = 20

rsub = last + 1
total_row(rsub,   "Subtotal",   f"=SUM(F{first}:F{last})")
total_row(rsub+1, "IVA 16%",    f"=F{rsub}*0.16")
total_row(rsub+2, "TOTAL",      f"=F{rsub}+F{rsub+1}", bold=True, big=True)

# ---------- FIRMAS ----------
fr = rsub + 5
for col, txt in [("A", "ELABORO"), ("C", "AUTORIZO"), ("E", "RECIBIO")]:
    idx = openpyxl.utils.column_index_from_string(col)
    ws.merge_cells(start_row=fr, start_column=idx, end_row=fr, end_column=idx+1)
    for c2 in range(idx, idx+2):
        ws.cell(row=fr, column=c2).border = Border(top=Side(style="thin", color=CARBON))
    lab = ws.cell(row=fr+1, column=idx, value=txt)
    ws.merge_cells(start_row=fr+1, start_column=idx, end_row=fr+1, end_column=idx+1)
    lab.font = Font(name="Arial", size=9, bold=True, color=GRIS)
    lab.alignment = Alignment(horizontal="center")

# Nota pie
ws.merge_cells(f"A{fr+3}:F{fr+3}")
nota = ws.cell(row=fr+3, column=1,
    value="Los precios incluyen entrega en sucursal. Cualquier variacion debe autorizarse antes de surtir.")
nota.font = Font(name="Arial", size=8, italic=True, color=GRIS)
nota.alignment = Alignment(horizontal="left")

# Impresion
ws.print_area = f"A1:F{fr+3}"
ws.page_setup.orientation = "portrait"
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0
ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.page_margins.left = ws.page_margins.right = 0.4

out = "/mnt/c/Users/Conta/Desktop/Orden de Compra - Titi Burger.xlsx"
wb.save(out)
print("Guardado:", out)
