#!/usr/bin/env python3
"""P&L por punto de venta Mayo 2026 — Excel verde claro con detalle escondido."""
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
OUT = Path("/home/tito/.openclaw/data/P&L por Sucursal Mayo 2026.xlsx")
OUT.parent.mkdir(parents=True, exist_ok=True)

# ============ DATOS ============
# Ventas mayo desde SR Admin
data = json.loads(Path("/home/tito/.openclaw/data/ventas_mayo_2026.json").read_text())
suc = data["sucursales"]

VENTAS = {
    "FOVISSTE":         suc["FOVISSTE"]["total"],
    "MONTECARLO":       suc["MONTECARLO"]["total"],
    "SAN MARCOS":       suc["SAN MARCOS"]["total"],
    "HACIENDA DEL RÍO": suc["HACIENDA DEL RÍO"]["total"],
    "CURTO":            suc["CURTO"]["total"],
    "VILLAS DEL REY":   suc["VILLAS DEL REY"]["total"],
}
TICKETS = {
    "FOVISSTE":         suc["FOVISSTE"]["tickets"],
    "MONTECARLO":       suc["MONTECARLO"]["tickets"],
    "SAN MARCOS":       suc["SAN MARCOS"]["tickets"],
    "HACIENDA DEL RÍO": suc["HACIENDA DEL RÍO"]["tickets"],
    "CURTO":            suc["CURTO"]["tickets"],
    "VILLAS DEL REY":   suc["VILLAS DEL REY"]["tickets"],
}
VENTA_TOTAL = sum(VENTAS.values())

# Porcentaje de venta por sucursal (para prorrateo)
PCT = {k: v/VENTA_TOTAL for k, v in VENTAS.items()}

# Nómina directa por sucursal (mensual = semanal × 4.33)
NOMINA_DIRECTA = {
    "FOVISSTE":         20040.45 * 4.33,   # 6 empleados (sucursal A)
    "MONTECARLO":       15098.27 * 4.33,   # 3 empleados (sucursal C)
    "SAN MARCOS":       7512.18 * 4.33,    # 2 empleados (sucursal E)
    "HACIENDA DEL RÍO": 7652.18 * 4.33,    # 2 empleados (sucursal B)
    "CURTO":            12738.27 * 4.33,   # 3 empleados
    "VILLAS DEL REY":   4646.09 * 4.33,    # 1 empleado (sucursal D)
}
EMPLEADOS_DIRECTOS = {
    "FOVISSTE": 6, "MONTECARLO": 3, "SAN MARCOS": 2,
    "HACIENDA DEL RÍO": 2, "CURTO": 3, "VILLAS DEL REY": 1,
}

# Nómina central (AM, AM/C, ADMVO, COCINA, MENSAJERO) — se prorratea por % venta
NOMINA_CENTRAL_SEMANAL = 3506.09 + 3846.09 + 9732.18 + 11148.27 + 4196.09  # AM+AM/C+ADMVO+COCINA+MENSAJERO
NOMINA_CENTRAL_MES = NOMINA_CENTRAL_SEMANAL * 4.33  # ~$140,600

# Rentas mensuales por sucursal (del cuadro semanal × 4.33)
RENTAS = {
    "FOVISSTE":         8740.35 * 4.33,   # "Rey Pachelli" del sábado
    "MONTECARLO":       9880 * 4.33,
    "SAN MARCOS":       10890 * 4.33,
    "HACIENDA DEL RÍO": 16000 * 4.33,      # martes
    "CURTO":            16983 * 4.33,
    "VILLAS DEL REY":   0,                 # no aparece en el cuadro — pendiente confirmar
}

# Servicios por sucursal (recibos identificados; bimestrales /2 para mensualizar)
# CFE bimestral /2 + Agua CESPM mensual + Gas Ecogas bimestral /2
SERVICIOS = {
    "FOVISSTE": {
        "CFE": (9892 + 9608) / 2,  # 2 recibos de Fovissste/L Montejano
        "Agua": 5436,
        "Gas": 5649 / 2,
    },
    "MONTECARLO": {
        "CFE": (2046 + 738 + 517) / 2,  # 3 recibos de Montecarlo
        "Agua": 6849,
        "Gas": 248 / 2,
    },
    "SAN MARCOS": {
        "CFE": 741 / 2,
        "Agua": 804,
        "Gas": 0,  # no aparece recibo
    },
    "HACIENDA DEL RÍO": {
        "CFE": 0,  # no aparece recibo específico
        "Agua": 0,
        "Gas": 0,
    },
    "CURTO": {
        "CFE": 0,
        "Agua": 0,
        "Gas": 0,
    },
    "VILLAS DEL REY": {
        "CFE": 0,
        "Agua": 288,
        "Gas": 759 / 2,
    },
}

# Costos indirectos totales (mensuales) — se prorratean por % venta
PROVEEDORES_COMIDA_MES = 200000
REFRESCOS_MES = 56000
CARBON_MES = 58200
GASOLINA_MES = 151500
IMSS_INFONAVIT_MES = 142694  # patronal (Lonchería $120k + Herrería $22k)
FONACOT_MES = 9681.55 * 4.33  # descuento a empleado
LICENCIAS_SR_MES = 926.84 * 6  # 6 sucursales

# ============ EXCEL ============
wb = Workbook()

# Paleta VERDE CLARO
FILL_HEADER = PatternFill("solid", fgColor="66BB6A")   # verde medio para headers
FILL_SUB    = PatternFill("solid", fgColor="A5D6A7")   # verde claro para subheaders
FILL_CAT    = PatternFill("solid", fgColor="C8E6C9")   # verde muy claro para categorías
FILL_TOT    = PatternFill("solid", fgColor="81C784")   # verde para totales
FILL_UTIL   = PatternFill("solid", fgColor="4CAF50")   # verde fuerte para utilidad
FILL_ROJO   = PatternFill("solid", fgColor="EF9A9A")   # rojo suave para negativos
FILL_ALT    = PatternFill("solid", fgColor="F1F8E9")   # verde blanquecino alterno

FONT_TITLE  = Font(name="Arial", size=16, bold=True, color="FFFFFF")
FONT_HEADER = Font(name="Arial", size=12, bold=True, color="FFFFFF")
FONT_SUB    = Font(name="Arial", size=11, bold=True, color="1B5E20")
FONT_CAT    = Font(name="Arial", size=11, bold=True, color="2E7D32")
FONT_BODY   = Font(name="Arial", size=10)
FONT_TOTAL  = Font(name="Arial", size=12, bold=True, color="FFFFFF")

thin = Side(border_style="thin", color="A5D6A7")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

def money(cell): cell.number_format = '"$"#,##0.00'
def pct(cell): cell.number_format = '0.00%'

# ============ HOJA 1: P&L POR SUCURSAL ============
ws = wb.active
ws.title = "P&L por Sucursal"

SUCS = list(VENTAS.keys())

# Ancho columnas
ws.column_dimensions["A"].width = 42
for i, _ in enumerate(SUCS, start=2):
    ws.column_dimensions[get_column_letter(i)].width = 17
ws.column_dimensions[get_column_letter(len(SUCS)+2)].width = 17  # TOTAL

# Título
last_col = get_column_letter(len(SUCS)+2)
ws.merge_cells(f"A1:{last_col}1")
ws["A1"] = "P&L POR PUNTO DE VENTA — MAYO 2026"
ws["A1"].font = FONT_TITLE; ws["A1"].fill = FILL_HEADER
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 32

# Fila 2: nombres de sucursales como headers
ws.cell(row=2, column=1, value="").fill = FILL_SUB
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=2, column=i, value=s)
    c.font = FONT_HEADER; c.fill = FILL_HEADER
    c.alignment = Alignment(horizontal="center")
c = ws.cell(row=2, column=len(SUCS)+2, value="TOTAL")
c.font = FONT_HEADER; c.fill = FILL_HEADER
c.alignment = Alignment(horizontal="center")

row = 3

# Sección VENTAS
c = ws.cell(row=row, column=1, value="INGRESOS"); c.font = FONT_SUB; c.fill = FILL_SUB
for i in range(2, len(SUCS)+3):
    ws.cell(row=row, column=i).fill = FILL_SUB
row += 1

ws.cell(row=row, column=1, value="  Venta bruta mayo (SR Admin)").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=row, column=i, value=VENTAS[s]); money(c); c.font = FONT_BODY
c = ws.cell(row=row, column=len(SUCS)+2, value=VENTA_TOTAL); money(c); c.font = FONT_TOTAL; c.fill = FILL_TOT
venta_row = row
row += 1

ws.cell(row=row, column=1, value="  Tickets vendidos").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    ws.cell(row=row, column=i, value=TICKETS[s])
ws.cell(row=row, column=len(SUCS)+2, value=sum(TICKETS.values())).font = Font(bold=True)
row += 1

ws.cell(row=row, column=1, value="  Ticket promedio").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=row, column=i, value=VENTAS[s]/TICKETS[s] if TICKETS[s] else 0); money(c)
c = ws.cell(row=row, column=len(SUCS)+2, value=VENTA_TOTAL/sum(TICKETS.values())); money(c); c.font = Font(bold=True)
row += 1

ws.cell(row=row, column=1, value="  % de la venta total").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=row, column=i, value=PCT[s]); pct(c)
c = ws.cell(row=row, column=len(SUCS)+2, value=1.0); pct(c); c.font = Font(bold=True)
row += 2

# COSTOS DIRECTOS
c = ws.cell(row=row, column=1, value="COSTOS DIRECTOS DE LA SUCURSAL"); c.font = FONT_SUB; c.fill = FILL_SUB
for i in range(2, len(SUCS)+3):
    ws.cell(row=row, column=i).fill = FILL_SUB
row += 1

# Nómina directa
ws.cell(row=row, column=1, value="  Nómina empleados (mensual)").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=row, column=i, value=NOMINA_DIRECTA[s]); money(c)
c = ws.cell(row=row, column=len(SUCS)+2, value=sum(NOMINA_DIRECTA.values())); money(c); c.font = Font(bold=True)
row += 1

# # empleados
ws.cell(row=row, column=1, value="  # empleados directos").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    ws.cell(row=row, column=i, value=EMPLEADOS_DIRECTOS[s])
ws.cell(row=row, column=len(SUCS)+2, value=sum(EMPLEADOS_DIRECTOS.values())).font = Font(bold=True)
row += 1

# Renta
ws.cell(row=row, column=1, value="  Renta mensual").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=row, column=i, value=RENTAS[s]); money(c)
c = ws.cell(row=row, column=len(SUCS)+2, value=sum(RENTAS.values())); money(c); c.font = Font(bold=True)
row += 1

# Servicios
for concepto_srv in ["CFE", "Agua", "Gas"]:
    ws.cell(row=row, column=1, value=f"  {concepto_srv}").font = FONT_BODY
    tot = 0
    for i, s in enumerate(SUCS, start=2):
        v = SERVICIOS[s].get(concepto_srv, 0)
        c = ws.cell(row=row, column=i, value=v); money(c)
        tot += v
    c = ws.cell(row=row, column=len(SUCS)+2, value=tot); money(c); c.font = Font(bold=True)
    row += 1

# Licencia SR
ws.cell(row=row, column=1, value="  Licencia Soft Restaurant").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=row, column=i, value=926.84); money(c)
c = ws.cell(row=row, column=len(SUCS)+2, value=LICENCIAS_SR_MES); money(c); c.font = Font(bold=True)
row += 2

# COSTOS INDIRECTOS (prorrateados por % venta)
c = ws.cell(row=row, column=1, value="COSTOS PRORRATEADOS (por % de venta)"); c.font = FONT_SUB; c.fill = FILL_SUB
for i in range(2, len(SUCS)+3):
    ws.cell(row=row, column=i).fill = FILL_SUB
row += 1

for concepto, total_mes in [
    ("Proveedores comida", PROVEEDORES_COMIDA_MES),
    ("Refrescos y bebidas", REFRESCOS_MES),
    ("Carbón", CARBON_MES),
    ("Gasolina", GASOLINA_MES),
    ("IMSS + Infonavit (patronal)", IMSS_INFONAVIT_MES),
    ("Fonacot (retención)", FONACOT_MES),
    ("Nómina central (AM/ADMVO/COCINA/MENS)", NOMINA_CENTRAL_MES),
]:
    ws.cell(row=row, column=1, value=f"  {concepto}").font = FONT_BODY
    for i, s in enumerate(SUCS, start=2):
        c = ws.cell(row=row, column=i, value=total_mes * PCT[s]); money(c)
    c = ws.cell(row=row, column=len(SUCS)+2, value=total_mes); money(c); c.font = Font(bold=True)
    row += 1

row += 1

# ---- Totales por sucursal ----
c = ws.cell(row=row, column=1, value="TOTAL COSTOS"); c.font = FONT_TOTAL; c.fill = FILL_TOT
for i, s in enumerate(SUCS, start=2):
    # Directos
    directos = NOMINA_DIRECTA[s] + RENTAS[s] + sum(SERVICIOS[s].values()) + 926.84
    # Indirectos
    indirectos = PCT[s] * (PROVEEDORES_COMIDA_MES + REFRESCOS_MES + CARBON_MES + GASOLINA_MES
                           + IMSS_INFONAVIT_MES + FONACOT_MES + NOMINA_CENTRAL_MES)
    total = directos + indirectos
    c = ws.cell(row=row, column=i, value=total); money(c); c.font = Font(bold=True, color="FFFFFF"); c.fill = FILL_TOT

TOT_COSTOS_TOTAL = (sum(NOMINA_DIRECTA.values()) + sum(RENTAS.values())
                    + sum(sum(v.values()) for v in SERVICIOS.values())
                    + LICENCIAS_SR_MES
                    + PROVEEDORES_COMIDA_MES + REFRESCOS_MES + CARBON_MES + GASOLINA_MES
                    + IMSS_INFONAVIT_MES + FONACOT_MES + NOMINA_CENTRAL_MES)
c = ws.cell(row=row, column=len(SUCS)+2, value=TOT_COSTOS_TOTAL); money(c); c.font = FONT_TOTAL; c.fill = FILL_TOT
row += 1

# UTILIDAD
c = ws.cell(row=row, column=1, value="UTILIDAD (Ingresos − Costos)"); c.font = FONT_TOTAL; c.fill = FILL_UTIL
utils = {}
for i, s in enumerate(SUCS, start=2):
    directos = NOMINA_DIRECTA[s] + RENTAS[s] + sum(SERVICIOS[s].values()) + 926.84
    indirectos = PCT[s] * (PROVEEDORES_COMIDA_MES + REFRESCOS_MES + CARBON_MES + GASOLINA_MES
                           + IMSS_INFONAVIT_MES + FONACOT_MES + NOMINA_CENTRAL_MES)
    util = VENTAS[s] - directos - indirectos
    utils[s] = util
    c = ws.cell(row=row, column=i, value=util); money(c); c.font = FONT_TOTAL
    c.fill = FILL_UTIL if util >= 0 else FILL_ROJO
util_tot = VENTA_TOTAL - TOT_COSTOS_TOTAL
c = ws.cell(row=row, column=len(SUCS)+2, value=util_tot); money(c); c.font = FONT_TOTAL
c.fill = FILL_UTIL if util_tot >= 0 else FILL_ROJO
row += 1

# Margen %
c = ws.cell(row=row, column=1, value="Margen % (Utilidad / Venta)"); c.font = Font(bold=True, color="1B5E20")
for i, s in enumerate(SUCS, start=2):
    c = ws.cell(row=row, column=i, value=utils[s]/VENTAS[s] if VENTAS[s] else 0); pct(c); c.font = Font(bold=True)
c = ws.cell(row=row, column=len(SUCS)+2, value=util_tot/VENTA_TOTAL if VENTA_TOTAL else 0); pct(c); c.font = Font(bold=True)

# ============ HOJA 2: DETALLE NÓMINA ============
ws2 = wb.create_sheet("Detalle Nómina")
ws2.column_dimensions["A"].width = 22
ws2.column_dimensions["B"].width = 20
ws2.column_dimensions["C"].width = 22
for col in ["D","E","F","G","H"]:
    ws2.column_dimensions[col].width = 13
ws2.merge_cells("A1:H1")
ws2["A1"] = "DETALLE NÓMINA POR SUCURSAL — Fuente: catálogo empleados (backup 8-jul-2026)"
ws2["A1"].font = FONT_TITLE; ws2["A1"].fill = FILL_HEADER
ws2["A1"].alignment = Alignment(horizontal="center")

headers = ["Sucursal", "Empleado", "Puesto", "Sal semanal", "Bono Puntual", "Bono Encargado", "Total semanal", "Total mensual"]
for i, h in enumerate(headers, start=1):
    c = ws2.cell(row=3, column=i, value=h); c.font = FONT_HEADER; c.fill = FILL_HEADER

# Leer catálogo empleados de nuevo
from openpyxl import load_workbook
wb_emp = load_workbook('/home/tito/.openclaw/backups/nomina_2026-07-08.xlsx', data_only=True)
ws_emp = wb_emp["empleados"]

# Mapeo sucursal_codigo → nombre bonito
SUC_MAP = {
    "A": "FOVISSTE",
    "B": "HACIENDA DEL RÍO",
    "C": "MONTECARLO",
    "D": "VILLAS DEL REY",
    "E": "SAN MARCOS",
    "CURTO": "CURTO",
    "AM": "AM (central)",
    "AM/C": "AM/C (central)",
    "ADMVO": "OFICINA (central)",
    "COCINA": "COCINA (central)",
    "MENSAJERO": "MENSAJERO (central)",
}

r = 4
for row_e in ws_emp.iter_rows(min_row=2, values_only=True):
    if not row_e[0]: continue
    id_, corto, completo, nss, suc_cod, suc_nom, puesto, sal_sem, bono_p, bono_e, ing, baja, activo, notas, cr, up = row_e
    if activo != 1: continue
    ws2.cell(row=r, column=1, value=SUC_MAP.get(suc_cod, suc_cod))
    ws2.cell(row=r, column=2, value=corto)
    ws2.cell(row=r, column=3, value=puesto)
    c = ws2.cell(row=r, column=4, value=sal_sem or 0); money(c)
    c = ws2.cell(row=r, column=5, value=bono_p or 0); money(c)
    c = ws2.cell(row=r, column=6, value=bono_e or 0); money(c)
    tot_sem = (sal_sem or 0) + (bono_p or 0) + (bono_e or 0)
    c = ws2.cell(row=r, column=7, value=tot_sem); money(c); c.font = Font(bold=True)
    c = ws2.cell(row=r, column=8, value=tot_sem * 4.33); money(c); c.font = Font(bold=True)
    r += 1

# ============ HOJA 3: DETALLE ESCONDIDO ============
ws3 = wb.create_sheet("Detalle y Supuestos")
ws3.column_dimensions["A"].width = 45
ws3.column_dimensions["B"].width = 25
ws3.column_dimensions["C"].width = 70

ws3.merge_cells("A1:C1")
ws3["A1"] = "DETALLE, FÓRMULAS Y SUPUESTOS"
ws3["A1"].font = FONT_TITLE; ws3["A1"].fill = FILL_HEADER
ws3["A1"].alignment = Alignment(horizontal="center")

# Filas de detalle
detalles = [
    ("SECCIÓN INGRESOS", None, None),
    ("Venta bruta mayo", f"${VENTA_TOTAL:,.2f}", "SR Admin — reporte 'Ventas mensuales' del 10-jul-2026, las 6 sucursales"),
    ("", None, None),
    ("SECCIÓN NÓMINA DIRECTA", None, None),
    ("Empleados con sucursal asignada", "17", "de un total de 26 activos (los otros 9 son centrales: AM, AM/C, ADMVO, COCINA, MENSAJERO)"),
    ("Fórmula mensualización", "semanal × 4.33", "aproximación semanas por mes"),
    ("Fuente", "catálogo empleados", "backup nomina_2026-07-08.xlsx"),
    ("", None, None),
    ("SECCIÓN NÓMINA CENTRAL (prorrateo)", None, None),
    ("Empleados centrales", "9", "AM (Jennifer), AM/C (Carlos), ADMVO (David, Nancy Lizeth), COCINA (Andrónica, Yazmín, Sandra), MENSAJERO (Susano)"),
    ("Nómina central mensual", f"${NOMINA_CENTRAL_MES:,.2f}", "sumada y prorrateada por % de venta de cada sucursal"),
    ("", None, None),
    ("SECCIÓN RENTAS", None, None),
    ("Fuente rentas", "cuadro semanal foto 10-jul", "cada sucursal tiene su renta semanal identificada"),
    ("FOVISSTE (Rey Pachelli)", f"${RENTAS['FOVISSTE']:,.2f}", "$8,740.35/sem × 4.33"),
    ("MONTECARLO", f"${RENTAS['MONTECARLO']:,.2f}", "$9,880/sem × 4.33"),
    ("SAN MARCOS", f"${RENTAS['SAN MARCOS']:,.2f}", "$10,890/sem × 4.33"),
    ("HACIENDA DEL RÍO", f"${RENTAS['HACIENDA DEL RÍO']:,.2f}", "$16,000/sem × 4.33 (verificar frecuencia)"),
    ("CURTO", f"${RENTAS['CURTO']:,.2f}", "$16,983/sem × 4.33 — la más cara"),
    ("VILLAS DEL REY", "$0.00", "🔴 NO aparece en el cuadro semanal — pendiente confirmar con Nancy"),
    ("", None, None),
    ("SECCIÓN SERVICIOS", None, None),
    ("Fuente", "recibos CFE, CESPM, Ecogas", "de los 96 recibos enviados 10-jul-2026 12:46"),
    ("CFE (bimestral)", "recibo/2", "prorrateado a mensual"),
    ("Agua CESPM (mensual)", "monto directo", ""),
    ("Gas Ecogas (bimestral)", "recibo/2", "prorrateado a mensual"),
    ("Sucursales SIN recibo identificado", "HACIENDA, CURTO parciales", "asumido $0 — subestima costo real; pedir recibos"),
    ("", None, None),
    ("SECCIÓN COSTOS PRORRATEADOS", None, None),
    ("Base de prorrateo", "% venta de cada sucursal", "FOVISSTE 36.76%, MONTECARLO 26.06%, HACIENDA 10.65%, CURTO 10.40%, SAN MARCOS 8.22%, VILLAS 7.90%"),
    ("Proveedores comida", f"${PROVEEDORES_COMIDA_MES:,.2f}", "Costalonorte $42k/sem, Bimbo, Bona (carne), Islas (pollo), Julián, Kowi, verduras QM, Parra"),
    ("Refrescos y bebidas", f"${REFRESCOS_MES:,.2f}", "Coca $5.5k + Peñafiel $3.5k + Pepsi $4k + Quevedo $5.5k semanal"),
    ("Carbón", f"${CARBON_MES:,.2f}", "$13.4k/sem"),
    ("Gasolina", f"${GASOLINA_MES:,.2f}", "$35k/sem — el rubro más sospechoso (parece alto para 6 sucursales fijas)"),
    ("IMSS + Infonavit patronal", f"${IMSS_INFONAVIT_MES:,.2f}", "Lonchería $120k + Herrería $22k (recibos junio 2026 vencen 20-jul)"),
    ("Fonacot", f"${FONACOT_MES:,.2f}", "$9,681/semana — retención a empleados afiliados"),
    ("Licencia Soft Restaurant", f"${LICENCIAS_SR_MES:,.2f}", "6 sucursales × $926.84/mes (incluye Curto que estuvo suspendida)"),
    ("", None, None),
    ("COSTOS NO PRORRATEADOS (NO METIDOS EN ESTE P&L)", None, None),
    ("Andrónica préstamos Santander", "$137,000/mes", "$45k crédito simple + $92k revolvente (bloqueada por atrasos) — NO es gasto operativo, es servicio de deuda"),
    ("Retiro personal Don Titi ('Otros $60k/sem')", "$259,800/mes", "nómina personal, usualmente para AmEx — NO es operación del negocio"),
    ("Personales mezclados", "~$110,000/mes", "Hipoteca Titi, CFE casa, Ecogas casa, Liverpool, Carola, Arándano — NO operativo"),
    ("Abogado, mantenimiento, otros", "~$21,000/mes", "no atribuibles a una sucursal específica"),
    ("", None, None),
    ("QUÉ FALTA PARA CERRAR", None, None),
    ("Renta Villas del Rey", "?", "confirmar con Nancy"),
    ("Recibos servicios completos", "Hacienda, Curto, San Marcos, Villas", "para dejar de subestimar servicios"),
    ("Desglose apps (Uber/Rappi/DiDi)", "pendiente", "esperando accesos vía Elías o liquidaciones de Nancy"),
    ("Reparto real proveedores por sucursal", "pendiente", "hoy prorrateado por venta — puede sobreestimar o subestimar sucursales chicas"),
]

r = 3
for label, valor, nota in detalles:
    if label and not valor and not nota:
        c = ws3.cell(row=r, column=1, value=label); c.font = FONT_CAT; c.fill = FILL_CAT
        ws3.cell(row=r, column=2).fill = FILL_CAT
        ws3.cell(row=r, column=3).fill = FILL_CAT
    elif label:
        ws3.cell(row=r, column=1, value=label).font = FONT_BODY
        ws3.cell(row=r, column=2, value=valor).font = FONT_BODY
        ws3.cell(row=r, column=3, value=nota).font = FONT_BODY
    r += 1

# ============ HOJA 4: VENTAS BRUTAS ============
ws4 = wb.create_sheet("Ventas Mayo")
ws4.column_dimensions["A"].width = 25
for col in ["B","C","D","E","F","G"]:
    ws4.column_dimensions[col].width = 15
ws4.merge_cells("A1:G1")
ws4["A1"] = "VENTAS MAYO 2026 (SR ADMIN)"
ws4["A1"].font = FONT_TITLE; ws4["A1"].fill = FILL_HEADER
ws4["A1"].alignment = Alignment(horizontal="center")

hdrs = ["Sucursal", "Tickets", "Ticket prom", "Subtotal", "Descuentos", "Impuestos", "TOTAL"]
for i, h in enumerate(hdrs, start=1):
    c = ws4.cell(row=3, column=i, value=h); c.font = FONT_HEADER; c.fill = FILL_HEADER

for i, (name, s) in enumerate(suc.items(), start=4):
    ws4.cell(row=i, column=1, value=name)
    if "tickets" in s:
        ws4.cell(row=i, column=2, value=s["tickets"])
        c = ws4.cell(row=i, column=3, value=s["ticket_promedio"]); money(c)
        c = ws4.cell(row=i, column=4, value=s["subtotal"]); money(c)
        c = ws4.cell(row=i, column=5, value=s["descuentos"]); money(c)
        c = ws4.cell(row=i, column=6, value=s["impuestos"]); money(c)
        c = ws4.cell(row=i, column=7, value=s["total"]); money(c); c.font = Font(bold=True)

# Guardar
wb.save(OUT)
print(f"Excel guardado: {OUT}", flush=True)

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
    print(f"Creada: {name}  id={folder['id']}", flush=True)
    return folder["id"]

analisis_id = find_or_create_folder("Titi Burger - Análisis por Sucursal", TITI_BURGER_FOLDER)
anio_id = find_or_create_folder("2026", analisis_id)

file_name = "P&L por Sucursal Mayo 2026"
media = MediaFileUpload(str(OUT),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)

existing = d.files().list(
    q=f"name='{file_name}' and '{anio_id}' in parents and trashed=false",
    fields="files(id)"
).execute().get("files", [])
if existing:
    d.files().update(fileId=existing[0]["id"], media_body=media).execute()
    print(f"Actualizado: {file_name}", flush=True)
    print(f"Link: https://docs.google.com/spreadsheets/d/{existing[0]['id']}/edit", flush=True)
else:
    file_meta = {
        "name": file_name, "parents": [anio_id],
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }
    f = d.files().create(body=file_meta, media_body=media, fields="id,webViewLink").execute()
    print(f"Subido: {file_name}", flush=True)
    print(f"Link: {f.get('webViewLink')}", flush=True)
