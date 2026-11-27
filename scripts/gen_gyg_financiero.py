#!/usr/bin/env python3
"""Excel de Ganancias y Gastos por Sucursal — Mayo 2026.
Diseño financiero profesional: bordes cuadrados, fórmulas conectadas, estilo Estado de Resultados."""
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
OUT = Path("/home/tito/.openclaw/data/Ganancias y Gastos por Sucursal Mayo 2026.xlsx")

# ============ INPUTS ============
data = json.loads(Path("/home/tito/.openclaw/data/ventas_mayo_2026.json").read_text())
S = data["sucursales"]
SUCS = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]

# Venta y tickets
VENTA = {s: S[s]["total"] for s in SUCS}
TICKETS = {s: S[s]["tickets"] for s in SUCS}

# Nómina directa mensual (semanal × 4.33)
NOMINA_DIR = {
    "FOVISSTE":         20040.45,
    "MONTECARLO":       15098.27,
    "SAN MARCOS":       7512.18,
    "HACIENDA DEL RÍO": 7652.18,
    "CURTO":            12738.27,
    "VILLAS DEL REY":   4646.09,
}
EMP_DIR = {"FOVISSTE": 6, "MONTECARLO": 3, "SAN MARCOS": 2,
           "HACIENDA DEL RÍO": 2, "CURTO": 3, "VILLAS DEL REY": 1}

# Renta mensual (SON MENSUALES — Staff confirmó 10-jul-2026, no multiplicar ×4.33)
RENTA_MES = {
    "FOVISSTE":         0.00,       # pendiente confirmar con Staff
    "MONTECARLO":       9880.00,
    "SAN MARCOS":       10890.00,
    "HACIENDA DEL RÍO": 16000.00,
    "CURTO":            16983.00,
    "VILLAS DEL REY":   0.00,       # no aparece en el cuadro
}
# Almacén Pachelli (mensual) — va como costo repartido, no directo de sucursal
ALMACEN_PACHELLI = 8740.35

# Servicios (calculados a mensual desde los recibos)
CFE_MES = {"FOVISSTE": (9892+9608)/2, "MONTECARLO": (2046+738+517)/2,
           "SAN MARCOS": 741/2, "HACIENDA DEL RÍO": 0, "CURTO": 0, "VILLAS DEL REY": 0}
AGUA_MES = {"FOVISSTE": 5436, "MONTECARLO": 6849, "SAN MARCOS": 804,
            "HACIENDA DEL RÍO": 0, "CURTO": 0, "VILLAS DEL REY": 288}
GAS_MES = {"FOVISSTE": 5649/2, "MONTECARLO": 248/2, "SAN MARCOS": 0,
           "HACIENDA DEL RÍO": 0, "CURTO": 0, "VILLAS DEL REY": 759/2}

# Costos globales mensuales
GLOBALES = {
    "Proveedores comida":               200000,
    "Refrescos y bebidas":              56000,
    "Carbón":                           58200,
    "Gasolina":                         151500,
    "IMSS + Infonavit (patronal)":      142694,
    "Fonacot (retención)":              9681.55 * 4.33,
    "Sueldos oficina/cocina/mensajero": 32428.63 * 4.33,  # 9 empleados centrales
    "Renta almacén Pachelli":           ALMACEN_PACHELLI,
}

# ============ ESTILOS ============
wb = Workbook()

# Paleta financiera, verde claro sutil
VERDE_HEADER = PatternFill("solid", fgColor="388E3C")
VERDE_SUB    = PatternFill("solid", fgColor="C8E6C9")
VERDE_TOT    = PatternFill("solid", fgColor="A5D6A7")
GRIS_ALT     = PatternFill("solid", fgColor="F5F5F5")
ROJO         = PatternFill("solid", fgColor="FFCDD2")

FT_TITLE  = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
FT_HEAD   = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
FT_SUB    = Font(name="Calibri", size=11, bold=True, color="1B5E20")
FT_BODY   = Font(name="Calibri", size=10)
FT_BOLD   = Font(name="Calibri", size=10, bold=True)
FT_TOT    = Font(name="Calibri", size=11, bold=True, color="000000")

thin = Side(border_style="thin", color="9E9E9E")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

def money_fmt(cell): cell.number_format = '"$"#,##0.00'
def pct_fmt(cell): cell.number_format = '0.00%'
def int_fmt(cell): cell.number_format = '#,##0'

def apply_box(ws, r1, c1, r2, c2):
    for r in range(r1, r2+1):
        for c in range(c1, c2+1):
            ws.cell(row=r, column=c).border = BOX

# ============ HOJA 1: GANANCIAS Y GASTOS POR SUCURSAL ============
ws = wb.active
ws.title = "Ganancias y Gastos"

# Anchos: A concepto, B-G sucursales, H total
ws.column_dimensions["A"].width = 44
for col in ["B","C","D","E","F","G"]:
    ws.column_dimensions[col].width = 18
ws.column_dimensions["H"].width = 18

# Row 1: TÍTULO
ws.merge_cells("A1:H1")
ws["A1"] = "GANANCIAS Y GASTOS POR SUCURSAL — MAYO 2026"
ws["A1"].font = FT_TITLE; ws["A1"].fill = VERDE_HEADER
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 24

# Row 2: headers sucursales
ws["A2"] = "Concepto"; ws["A2"].font = FT_HEAD; ws["A2"].fill = VERDE_HEADER
ws["A2"].alignment = Alignment(horizontal="center")
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=2, column=i, value=s)
    c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center")
c = ws.cell(row=2, column=8, value="TOTAL")
c.font = FT_HEAD; c.fill = VERDE_HEADER
c.alignment = Alignment(horizontal="center")

# ---- BLOQUE INGRESOS ----
r = 3
c = ws.cell(row=r, column=1, value="INGRESOS")
c.font = FT_SUB; c.fill = VERDE_SUB
for col in range(2, 9):
    ws.cell(row=r, column=col).fill = VERDE_SUB
r += 1

# Venta bruta (INPUT)
VENTA_ROW = r
ws.cell(row=r, column=1, value="Venta bruta").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=VENTA[s]); money_fmt(c); c.font = FT_BODY
# TOTAL con fórmula
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); money_fmt(c); c.font = FT_BOLD
r += 1

# Tickets (INPUT)
TICKETS_ROW = r
ws.cell(row=r, column=1, value="Tickets").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=TICKETS[s]); int_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); int_fmt(c); c.font = FT_BOLD
r += 1

# Ticket promedio (FÓRMULA = Venta / Tickets)
ws.cell(row=r, column=1, value="Ticket promedio").font = FT_BODY
for i in range(2, 9):
    col_letter = get_column_letter(i)
    c = ws.cell(row=r, column=i, value=f"=IFERROR({col_letter}{VENTA_ROW}/{col_letter}{TICKETS_ROW},0)")
    money_fmt(c); c.font = FT_BODY
r += 1

# % de venta total (FÓRMULA = Venta_i / Venta_total)
PCT_ROW = r
ws.cell(row=r, column=1, value="% de venta total").font = FT_BODY
for i in range(2, 8):
    col_letter = get_column_letter(i)
    c = ws.cell(row=r, column=i, value=f"={col_letter}{VENTA_ROW}/$H${VENTA_ROW}")
    pct_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=1.0); pct_fmt(c); c.font = FT_BOLD
r += 2

# ---- BLOQUE COSTOS DIRECTOS ----
c = ws.cell(row=r, column=1, value="COSTOS DIRECTOS DE LA SUCURSAL")
c.font = FT_SUB; c.fill = VERDE_SUB
for col in range(2, 9):
    ws.cell(row=r, column=col).fill = VERDE_SUB
r += 1

# Sueldos de la sucursal (INPUT: semanal × 4.33)
NOMINA_ROW = r
ws.cell(row=r, column=1, value="Sueldos empleados de la sucursal").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=NOMINA_DIR[s] * 4.33); money_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); money_fmt(c); c.font = FT_BOLD
r += 1

# Empleados
ws.cell(row=r, column=1, value="Cuántos empleados").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=EMP_DIR[s]); int_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); int_fmt(c); c.font = FT_BOLD
r += 1

# Renta mensual (input directo del cuadro semanal — YA son mensuales)
RENTA_ROW = r
ws.cell(row=r, column=1, value="Renta mensual").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=RENTA_MES[s]); money_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); money_fmt(c); c.font = FT_BOLD
r += 1

# Luz (CFE)
CFE_ROW = r
ws.cell(row=r, column=1, value="Luz (CFE)").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=CFE_MES[s]); money_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); money_fmt(c); c.font = FT_BOLD
r += 1

# Agua
AGUA_ROW = r
ws.cell(row=r, column=1, value="Agua (CESPM)").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=AGUA_MES[s]); money_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); money_fmt(c); c.font = FT_BOLD
r += 1

# Gas
GAS_ROW = r
ws.cell(row=r, column=1, value="Gas (Ecogas)").font = FT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=r, column=i, value=GAS_MES[s]); money_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); money_fmt(c); c.font = FT_BOLD
r += 1

# Licencia Soft Restaurant
LIC_ROW = r
ws.cell(row=r, column=1, value="Licencia Soft Restaurant").font = FT_BODY
for i in range(2, 8):
    c = ws.cell(row=r, column=i, value=926.84); money_fmt(c); c.font = FT_BODY
c = ws.cell(row=r, column=8, value=f"=SUM(B{r}:G{r})"); money_fmt(c); c.font = FT_BOLD
r += 1

# Subtotal directos (FÓRMULA)
SUB_DIR_ROW = r
c = ws.cell(row=r, column=1, value="Subtotal costos directos")
c.font = FT_BOLD; c.fill = VERDE_TOT
for i in range(2, 9):
    col_letter = get_column_letter(i)
    c = ws.cell(row=r, column=i, value=f"={col_letter}{NOMINA_ROW}+{col_letter}{RENTA_ROW}+{col_letter}{CFE_ROW}+{col_letter}{AGUA_ROW}+{col_letter}{GAS_ROW}+{col_letter}{LIC_ROW}")
    money_fmt(c); c.font = FT_BOLD; c.fill = VERDE_TOT
r += 2

# ---- BLOQUE COSTOS REPARTIDOS (prorrateados por % venta) ----
c = ws.cell(row=r, column=1, value="COSTOS REPARTIDOS (por % de venta)")
c.font = FT_SUB; c.fill = VERDE_SUB
for col in range(2, 9):
    ws.cell(row=r, column=col).fill = VERDE_SUB
r += 1

globales_rows = {}
for concepto, monto_total in GLOBALES.items():
    ws.cell(row=r, column=1, value=concepto).font = FT_BODY
    for i in range(2, 8):
        col_letter = get_column_letter(i)
        # Fórmula: monto_total (input celda H) * % venta ($col$PCT_ROW)
        # Prefiero anclar el monto total en la col H (input) y prorratear con % venta
        c = ws.cell(row=r, column=i, value=f"=$H${r}*{col_letter}${PCT_ROW}")
        money_fmt(c); c.font = FT_BODY
    # Col H: monto total (INPUT)
    c = ws.cell(row=r, column=8, value=monto_total); money_fmt(c); c.font = FT_BOLD
    globales_rows[concepto] = r
    r += 1

# Subtotal repartidos (FÓRMULA)
first_g = min(globales_rows.values())
last_g = max(globales_rows.values())
SUB_REP_ROW = r
c = ws.cell(row=r, column=1, value="Subtotal costos repartidos")
c.font = FT_BOLD; c.fill = VERDE_TOT
for i in range(2, 9):
    col_letter = get_column_letter(i)
    c = ws.cell(row=r, column=i, value=f"=SUM({col_letter}{first_g}:{col_letter}{last_g})")
    money_fmt(c); c.font = FT_BOLD; c.fill = VERDE_TOT
r += 2

# ---- TOTALES FINALES ----
GASTO_TOT_ROW = r
c = ws.cell(row=r, column=1, value="GASTO TOTAL")
c.font = FT_TOT; c.fill = VERDE_TOT
for i in range(2, 9):
    col_letter = get_column_letter(i)
    c = ws.cell(row=r, column=i, value=f"={col_letter}{SUB_DIR_ROW}+{col_letter}{SUB_REP_ROW}")
    money_fmt(c); c.font = FT_TOT; c.fill = VERDE_TOT
r += 1

# Ganancia/Pérdida
GAN_ROW = r
c = ws.cell(row=r, column=1, value="GANANCIA / PÉRDIDA")
c.font = FT_TOT; c.fill = VERDE_HEADER; c.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
for i in range(2, 9):
    col_letter = get_column_letter(i)
    c = ws.cell(row=r, column=i, value=f"={col_letter}{VENTA_ROW}-{col_letter}{GASTO_TOT_ROW}")
    money_fmt(c); c.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF"); c.fill = VERDE_HEADER
r += 1

# Margen %
MARGEN_ROW = r
ws.cell(row=r, column=1, value="Margen sobre venta").font = FT_BOLD
for i in range(2, 9):
    col_letter = get_column_letter(i)
    c = ws.cell(row=r, column=i, value=f"=IFERROR({col_letter}{GAN_ROW}/{col_letter}{VENTA_ROW},0)")
    pct_fmt(c); c.font = FT_BOLD

# Bordes cuadrados a toda la tabla
apply_box(ws, 2, 1, r, 8)

# Congelar paneles
ws.freeze_panes = "B3"

# ============ HOJA 2: DATOS BASE (Inputs) ============
ws2 = wb.create_sheet("Datos base")
ws2.column_dimensions["A"].width = 45
ws2.column_dimensions["B"].width = 20
ws2.column_dimensions["C"].width = 60

ws2.merge_cells("A1:C1")
ws2["A1"] = "DATOS BASE — Fuentes de cada número"
ws2["A1"].font = FT_TITLE; ws2["A1"].fill = VERDE_HEADER
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 24

ws2["A2"] = "Concepto"; ws2["B2"] = "Valor / Referencia"; ws2["C2"] = "Fuente"
for col in [1, 2, 3]:
    c = ws2.cell(row=2, column=col); c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center")

filas_base = [
    ("Venta mayo (SR Admin)", f"${sum(VENTA.values()):,.2f}", "Panel admin.softrestaurant.com, reporte Ventas Mensuales, mayo 2026, 6 sucursales"),
    ("Tickets totales", f"{sum(TICKETS.values()):,}", "Mismo panel — reporte incluye tickets emitidos"),
    ("Nómina directa semanal (6 sucursales)", f"${sum(NOMINA_DIR.values()):,.2f}", "17 empleados con sucursal asignada (backup nómina 8-jul-2026)"),
    ("Nómina central semanal (9 empleados)", f"${32428.63:,.2f}", "Jennifer AM, Carlos AM/C, David/Nancy ADMVO, Andrónica/Yazmín/Sandra COCINA, Susano MENSAJERO"),
    ("Renta MENSUAL de sucursales identificadas", f"${sum(RENTA_MES.values()):,.2f}", "Cuadro Titi Burger (fotos 10-jul-2026). Confirmado por Staff: son mensuales, no semanales. Falta Fovissste y Villas del Rey."),
    ("Renta almacén Pachelli (repartida)", f"${ALMACEN_PACHELLI:,.2f}", "Es un almacén, no sucursal. Va como costo repartido entre las 6 sucursales según venta."),
    ("CFE (recibos bimestrales /2)", f"${sum(CFE_MES.values()):,.2f}", "Recibos CFE enviados 10-jul: FOVISSTE (2 medidores), MONTECARLO (3), SAN MARCOS (1)"),
    ("Agua CESPM mensual", f"${sum(AGUA_MES.values()):,.2f}", "Recibos CESPM: FOVISSTE $5,436, MONTECARLO $6,849, SAN MARCOS $804, VILLAS $288"),
    ("Gas Ecogas (bimestral /2)", f"${sum(GAS_MES.values()):,.2f}", "Recibos Ecogas: FOVISSTE, MONTECARLO, VILLAS. Sin recibo de HACIENDA, CURTO, SAN MARCOS"),
    ("Proveedores comida mensual", "$200,000", "Costalonorte $42k/sem + Bimbo + Bona (carne) + Islas (pollo) + Julián + Kowi + verduras QM + Parra"),
    ("Refrescos y bebidas mensual", "$56,000", "Coca $5.5k + Peñafiel $3.5k + Pepsi $4k + Quevedo $5.5k semanales"),
    ("Carbón mensual", "$58,200", "$13,453/semana × 4.33"),
    ("Gasolina mensual", "$151,500", "$35,000/semana × 4.33 — parece alto para 6 sucursales fijas; posible carga del rancho"),
    ("IMSS + Infonavit patronal", "$142,694", "Lonchería $120,578 + Herrería $22,116 (recibos IMSS junio 2026)"),
    ("Fonacot mensual", f"${9681.55*4.33:,.2f}", "$9,681.55/semana × 4.33 — retención a empleados afiliados"),
    ("Licencia Soft Restaurant", "$5,561.04", "6 sucursales × $926.84/mes (Backup Soluciones Informáticas)"),
    ("", "", ""),
    ("NO INCLUIDOS EN ESTE ANÁLISIS", "", ""),
    ("Retiro personal Don Titi", "$259,800/mes", "'Otros gastos' $60,000/L × 4.33 — usualmente para American Express"),
    ("Préstamos Santander Andrónica", "$137,000/mes", "Crédito simple $45k + Revolvente $92k (bloqueada por atrasos)"),
    ("Gastos personales mezclados", "~$110,000/mes", "Hipoteca Titi, CFE casa, Ecogas casa, Liverpool, Carola, Arándano"),
    ("Otros (abogado, mantenimiento)", "~$21,000/mes", "Abogado Luis, Casa del Acero, Casa del Carpintero, MJ, Halcón"),
    ("", "", ""),
    ("PENDIENTES DE CONFIRMAR", "", ""),
    ("Renta Villas del Rey", "?", "No aparece en el cuadro semanal — confirmar con Nancy"),
    ("Recibos servicios Hacienda del Río y Curto", "?", "Sin recibos identificados — sus servicios están en $0, subestima costo real"),
    ("Comisiones apps (Uber, Rappi, DiDi)", "?", "Pendiente accesos con Elías o liquidaciones"),
    ("Reparto real de proveedores por sucursal", "?", "Hoy prorrateado por venta; cada sucursal usa distinta cantidad de comida"),
]
r = 3
for label, valor, fuente in filas_base:
    if not label and not valor and not fuente:
        r += 1
        continue
    if not valor and not fuente:
        # es sección
        c = ws2.cell(row=r, column=1, value=label); c.font = FT_SUB; c.fill = VERDE_SUB
        for col in [2, 3]:
            ws2.cell(row=r, column=col).fill = VERDE_SUB
    else:
        c = ws2.cell(row=r, column=1, value=label); c.font = FT_BODY
        c = ws2.cell(row=r, column=2, value=valor); c.font = FT_BOLD
        c.alignment = Alignment(horizontal="right")
        c = ws2.cell(row=r, column=3, value=fuente); c.font = FT_BODY
        c.alignment = Alignment(wrap_text=True, vertical="top")
    apply_box(ws2, r, 1, r, 3)
    ws2.row_dimensions[r].height = 22
    r += 1

# ============ HOJA 3: NÓMINA POR EMPLEADO ============
ws3 = wb.create_sheet("Nómina por empleado")
ws3.column_dimensions["A"].width = 22
ws3.column_dimensions["B"].width = 20
ws3.column_dimensions["C"].width = 22
for col in ["D","E","F","G","H"]:
    ws3.column_dimensions[col].width = 15

ws3.merge_cells("A1:H1")
ws3["A1"] = "NÓMINA POR EMPLEADO — Base semanal + bonos + mensualización × 4.33"
ws3["A1"].font = FT_TITLE; ws3["A1"].fill = VERDE_HEADER
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 24

headers = ["Sucursal", "Empleado", "Puesto", "Sal semanal", "Bono Puntual", "Bono Encargado", "Total semanal", "Total mensual"]
for i, h in enumerate(headers, start=1):
    c = ws3.cell(row=3, column=i, value=h); c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center")

from openpyxl import load_workbook
wb_emp = load_workbook('/home/tito/.openclaw/backups/nomina_2026-07-08.xlsx', data_only=True)
ws_emp = wb_emp["empleados"]

SUC_MAP = {
    "A": "FOVISSTE", "B": "HACIENDA DEL RÍO", "C": "MONTECARLO",
    "D": "VILLAS DEL REY", "E": "SAN MARCOS", "CURTO": "CURTO",
    "AM": "AM (central)", "AM/C": "AM/C (central)", "ADMVO": "OFICINA (central)",
    "COCINA": "COCINA (central)", "MENSAJERO": "MENSAJERO (central)",
}

r = 4
empleados_data = []
for row_e in ws_emp.iter_rows(min_row=2, values_only=True):
    if not row_e[0]: continue
    id_, corto, completo, nss, suc_cod, suc_nom, puesto, sal_sem, bono_p, bono_e, ing, baja, activo, notas, cr, up = row_e
    if activo != 1: continue
    empleados_data.append((SUC_MAP.get(suc_cod, suc_cod), corto, puesto, sal_sem or 0, bono_p or 0, bono_e or 0))

# Ordenar por sucursal
empleados_data.sort(key=lambda x: (0 if x[0] in SUCS else 1, x[0], x[1]))

r_ini = 4
for suc, corto, puesto, sal, bp, be in empleados_data:
    ws3.cell(row=r, column=1, value=suc).font = FT_BODY
    ws3.cell(row=r, column=2, value=corto).font = FT_BODY
    ws3.cell(row=r, column=3, value=puesto).font = FT_BODY
    c = ws3.cell(row=r, column=4, value=sal); money_fmt(c); c.font = FT_BODY
    c = ws3.cell(row=r, column=5, value=bp); money_fmt(c); c.font = FT_BODY
    c = ws3.cell(row=r, column=6, value=be); money_fmt(c); c.font = FT_BODY
    # Total semanal = suma con fórmula
    c = ws3.cell(row=r, column=7, value=f"=D{r}+E{r}+F{r}"); money_fmt(c); c.font = FT_BOLD
    # Total mensual = semanal × 4.33
    c = ws3.cell(row=r, column=8, value=f"=G{r}*4.33"); money_fmt(c); c.font = FT_BOLD
    apply_box(ws3, r, 1, r, 8)
    r += 1

# Total general
c = ws3.cell(row=r, column=1, value="TOTAL"); c.font = FT_TOT; c.fill = VERDE_TOT
for col in range(2, 9):
    ws3.cell(row=r, column=col).fill = VERDE_TOT
for col_letter in ["D", "E", "F", "G", "H"]:
    c = ws3.cell(row=r, column=ord(col_letter)-ord('A')+1, value=f"=SUM({col_letter}{r_ini}:{col_letter}{r-1})")
    money_fmt(c); c.font = FT_TOT; c.fill = VERDE_TOT
apply_box(ws3, r, 1, r, 8)
ws3.freeze_panes = "A4"

# Guardar
wb.save(OUT)
print(f"Guardado: {OUT}", flush=True)

# Actualizar en Drive
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)
FILE_ID = "11ov6JINhx_ESbWWT4lR8cM2mQq7ePyP7Ldvb---79qw"
media = MediaFileUpload(str(OUT),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)
d.files().update(fileId=FILE_ID, media_body=media).execute()
print(f"Actualizado en Drive.", flush=True)
print(f"Link: https://docs.google.com/spreadsheets/d/{FILE_ID}/edit", flush=True)
