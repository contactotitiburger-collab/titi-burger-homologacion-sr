#!/usr/bin/env python3
"""Genera un Excel plantilla para que Rafael copie al pizarrón físico de la oficina."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path

OUT = Path.home() / ".openclaw/workspace/apps_delivery/Plantilla pizarron oficina.xlsx"

wb = Workbook()
ws = wb.active
ws.title = "Pizarrón"
ws.sheet_view.showGridLines = False

# Estilos
F_TIT = Font(name="Calibri", size=18, bold=True, color="FFFFFF")
F_SUB = Font(name="Calibri", size=13, bold=True, color="1F3864")
F_ITEM = Font(name="Calibri", size=11)
F_MONTO = Font(name="Calibri", size=11, bold=True)
FILL_TIT = PatternFill("solid", fgColor="1F3864")
FILL_SUB = PatternFill("solid", fgColor="D9E2F3")
FILL_ROJO = PatternFill("solid", fgColor="FFC7CE")
B = Side(style="medium", color="1F3864")
BORDE_GRUESO = Border(left=B, right=B, top=B, bottom=B)

# Anchos
for c, w in [(1, 3), (2, 30), (3, 15), (4, 15), (5, 3)]:
    ws.column_dimensions[get_column_letter(c)].width = w

# Título
ws.merge_cells("B2:D2")
c = ws.cell(2, 2, "PIZARRÓN DE PAGOS · TITI BURGER · ______________")
c.font = F_TIT; c.fill = FILL_TIT; c.alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[2].height = 32

fila = 4

def seccion(texto):
    global fila
    ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=4)
    c = ws.cell(fila, 2, texto)
    c.font = F_SUB; c.fill = FILL_SUB; c.alignment = Alignment(horizontal="left", indent=1)
    ws.row_dimensions[fila].height = 24
    fila += 1

def item(nombre, monto=""):
    global fila
    ws.cell(fila, 2, "▢  " + nombre).font = F_ITEM
    if monto:
        c = ws.cell(fila, 3, monto); c.font = F_MONTO; c.alignment = Alignment(horizontal="right")
        c.number_format = '"$"#,##0'
    else:
        c = ws.cell(fila, 3, "$ ______"); c.font = F_ITEM; c.alignment = Alignment(horizontal="right")
    ws.row_dimensions[fila].height = 20
    fila += 1

# ---- 1. RENTAS ----
seccion("1. RENTAS  (mensual)")
item("Renta Cine Curto", 16983)
item("Renta Fovissste")   # pendiente
item("Renta Montecarlo", 9880)
item("Renta Hacienda del Río", 10000)
item("Renta San Marcos", 10890)
item("Renta Villas del Rey")
item("Renta Pachelli (almacén)", 8740)

fila += 1

# ---- 2. SERVICIOS ----
seccion("2. SERVICIOS  (mensual)")
item("Luz — Fovissste")
item("Luz — Montecarlo")
item("Luz — Hacienda del Río")
item("Luz — San Marcos")
item("Luz — Villas del Rey")
item("Luz — Cine Curto")
item("Gas Ecogas")
item("Agua")
item("Internet")

fila += 1

# ---- 3. NÓMINA Y RETIROS ----
seccion("3. NÓMINA Y RETIROS  (semanal)")
item("Nómina viernes")
item("Retiro Don Titi (Amex)", 60000)
item("Abogado Luis", 2500)
item("Juan Muñoz (mantenimiento)", 2000)
item("Pascual Omar Domínguez", 3615)

fila += 1

# ---- 4. PRÉSTAMOS ----
seccion("4. PRÉSTAMOS Y CRÉDITOS  (mensual)")
item("Préstamo Santander 1 (Andrónica)", 45000)
item("Préstamo Santander 2 (Andrónica)", 92000)

fila += 1

# ---- 5. IMPUESTOS ----
seccion("5. IMPUESTOS Y APORTACIONES  (mensual)")
item("SAT")
item("IMSS")
item("Fonacot")
item("Infonavit")

fila += 1

# ---- 6. PROVEEDORES ----
seccion("6. PROVEEDORES  (cuando llega la factura)")
item("Bona (carne principal)")
item("Julián (carne secundario)")
item("Islas (pollo)")
item("Kowi (tocino)")
item("Papas")
item("Refrescos")
item("Empaques / desechables")
item("Pan / verduras")
item("Otros insumos")

fila += 1

# ---- 7. ATRASADOS ----
seccion("7. ATRASADOS / URGENTES  (poner en rojo)")
for _ in range(3):
    ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=4)
    c = ws.cell(fila, 2, "  ")
    c.fill = FILL_ROJO
    ws.row_dimensions[fila].height = 22
    fila += 1

fila += 1

# Instrucciones
ws.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=4)
c = ws.cell(fila, 2, "REGLAS: ▢ = pendiente  ·  ✓ = pagado (verde)  ·  rojo = urgente/atrasado  ·  cierre de mes → limpiar y empezar de nuevo")
c.font = Font(name="Calibri", size=9, italic=True, color="595959")
c.alignment = Alignment(wrap_text=True)
ws.row_dimensions[fila].height = 30

# borde alrededor de todo el bloque
for r in range(2, fila + 1):
    for co in range(2, 5):
        cell = ws.cell(r, co)
        if not cell.border.left.style:
            cell.border = Border(left=Side(style="thin", color="BFBFBF"),
                                 right=Side(style="thin", color="BFBFBF"),
                                 top=Side(style="thin", color="BFBFBF"),
                                 bottom=Side(style="thin", color="BFBFBF"))

wb.save(OUT)
print(f"Guardado: {OUT}")
