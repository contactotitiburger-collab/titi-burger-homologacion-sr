#!/usr/bin/env python3
"""Catálogo de Gastos v2 — con columna Tipo (FIJO/VARIABLE/PERIÓDICO/EXTRAORDINARIO)."""
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
OUT = Path("/home/tito/.openclaw/data/Catálogo de Gastos - Titi Burger.xlsx")

# ============ DATOS ============
# (categoría, concepto, fuente, monto, frecuencia, TIPO, estado, notas)
RUBROS = [
    # ===== RENTAS =====
    ("RENTAS", "Renta Fovissste",              "Cuadro semanal",              0.00, "Mensual", "FIJO", "PENDIENTE", "Confirmar si tiene renta o es local propio"),
    ("RENTAS", "Renta Montecarlo",             "Cuadro semanal — Lunes 6",    9880.00, "Mensual", "FIJO", "CONFIRMADO", "Sucursal C"),
    ("RENTAS", "Renta San Marcos",             "Cuadro semanal — Lunes 6",   10890.00, "Mensual", "FIJO", "CONFIRMADO", "Sucursal E"),
    ("RENTAS", "Renta Hacienda del Río",       "Cuadro semanal — Martes 7",  16000.00, "Mensual", "FIJO", "CONFIRMADO", "Sucursal B"),
    ("RENTAS", "Renta Cine Curto",             "Cuadro semanal — Lunes 6",   16983.00, "Mensual", "FIJO", "CONFIRMADO", "La más alta de las sucursales"),
    ("RENTAS", "Renta Villas del Rey",         "N/A",                            0.00, "Mensual", "FIJO", "PENDIENTE", "No aparece en el cuadro — confirmar con Nancy"),
    ("RENTAS", "Renta Pachelli (almacén)",     "Cuadro semanal — Sábado 11",  8740.35, "Mensual", "FIJO", "CONFIRMADO", "Almacén, no sucursal"),
    # ===== SUELDOS =====
    ("SUELDOS", "Nómina sucursales (17 empleados)","Nómina semanal",             67687.44, "Semanal", "FIJO", "CONFIRMADO", "Sueldos base — empleados con sucursal asignada"),
    ("SUELDOS", "Nómina central (9 empleados)",    "Nómina semanal",             32428.63, "Semanal", "FIJO", "CONFIRMADO", "Jennifer, Carlos, David, Nancy Lizeth, Andrónica, Yazmín, Sandra, Susano"),
    ("SUELDOS", "Retiro personal Don Titi",        "Cuadro semanal — Lunes 6",   60000.00, "Semanal", "FIJO", "CONFIRMADO", "Usualmente American Express"),
    ("SUELDOS", "Abogado Luis",                    "Cuadro semanal — Lunes 6",    2500.00, "N/A",     "EXTRAORDINARIO", "CONFIRMADO", "Corregido por Don Titi: no es cada semana, es cuando hay que ir"),
    ("SUELDOS", "Juan Muñoz",                      "Cuadro semanal — Viernes 10", 2000.00, "N/A",     "EXTRAORDINARIO", "CONFIRMADO", "Corregido: mantenimiento no fijo"),
    ("SUELDOS", "Pascual Omar Domínguez",          "Cuadro semanal — Jueves 9",   3615.00, "N/A",     "PENDIENTE",      "PENDIENTE", "¿Quién es? No está en el catálogo de empleados"),
    ("SUELDOS", "Vacaciones Toro final",           "Cuadro semanal — Jueves 9",   3900.00, "Único",   "EXTRAORDINARIO", "PENDIENTE", "¿Pago único de vacaciones a 'Toro'?"),
    # ===== PROVEEDORES DE COMIDA =====
    ("PROVEEDORES", "Bona (carne, principal)",     "Cuadro semanal — Jueves 9",  30000.00, "Semanal", "VARIABLE", "CONFIRMADO", "Carne principal — depende de ventas"),
    ("PROVEEDORES", "Julián Romero (carne)",       "Cuadro semanal — Lunes 6",    5181.20, "Semanal", "VARIABLE", "CONFIRMADO", "Carne secundaria"),
    ("PROVEEDORES", "Islas (pollo)",               "Cuadro semanal",              7000.00, "Semanal", "VARIABLE", "CONFIRMADO", "Pollo"),
    ("PROVEEDORES", "Kowi (tocino) — pedido 1",    "Cuadro semanal — Jueves 9",   7660.00, "Semanal", "VARIABLE", "CONFIRMADO", "Tocino"),
    ("PROVEEDORES", "Kowi (tocino) — pedido 2",    "Cuadro semanal — Viernes 10", 3940.00, "Semanal", "VARIABLE", "CONFIRMADO", "Segundo pedido"),
    ("PROVEEDORES", "McCain (papas) — pedido 1",   "Cuadro semanal — Lunes 6",   12330.00, "Semanal", "VARIABLE", "CONFIRMADO", "Papas"),
    ("PROVEEDORES", "McCain (papas) — pedido 2",   "Cuadro semanal — Miércoles 8",2740.00, "Semanal", "VARIABLE", "CONFIRMADO", "Segundo pedido"),
    ("PROVEEDORES", "McCain (papas) — pedido 3",   "Cuadro semanal — Viernes 10", 2740.00, "Semanal", "VARIABLE", "CONFIRMADO", "Tercer pedido"),
    ("PROVEEDORES", "Bimbo (pan) — pedido 1",      "Cuadro semanal — Lunes 6",    8964.80, "Semanal", "VARIABLE", "CONFIRMADO", "Pan"),
    ("PROVEEDORES", "Bimbo (pan) — pedido 2",      "Cuadro semanal — Viernes 10", 8366.40, "Semanal", "VARIABLE", "CONFIRMADO", "Segundo pedido"),
    ("PROVEEDORES", "Costalonorte",                "Calendario Don Titi",        42000.00, "Semanal", "VARIABLE", "CONFIRMADO", "Paquete de insumos varios"),
    ("PROVEEDORES", "Alimentos Parra — pedido 1",  "Cuadro semanal — Martes 7",   5122.00, "PENDIENTE", "VARIABLE", "PENDIENTE", "Don Titi corrigió: NO es semanal. Falta saber cada cuánto y por qué es variable"),
    ("PROVEEDORES", "Alimentos Parra — pedido 2",  "Cuadro semanal — Miércoles 8",5122.00, "PENDIENTE", "VARIABLE", "PENDIENTE", "Igual — pendiente frecuencia real"),
    ("PROVEEDORES", "Verdura QM del Norte",        "Recibos varios",              5000.00, "Semanal", "VARIABLE", "CONFIRMADO", "Frutas y verduras — ~2 pedidos/semana"),
    ("PROVEEDORES", "Coca-Cola",                   "Cuadro semanal — Miércoles 8",5500.00, "Semanal", "VARIABLE", "CONFIRMADO", "Refrescos"),
    ("PROVEEDORES", "Pepsi",                       "Cuadro semanal — Miércoles 8",4080.00, "Semanal", "VARIABLE", "CONFIRMADO", "Refrescos"),
    ("PROVEEDORES", "Peñafiel",                    "Cuadro semanal — Martes 7",   3500.00, "Semanal", "VARIABLE", "CONFIRMADO", "Refrescos"),
    ("PROVEEDORES", "Quevedo — pedido 1",          "Cuadro semanal — Miércoles 8",5495.10, "Semanal", "VARIABLE", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Quevedo — pedido 2",          "Cuadro semanal — Viernes 10", 7195.00, "Semanal", "VARIABLE", "PENDIENTE", ""),
    ("PROVEEDORES", "Botellas",                    "Cuadro semanal — Martes 7",   7619.40, "Semanal", "VARIABLE", "PENDIENTE", "Envases"),
    ("PROVEEDORES", "Cascos (envases)",            "Cuadro semanal — Lunes 6",    3000.00, "Semanal", "VARIABLE", "PENDIENTE", ""),
    ("PROVEEDORES", "Hielos",                      "Cuadro semanal — Sábado 11",   800.00, "Semanal", "VARIABLE", "CONFIRMADO", ""),
    ("PROVEEDORES", "Agua de beber (garrafón)",    "Cuadro semanal — Viernes 10",  800.00, "Semanal", "VARIABLE", "PENDIENTE", "¿Es garrafón semanal?"),
    ("PROVEEDORES", "Grasa Dina",                  "Cuadro semanal — Martes 7",   1200.00, "Semanal", "VARIABLE", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Jofa",                        "Cuadro semanal — Viernes 10", 1514.83, "PENDIENTE", "PENDIENTE", "PENDIENTE", "Confirmar qué es y frecuencia"),
    ("PROVEEDORES", "Carbón",                      "Cuadro semanal — Miércoles 8",13453.20,"Semanal", "VARIABLE", "CONFIRMADO", "Insumo asado"),
    ("PROVEEDORES", "Compras (genérico)",          "Cuadro semanal — Lunes 6",    6189.00, "PENDIENTE", "PENDIENTE", "PENDIENTE", "¿Qué compras son? — abrir concepto"),
    ("PROVEEDORES", "Suza Curto",                  "Cuadro semanal — Lunes 6",    4854.14, "PENDIENTE", "PENDIENTE", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Rebajan",                     "Cuadro semanal — Miércoles 8",6028.00, "PENDIENTE", "PENDIENTE", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Hereberos (pago 1)",          "Cuadro semanal — Martes 7",   1432.00, "PENDIENTE", "PENDIENTE", "PENDIENTE", "Aparece 3 veces con montos distintos"),
    ("PROVEEDORES", "Hereberos (pago 2)",          "Cuadro semanal — Miércoles 8",4352.20, "PENDIENTE", "PENDIENTE", "PENDIENTE", ""),
    ("PROVEEDORES", "Hereberos (pago 3)",          "Cuadro semanal — Sábado 11",  4000.00, "PENDIENTE", "PENDIENTE", "PENDIENTE", ""),
    # ===== SERVICIOS =====
    ("SERVICIOS", "Luz CFE — Fovissste (2 medidores)","Recibos CFE",             19500.00, "Bimestral","PERIÓDICO", "CONFIRMADO", "2 recibos bimestrales"),
    ("SERVICIOS", "Luz CFE — Montecarlo (3 medidores)","Recibos CFE",             3301.00, "Bimestral","PERIÓDICO", "CONFIRMADO", "3 recibos"),
    ("SERVICIOS", "Luz CFE — San Marcos",             "Recibo CFE",                741.00, "Bimestral","PERIÓDICO", "CONFIRMADO", ""),
    ("SERVICIOS", "Luz CFE — Montecarlo (viernes)",   "Cuadro semanal — Viernes 10", 2050.00,"Bimestral","PERIÓDICO", "CONFIRMADO", "Duplica los de arriba — mismo recibo"),
    ("SERVICIOS", "Agua CESPM — Fovissste",           "Recibo CESPM",             5436.00, "Mensual", "FIJO", "CONFIRMADO", ""),
    ("SERVICIOS", "Agua CESPM — Montecarlo",          "Recibo CESPM",             6849.00, "Mensual", "FIJO", "CONFIRMADO", ""),
    ("SERVICIOS", "Agua CESPM — San Marcos",          "Recibo CESPM",              804.00, "Mensual", "FIJO", "CONFIRMADO", ""),
    ("SERVICIOS", "Agua CESPM — Villas del Rey",      "Recibo CESPM",              288.00, "Mensual", "FIJO", "CONFIRMADO", ""),
    ("SERVICIOS", "Gas Ecogas — Fovissste",           "Recibo Ecogas",            5649.00, "Bimestral","PERIÓDICO", "CONFIRMADO", ""),
    ("SERVICIOS", "Gas Ecogas — Montecarlo",          "Recibo Ecogas",             248.00, "Bimestral","PERIÓDICO", "CONFIRMADO", ""),
    ("SERVICIOS", "Gas Ecogas — Villas del Rey",      "Recibo Ecogas",             759.00, "Bimestral","PERIÓDICO", "CONFIRMADO", ""),
    ("SERVICIOS", "Internet Total Play",              "Cuadro semanal — Lunes 6",  580.00, "Mensual", "FIJO", "PENDIENTE", "Confirmar frecuencia"),
    ("SERVICIOS", "Licencia Soft Restaurant (6 suc)", "Facturas Backup Soluciones",5561.04,"Mensual", "FIJO", "CONFIRMADO", "6 × $926.84"),
    ("SERVICIOS", "Basura Omar Domínguez",            "Cuadro semanal — Miércoles 8",4088.00,"PENDIENTE","PERIÓDICO", "PENDIENTE", "Recolección — puede ser semanal o mensual"),
    ("SERVICIOS", "Canirac Fovissste",                "Cuadro semanal — Miércoles 8",2700.00,"PENDIENTE","PERIÓDICO", "PENDIENTE", "Cámara restauranteros — puede ser anual"),
    ("SERVICIOS", "Gasolina",                         "Cuadro semanal",           35000.00, "Semanal", "PERIÓDICO", "CONFIRMADO", "Mensajero + rancho"),
    # ===== IMPUESTOS Y CRÉDITOS =====
    ("IMPUESTOS Y CRÉDITOS", "IMSS + Infonavit Lonchería (25 cotiz.)", "Recibo IMSS junio 2026",120578.00,"Mensual","FIJO", "CONFIRMADO", "Vence 20-jul-2026"),
    ("IMPUESTOS Y CRÉDITOS", "IMSS + Infonavit Herrería (3 cotiz.)",    "Recibo IMSS junio 2026", 22116.00,"Mensual","FIJO", "CONFIRMADO", "Vence 20-jul-2026"),
    ("IMPUESTOS Y CRÉDITOS", "Fonacot (retención empleados)",           "Cuadro semanal — Lunes 6",9681.55,"Semanal","FIJO", "CONFIRMADO", ""),
    ("IMPUESTOS Y CRÉDITOS", "Santander Andrónica — crédito simple",     "Cuadro semanal — Martes 7",45000.00,"Mensual","FIJO", "CONFIRMADO", ""),
    ("IMPUESTOS Y CRÉDITOS", "Santander Andrónica — cuenta revolvente",  "Extracto",              92000.00, "Mensual","FIJO", "CONFIRMADO", "Bloqueada por atrasos"),
    # ===== GASTOS PERSONALES DON TITI =====
    ("GASTOS PERSONALES", "Hipoteca Titi",                "Cuadro semanal — Lunes 6",    9280.00, "Mensual", "FIJO", "PENDIENTE", "Confirmar frecuencia"),
    ("GASTOS PERSONALES", "Luz CFE — Casa Titi",          "Cuadro semanal — Sábado 11",  1258.00, "Bimestral","PERIÓDICO", "CONFIRMADO", ""),
    ("GASTOS PERSONALES", "Gas Ecogas — Casa Titi",       "Cuadro semanal — Sábado 11",   235.00, "Bimestral","PERIÓDICO", "CONFIRMADO", ""),
    ("GASTOS PERSONALES", "Liverpool Titi",               "Cuadro semanal — Sábado 11",  1050.00, "Mensual", "FIJO", "PENDIENTE", "Plan Liverpool personal"),
    ("GASTOS PERSONALES", "Carola (pago 1)",              "Cuadro semanal — Lunes 6",    2000.00, "PENDIENTE","PENDIENTE", "PENDIENTE", "¿Qué es Carola? ¿es esposa/mesada?"),
    ("GASTOS PERSONALES", "Carola (pago 2)",              "Cuadro semanal — Sábado 11",  1200.00, "PENDIENTE","PENDIENTE", "PENDIENTE", "Aparece 2 veces"),
    ("GASTOS PERSONALES", "Arándano",                     "Cuadro semanal — Lunes 6",   13000.00, "PENDIENTE","PENDIENTE", "PENDIENTE", "¿Qué es?"),
    # ===== OTROS =====
    ("OTROS", "Lonas (publicidad)",                       "Cuadro semanal — Lunes 6",    1800.00, "Único",   "EXTRAORDINARIO", "PENDIENTE", "Publicidad — ¿cada cuánto?"),
    ("OTROS", "Mantenimiento (Casa Acero, Carpintero, MJ)","Recibos varios",             3000.00, "Mensual", "PERIÓDICO", "CONFIRMADO", "Estimación mensual promedio"),
    ("OTROS", "Uniformes El Halcón",                      "Recibo El Halcón",            1335.00, "Único",   "EXTRAORDINARIO", "CONFIRMADO", "Compra ocasional"),
]

# ============ EXCEL ============
wb = Workbook()

VERDE_TITLE   = PatternFill("solid", fgColor="1B5E20")
VERDE_HEADER  = PatternFill("solid", fgColor="388E3C")
VERDE_SUB     = PatternFill("solid", fgColor="A5D6A7")
VERDE_MUY     = PatternFill("solid", fgColor="E8F5E9")
AMARILLO      = PatternFill("solid", fgColor="FFF9C4")
GRIS_ALT      = PatternFill("solid", fgColor="F5F5F5")

# Colores por Tipo (para la columna Tipo)
COLOR_TIPO = {
    "FIJO":            PatternFill("solid", fgColor="BBDEFB"),  # azul claro
    "VARIABLE":        PatternFill("solid", fgColor="FFE0B2"),  # naranja claro
    "PERIÓDICO":       PatternFill("solid", fgColor="D1C4E9"),  # morado claro
    "EXTRAORDINARIO":  PatternFill("solid", fgColor="FFCDD2"),  # rojo claro
    "PENDIENTE":       PatternFill("solid", fgColor="FFF9C4"),  # amarillo
}

FT_TITLE_XL = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
FT_SUB      = Font(name="Calibri", size=11, italic=True, color="424242")
FT_HEAD     = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
FT_CAT      = Font(name="Calibri", size=12, bold=True, color="1B5E20")
FT_BODY     = Font(name="Calibri", size=10)
FT_BOLD     = Font(name="Calibri", size=10, bold=True)
FT_LEG      = Font(name="Calibri", size=9, color="424242")

thin = Side(border_style="thin", color="9E9E9E")
medium = Side(border_style="medium", color="1B5E20")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

def money(cell): cell.number_format = '"$"#,##0.00'

ws = wb.active
ws.title = "Catálogo de Gastos"

# Anchos (8 columnas)
ws.column_dimensions["A"].width = 42   # Concepto
ws.column_dimensions["B"].width = 26   # Fuente
ws.column_dimensions["C"].width = 15   # Monto
ws.column_dimensions["D"].width = 12   # Frecuencia
ws.column_dimensions["E"].width = 16   # Monto mensual
ws.column_dimensions["F"].width = 16   # Tipo
ws.column_dimensions["G"].width = 13   # Estado
ws.column_dimensions["H"].width = 45   # Notas

# Título
ws.merge_cells("A1:H1")
ws["A1"] = "CATÁLOGO DE GASTOS — TITI BURGER"
ws["A1"].font = FT_TITLE_XL; ws["A1"].fill = VERDE_TITLE
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 32

# Subtítulo
ws.merge_cells("A2:H2")
ws["A2"] = "Todos los rubros con su tipo y monto mensualizado — Consolidado 10 de julio de 2026"
ws["A2"].font = FT_SUB
ws["A2"].alignment = Alignment(horizontal="center")
ws.row_dimensions[2].height = 20

# Leyenda de tipos
ws.merge_cells("A3:H3")
ws["A3"] = ("FIJO = mismo monto cada mes (renta, préstamos, IMSS)  •  "
            "VARIABLE = depende de la venta (comida, refrescos)  •  "
            "PERIÓDICO = repite pero no exacto (servicios, mantenimiento)  •  "
            "EXTRAORDINARIO = ocasional, no recurrente (lonas, uniformes)")
ws["A3"].font = FT_LEG
ws["A3"].alignment = Alignment(horizontal="center", wrap_text=True)
ws.row_dimensions[3].height = 30

# Headers fila 5
headers = ["Concepto", "Fuente / día en cuadro", "Monto que aparece", "Frecuencia",
           "Monto mensual", "Tipo", "Estado", "Notas"]
for i, h in enumerate(headers, start=1):
    c = ws.cell(row=5, column=i, value=h)
    c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[5].height = 30

ORDEN_CATS = ["RENTAS", "SUELDOS", "PROVEEDORES", "SERVICIOS",
              "IMPUESTOS Y CRÉDITOS", "GASTOS PERSONALES", "OTROS"]
rubros_ordenados = sorted(RUBROS, key=lambda x: (ORDEN_CATS.index(x[0]), x[1]))

r = 6
current_cat = None
for cat, concepto, fuente, monto, freq, tipo, estado, notas in rubros_ordenados:
    if cat != current_cat:
        ws.merge_cells(f"A{r}:H{r}")
        c = ws.cell(row=r, column=1, value=cat)
        c.font = FT_CAT; c.fill = VERDE_SUB
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[r].height = 24
        current_cat = cat
        r += 1

    ws.cell(row=r, column=1, value=concepto).font = FT_BODY
    ws.cell(row=r, column=2, value=fuente).font = FT_BODY
    c = ws.cell(row=r, column=3, value=monto); money(c); c.font = FT_BODY
    ws.cell(row=r, column=4, value=freq).font = FT_BODY
    ws.cell(row=r, column=4).alignment = Alignment(horizontal="center")

    # Fórmula monto mensual
    if freq == "Semanal":
        formula = f"=C{r}*4.33"
    elif freq == "Mensual":
        formula = f"=C{r}"
    elif freq == "Bimestral":
        formula = f"=C{r}/2"
    elif freq == "Único":
        formula = f"=C{r}/12"
    elif freq == "N/A":
        formula = 0
    else:  # PENDIENTE
        formula = 0
    c = ws.cell(row=r, column=5, value=formula); money(c); c.font = FT_BOLD

    # Tipo con color
    c = ws.cell(row=r, column=6, value=tipo)
    c.font = FT_BOLD
    c.alignment = Alignment(horizontal="center")
    if tipo in COLOR_TIPO:
        c.fill = COLOR_TIPO[tipo]

    # Estado
    c = ws.cell(row=r, column=7, value=estado)
    c.font = FT_BOLD
    c.alignment = Alignment(horizontal="center")
    if estado == "CONFIRMADO":
        c.fill = VERDE_MUY
    else:
        c.fill = AMARILLO

    c = ws.cell(row=r, column=8, value=notas); c.font = FT_BODY
    c.alignment = Alignment(wrap_text=True, vertical="top")

    for col in range(1, 9):
        ws.cell(row=r, column=col).border = BOX
    ws.row_dimensions[r].height = 22
    r += 1

# Total general al final
ws.merge_cells(f"A{r}:D{r}")
c = ws.cell(row=r, column=1, value="TOTAL MENSUAL (suma de todos los rubros)")
c.font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
c.fill = VERDE_TITLE
c.alignment = Alignment(horizontal="right", vertical="center", indent=1)

c = ws.cell(row=r, column=5, value=f"=SUM(E6:E{r-1})")
money(c); c.font = Font(name="Calibri", size=12, bold=True, color="FFFFFF"); c.fill = VERDE_TITLE
for col in [6, 7, 8]:
    ws.cell(row=r, column=col).fill = VERDE_TITLE
ws.row_dimensions[r].height = 28

for col in range(1, 9):
    ws.cell(row=r, column=col).border = Border(left=medium, right=medium, top=medium, bottom=medium)

# Totales por tipo (fila siguiente, resumen)
r += 2
ws.merge_cells(f"A{r}:H{r}")
c = ws.cell(row=r, column=1, value="RESUMEN POR TIPO")
c.font = FT_CAT; c.fill = VERDE_SUB
c.alignment = Alignment(horizontal="center")
r += 1

# Headers resumen
for i, h in enumerate(["Tipo", "Total mensual", "Cómo se comporta"], start=1):
    c = ws.cell(row=r, column=i*2-1 if i<=2 else 5, value=h)
    c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center")
# Simplifico: uso cols A, B, C-H
c = ws.cell(row=r, column=1, value="Tipo"); c.font = FT_HEAD; c.fill = VERDE_HEADER
c.alignment = Alignment(horizontal="center")
c = ws.cell(row=r, column=2, value="Total mensual"); c.font = FT_HEAD; c.fill = VERDE_HEADER
c.alignment = Alignment(horizontal="center")
ws.merge_cells(f"C{r}:H{r}")
c = ws.cell(row=r, column=3, value="Cómo se comporta"); c.font = FT_HEAD; c.fill = VERDE_HEADER
c.alignment = Alignment(horizontal="center")
r += 1

tipos_info = [
    ("FIJO", "Cada mes se paga lo mismo — presupuestable con monto duro"),
    ("VARIABLE", "Depende de la venta — se calcula como % de ventas"),
    ("PERIÓDICO", "Repite pero no exacto cada mes — se usa promedio"),
    ("EXTRAORDINARIO", "Ocasional, no todos los meses — va a reserva de imprevistos"),
    ("PENDIENTE", "Aún no clasificado — se necesita más info"),
]
# fórmula SUMIF por Tipo (col F es Tipo)
DATA_START = 6
DATA_END = r - 4
for tipo, desc in tipos_info:
    c = ws.cell(row=r, column=1, value=tipo)
    c.font = FT_BOLD; c.fill = COLOR_TIPO.get(tipo, GRIS_ALT)
    c.alignment = Alignment(horizontal="center")
    c = ws.cell(row=r, column=2, value=f'=SUMIF(F{DATA_START}:F{DATA_END},"{tipo}",E{DATA_START}:E{DATA_END})')
    money(c); c.font = FT_BOLD
    ws.merge_cells(f"C{r}:H{r}")
    c = ws.cell(row=r, column=3, value=desc); c.font = FT_BODY
    c.alignment = Alignment(horizontal="left", indent=1, vertical="center")
    for col in range(1, 9):
        ws.cell(row=r, column=col).border = BOX
    ws.row_dimensions[r].height = 22
    r += 1

ws.freeze_panes = "A6"

wb.save(OUT)
print(f"Guardado: {OUT}", flush=True)

# Actualizar en Drive
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)
FILE_ID = "1h9s0OMHQui-pvL71_N0MEYpA9lkivZv1rM8nhaw0tKE"
media = MediaFileUpload(str(OUT),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)
d.files().update(fileId=FILE_ID, media_body=media).execute()
print(f"Actualizado en Drive.", flush=True)
print(f"Link: https://docs.google.com/spreadsheets/d/{FILE_ID}/edit", flush=True)
