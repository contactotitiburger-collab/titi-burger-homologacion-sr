#!/usr/bin/env python3
"""Excel super simple para Don Titi — solo lo importante, letras grandes, colores claros."""
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

# ============ DATOS ============
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
TICKETS = {k: suc[k]["tickets"] for k in VENTAS}
VENTA_TOTAL = sum(VENTAS.values())
PCT = {k: v/VENTA_TOTAL for k, v in VENTAS.items()}

# Nómina mensual directa
NOMINA = {
    "FOVISSTE":         20040.45 * 4.33,
    "MONTECARLO":       15098.27 * 4.33,
    "SAN MARCOS":       7512.18 * 4.33,
    "HACIENDA DEL RÍO": 7652.18 * 4.33,
    "CURTO":            12738.27 * 4.33,
    "VILLAS DEL REY":   4646.09 * 4.33,
}
EMPLEADOS = {"FOVISSTE": 6, "MONTECARLO": 3, "SAN MARCOS": 2,
             "HACIENDA DEL RÍO": 2, "CURTO": 3, "VILLAS DEL REY": 1}

RENTAS = {
    "FOVISSTE":         8740.35 * 4.33,
    "MONTECARLO":       9880 * 4.33,
    "SAN MARCOS":       10890 * 4.33,
    "HACIENDA DEL RÍO": 16000 * 4.33,
    "CURTO":            16983 * 4.33,
    "VILLAS DEL REY":   0,
}
SERVICIOS = {
    "FOVISSTE": (9892+9608)/2 + 5436 + 5649/2,
    "MONTECARLO": (2046+738+517)/2 + 6849 + 248/2,
    "SAN MARCOS": 741/2 + 804,
    "HACIENDA DEL RÍO": 0,
    "CURTO": 0,
    "VILLAS DEL REY": 288 + 759/2,
}

# Gastos globales prorrateados por venta
GASTOS_GLOBALES = 200000 + 56000 + 58200 + 151500 + 142694 + 41921 + 140596 + 5561
# proveedores + refrescos + carbón + gasolina + IMSS/Infonavit + Fonacot + nómina central + licencias SR

# Cálculos por sucursal
RESUMEN = {}
for s in VENTAS:
    venta = VENTAS[s]
    gasto = NOMINA[s] + RENTAS[s] + SERVICIOS[s] + PCT[s]*GASTOS_GLOBALES
    ganancia = venta - gasto
    RESUMEN[s] = {"venta": venta, "gasto": gasto, "ganancia": ganancia,
                  "empleados": EMPLEADOS[s], "tickets": TICKETS[s]}

TOTAL_GASTO = sum(r["gasto"] for r in RESUMEN.values())
TOTAL_GANANCIA = VENTA_TOTAL - TOTAL_GASTO

# ============ EXCEL ============
wb = Workbook()

# Paleta verde claro suave
VERDE_FUERTE = PatternFill("solid", fgColor="2E7D32")   # verde bandera para header
VERDE_MEDIO  = PatternFill("solid", fgColor="66BB6A")   # subheader
VERDE_CLARO  = PatternFill("solid", fgColor="A5D6A7")   # total
VERDE_MUY    = PatternFill("solid", fgColor="E8F5E9")   # fondo alterno
ROJO_SUAVE   = PatternFill("solid", fgColor="EF9A9A")   # pérdida
DORADO       = PatternFill("solid", fgColor="FFF9C4")   # resaltado

FONT_TITULO  = Font(name="Arial", size=22, bold=True, color="FFFFFF")
FONT_HEADER  = Font(name="Arial", size=14, bold=True, color="FFFFFF")
FONT_BODY    = Font(name="Arial", size=13)
FONT_BOLD    = Font(name="Arial", size=13, bold=True)
FONT_TOTAL   = Font(name="Arial", size=15, bold=True, color="FFFFFF")
FONT_NOTA    = Font(name="Arial", size=11, italic=True, color="424242")

thin = Side(border_style="thin", color="A5D6A7")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

def money(cell): cell.number_format = '"$"#,##0'  # sin decimales para simplicidad

# ============ HOJA 1: RESUMEN PARA DON TITI ============
ws = wb.active
ws.title = "Resumen"

ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 18
ws.column_dimensions["C"].width = 18
ws.column_dimensions["D"].width = 20
ws.column_dimensions["E"].width = 15

# TÍTULO
ws.merge_cells("A1:E1")
ws["A1"] = "GANANCIAS Y GASTOS DE MAYO 2026"
ws["A1"].font = FONT_TITULO; ws["A1"].fill = VERDE_FUERTE
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 45

# Subtítulo
ws.merge_cells("A2:E2")
ws["A2"] = "Fuente: Soft Restaurant (ventas) + cuadro semanal Titi Burger (gastos)"
ws["A2"].font = FONT_NOTA
ws["A2"].alignment = Alignment(horizontal="center")

# --- Bloque grande: total del negocio ---
ws.row_dimensions[4].height = 28
ws.merge_cells("A4:E4")
ws["A4"] = "EL NEGOCIO EN MAYO"
ws["A4"].font = FONT_HEADER; ws["A4"].fill = VERDE_MEDIO
ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

ws["A5"] = "Vendimos"; ws["A5"].font = FONT_BOLD
ws["B5"] = VENTA_TOTAL; money(ws["B5"]); ws["B5"].font = FONT_BOLD

ws["A6"] = "Gastamos"; ws["A6"].font = FONT_BOLD
ws["B6"] = TOTAL_GASTO; money(ws["B6"]); ws["B6"].font = FONT_BOLD

ws["A7"] = "Ganamos"; ws["A7"].font = FONT_TOTAL; ws["A7"].fill = VERDE_CLARO
ws["B7"] = TOTAL_GANANCIA; money(ws["B7"]); ws["B7"].font = FONT_TOTAL
ws["B7"].fill = VERDE_CLARO if TOTAL_GANANCIA >= 0 else ROJO_SUAVE
ws.row_dimensions[7].height = 25

ws.merge_cells("C5:E7")
ws["C5"] = "* Esto NO incluye:\n  • Pagos personales de Don Titi\n  • Préstamos Santander (Andrónica)\n  • Gastos personales mezclados"
ws["C5"].font = FONT_NOTA
ws["C5"].alignment = Alignment(vertical="top", wrap_text=True)

# --- Tabla por sucursal ---
ws.row_dimensions[9].height = 28
ws.merge_cells("A9:E9")
ws["A9"] = "CADA SUCURSAL EN MAYO"
ws["A9"].font = FONT_HEADER; ws["A9"].fill = VERDE_MEDIO
ws["A9"].alignment = Alignment(horizontal="center", vertical="center")

# Headers
r = 10
headers = ["Sucursal", "Vendió", "Gastó", "Ganó / Perdió", "Empleados"]
for i, h in enumerate(headers, start=1):
    c = ws.cell(row=r, column=i, value=h)
    c.font = FONT_HEADER; c.fill = VERDE_MEDIO
    c.alignment = Alignment(horizontal="center")
ws.row_dimensions[r].height = 24

# Filas de sucursal, ordenadas por ganancia (mejor arriba)
sorted_sucs = sorted(RESUMEN.items(), key=lambda kv: -kv[1]["ganancia"])
for i, (nombre, d) in enumerate(sorted_sucs, start=r+1):
    fill_row = VERDE_MUY if i % 2 == 0 else None
    c = ws.cell(row=i, column=1, value=nombre); c.font = FONT_BOLD
    if fill_row: c.fill = fill_row
    c = ws.cell(row=i, column=2, value=d["venta"]); money(c); c.font = FONT_BODY
    if fill_row: c.fill = fill_row
    c = ws.cell(row=i, column=3, value=d["gasto"]); money(c); c.font = FONT_BODY
    if fill_row: c.fill = fill_row
    c = ws.cell(row=i, column=4, value=d["ganancia"]); money(c); c.font = FONT_BOLD
    c.fill = VERDE_CLARO if d["ganancia"] >= 0 else ROJO_SUAVE
    c = ws.cell(row=i, column=5, value=d["empleados"]); c.font = FONT_BODY
    c.alignment = Alignment(horizontal="center")
    if fill_row and d["ganancia"] < 0: pass  # el fill de la ganancia manda
    ws.row_dimensions[i].height = 22

# Fila total
r_tot = r + 1 + len(sorted_sucs)
c = ws.cell(row=r_tot, column=1, value="TOTAL"); c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
c = ws.cell(row=r_tot, column=2, value=VENTA_TOTAL); money(c); c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
c = ws.cell(row=r_tot, column=3, value=TOTAL_GASTO); money(c); c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
c = ws.cell(row=r_tot, column=4, value=TOTAL_GANANCIA); money(c); c.font = FONT_TOTAL
c.fill = VERDE_FUERTE
c = ws.cell(row=r_tot, column=5, value=sum(EMPLEADOS.values()))
c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
c.alignment = Alignment(horizontal="center")
ws.row_dimensions[r_tot].height = 28

# --- Notitas al final ---
r_nota = r_tot + 3
ws.merge_cells(f"A{r_nota}:E{r_nota}")
ws[f"A{r_nota}"] = "LO QUE SE VE DE UN GOLPE"
ws[f"A{r_nota}"].font = FONT_HEADER; ws[f"A{r_nota}"].fill = VERDE_MEDIO
ws[f"A{r_nota}"].alignment = Alignment(horizontal="center", vertical="center")

notas_finales = [
    "• FOVISSTE y MONTECARLO son las que sostienen el negocio (63% de la venta total).",
    "• Sucursales en rojo pierden dinero por rentas altas vs poca venta.",
    "• La ganancia del negocio ($" + f"{TOTAL_GANANCIA:,.0f}" + "/mes) NO alcanza para los gastos personales de Don Titi + préstamos Santander (~$500,000/mes).",
    "• Villas del Rey no tiene renta registrada en el cuadro semanal — confirmar con Nancy.",
    "• Se aplicó estimación: gastos globales (proveedores, gasolina, IMSS, etc.) se repartieron entre sucursales según cuánto vendió cada una.",
]
for i, n in enumerate(notas_finales, start=r_nota+1):
    ws.merge_cells(f"A{i}:E{i}")
    c = ws.cell(row=i, column=1, value=n)
    c.font = FONT_BODY
    c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[i].height = 22

# ============ HOJA 2: DETALLE POR SUCURSAL (para Staff/Nancy) ============
ws2 = wb.create_sheet("Detalle por sucursal")
ws2.column_dimensions["A"].width = 45
for col_letter in ["B","C","D","E","F","G","H"]:
    ws2.column_dimensions[col_letter].width = 22

SUCS = list(VENTAS.keys())
last_col = get_column_letter(len(SUCS)+2)

ws2.merge_cells(f"A1:{last_col}1")
ws2["A1"] = "DESGLOSE COMPLETO DE CADA SUCURSAL"
ws2["A1"].font = FONT_TITULO; ws2["A1"].fill = VERDE_FUERTE
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 40

# Headers de sucursal
r = 3
ws2.cell(row=r, column=1, value="").fill = VERDE_MEDIO
for i, s in enumerate(SUCS, start=2):
    c = ws2.cell(row=r, column=i, value=s)
    c.font = FONT_HEADER; c.fill = VERDE_MEDIO
    c.alignment = Alignment(horizontal="center")
c = ws2.cell(row=r, column=len(SUCS)+2, value="TOTAL")
c.font = FONT_HEADER; c.fill = VERDE_MEDIO
c.alignment = Alignment(horizontal="center")
ws2.row_dimensions[r].height = 26
r += 1

# Ventas
c = ws2.cell(row=r, column=1, value="LO QUE ENTRA (Ventas)"); c.font = FONT_BOLD; c.fill = VERDE_CLARO
for i in range(2, len(SUCS)+3):
    ws2.cell(row=r, column=i).fill = VERDE_CLARO
r += 1

ws2.cell(row=r, column=1, value="Venta bruta").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws2.cell(row=r, column=i, value=VENTAS[s]); money(c)
c = ws2.cell(row=r, column=len(SUCS)+2, value=VENTA_TOTAL); money(c); c.font = FONT_BOLD
r += 1

ws2.cell(row=r, column=1, value="Tickets").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    ws2.cell(row=r, column=i, value=TICKETS[s]).alignment = Alignment(horizontal="right")
ws2.cell(row=r, column=len(SUCS)+2, value=sum(TICKETS.values())).font = FONT_BOLD
r += 2

# Gastos de la sucursal (directos)
c = ws2.cell(row=r, column=1, value="LO QUE PAGA CADA SUCURSAL"); c.font = FONT_BOLD; c.fill = VERDE_CLARO
for i in range(2, len(SUCS)+3):
    ws2.cell(row=r, column=i).fill = VERDE_CLARO
r += 1

ws2.cell(row=r, column=1, value="Sueldos de los empleados").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws2.cell(row=r, column=i, value=NOMINA[s]); money(c)
c = ws2.cell(row=r, column=len(SUCS)+2, value=sum(NOMINA.values())); money(c); c.font = FONT_BOLD
r += 1

ws2.cell(row=r, column=1, value="Cuántos empleados").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    ws2.cell(row=r, column=i, value=EMPLEADOS[s]).alignment = Alignment(horizontal="right")
ws2.cell(row=r, column=len(SUCS)+2, value=sum(EMPLEADOS.values())).font = FONT_BOLD
r += 1

ws2.cell(row=r, column=1, value="Renta del local").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws2.cell(row=r, column=i, value=RENTAS[s]); money(c)
c = ws2.cell(row=r, column=len(SUCS)+2, value=sum(RENTAS.values())); money(c); c.font = FONT_BOLD
r += 1

ws2.cell(row=r, column=1, value="Servicios (luz, agua, gas)").font = FONT_BODY
for i, s in enumerate(SUCS, start=2):
    c = ws2.cell(row=r, column=i, value=SERVICIOS[s]); money(c)
c = ws2.cell(row=r, column=len(SUCS)+2, value=sum(SERVICIOS.values())); money(c); c.font = FONT_BOLD
r += 2

# Gastos globales prorrateados
c = ws2.cell(row=r, column=1, value="LO QUE SE REPARTE ENTRE TODAS (según venta)"); c.font = FONT_BOLD; c.fill = VERDE_CLARO
for i in range(2, len(SUCS)+3):
    ws2.cell(row=r, column=i).fill = VERDE_CLARO
r += 1

rubros_globales = [
    ("Comida (proveedores)", 200000),
    ("Refrescos y bebidas", 56000),
    ("Carbón", 58200),
    ("Gasolina", 151500),
    ("Seguro social (IMSS + Infonavit)", 142694),
    ("Fonacot (descuento empleados)", 41921),
    ("Sueldos de oficina/cocina/mensajero", 140596),
    ("Licencia del Soft Restaurant", 5561),
]
for nombre, monto in rubros_globales:
    ws2.cell(row=r, column=1, value=nombre).font = FONT_BODY
    for i, s in enumerate(SUCS, start=2):
        c = ws2.cell(row=r, column=i, value=monto * PCT[s]); money(c)
    c = ws2.cell(row=r, column=len(SUCS)+2, value=monto); money(c); c.font = FONT_BOLD
    r += 1

r += 1

# Totales
c = ws2.cell(row=r, column=1, value="GASTO TOTAL"); c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
for i, s in enumerate(SUCS, start=2):
    c = ws2.cell(row=r, column=i, value=RESUMEN[s]["gasto"]); money(c); c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
c = ws2.cell(row=r, column=len(SUCS)+2, value=TOTAL_GASTO); money(c); c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
r += 1

c = ws2.cell(row=r, column=1, value="GANANCIA / PÉRDIDA"); c.font = FONT_TOTAL; c.fill = VERDE_FUERTE
for i, s in enumerate(SUCS, start=2):
    v = RESUMEN[s]["ganancia"]
    c = ws2.cell(row=r, column=i, value=v); money(c); c.font = FONT_TOTAL
    c.fill = VERDE_CLARO if v >= 0 else ROJO_SUAVE
c = ws2.cell(row=r, column=len(SUCS)+2, value=TOTAL_GANANCIA); money(c); c.font = FONT_TOTAL
c.fill = VERDE_CLARO if TOTAL_GANANCIA >= 0 else ROJO_SUAVE
r += 1

# ============ HOJA 3: LEYENDA / SUPUESTOS SIMPLE ============
ws3 = wb.create_sheet("Cómo se calculó")
ws3.column_dimensions["A"].width = 38
ws3.column_dimensions["B"].width = 80

ws3.merge_cells("A1:B1")
ws3["A1"] = "DE DÓNDE SALIÓ CADA NÚMERO"
ws3["A1"].font = FONT_TITULO; ws3["A1"].fill = VERDE_FUERTE
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 40

items = [
    ("Ventas", "Del panel de Soft Restaurant Admin — reporte mensual de mayo con las 6 sucursales seleccionadas."),
    ("Empleados y sueldos", "Del catálogo de empleados de Titi Burger. Se sumó el sueldo semanal de cada uno y se multiplicó × 4.33 semanas."),
    ("Rentas", "De la hoja de gastos semanales de Titi Burger. Multiplicadas × 4.33 para el mes."),
    ("Luz, agua y gas", "De los recibos que se mandaron el 10 de julio. Bimestrales se dividieron entre 2 para dejar el mensual."),
    ("Comida (proveedores)", "Del cuadro semanal — Costalonorte, Bimbo, Bona (carne), Islas (pollo), Julián, Kowi, verduras QM, Parra."),
    ("Refrescos", "Coca, Peñafiel, Pepsi, Quevedo del cuadro semanal."),
    ("Carbón", "$13,400/semana del cuadro semanal."),
    ("Gasolina", "$35,000/semana del cuadro semanal."),
    ("IMSS + Infonavit", "De los recibos IMSS de junio 2026 (Lonchería $120,578 + Herrería $22,116)."),
    ("Fonacot", "$9,681 semanales de la retención a empleados afiliados."),
    ("Sueldos oficina/cocina", "9 empleados centrales (AM Jennifer, Carlos, David, Nancy Lizeth, Andrónica, Yazmín, Sandra, Susano) que no pertenecen a una sucursal específica."),
    ("Licencia Soft Restaurant", "$926.84 mensual × 6 sucursales (Cine Curto acaba de reactivarse)."),
    ("", ""),
    ("QUÉ NO SE INCLUYE EN ESTE CÁLCULO", ""),
    ("Nómina personal Don Titi ($260k/mes)", "Retiro semanal 'Otros $60,000' que normalmente va a pagar la American Express."),
    ("Préstamos Santander Andrónica ($137k/mes)", "Crédito simple $45,000 + cuenta revolvente $92,000. La revolvente está bloqueada por atrasos."),
    ("Gastos personales mezclados", "Hipoteca Titi, luz de la casa, gas de la casa, Liverpool, Carola, Arándano."),
    ("", ""),
    ("QUÉ FALTA CONFIRMAR", ""),
    ("Renta Villas del Rey", "No aparece en el cuadro semanal — pendiente confirmar con Nancy."),
    ("Recibos de Hacienda del Río y Cine Curto", "No hay recibos de luz/agua/gas para esas dos, así que quedaron en $0 (subestimado)."),
    ("Comisiones apps (Uber, Rappi, DiDi)", "Pendiente conseguir accesos con Elías para saber cuánto se lleva cada app."),
    ("Reparto real de proveedores", "Hoy se prorrateó por venta, pero cada sucursal usa distinta cantidad de comida."),
]
r = 3
for label, texto in items:
    c1 = ws3.cell(row=r, column=1, value=label); c1.font = FONT_BOLD
    c2 = ws3.cell(row=r, column=2, value=texto); c2.font = FONT_BODY
    c2.alignment = Alignment(wrap_text=True, vertical="top")
    if label and not texto:  # es sección
        c1.fill = VERDE_MEDIO; c2.fill = VERDE_MEDIO
        c1.font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws3.row_dimensions[r].height = 24
    r += 1

# Guardar
wb.save(OUT)
print(f"Excel guardado: {OUT}", flush=True)

# ============ ACTUALIZAR EN DRIVE (mismo ID) ============
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)

# Sobrescribir el archivo ya subido
FILE_ID = "11ov6JINhx_ESbWWT4lR8cM2mQq7ePyP7Ldvb---79qw"
media = MediaFileUpload(str(OUT),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)
d.files().update(fileId=FILE_ID, media_body=media).execute()
print(f"Actualizado en Drive.", flush=True)
print(f"Link: https://docs.google.com/spreadsheets/d/{FILE_ID}/edit", flush=True)
