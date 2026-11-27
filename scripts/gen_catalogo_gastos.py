#!/usr/bin/env python3
"""Catálogo de Gastos — Titi Burger. Formal, presentable, con todos los rubros identificados."""
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
# Estructura: (categoría, concepto, día/fuente, monto, frecuencia, estado, notas)
# Categorías: RENTAS · SUELDOS · PROVEEDORES · SERVICIOS · IMPUESTOS Y CRÉDITOS · GASTOS PERSONALES · OTROS

RUBROS = [
    # ===== RENTAS =====
    ("RENTAS", "Renta Fovissste",                  "Cuadro semanal",   0.00,       "Mensual",   "PENDIENTE",  "Confirmar con Nancy si tiene renta o es local propio"),
    ("RENTAS", "Renta Montecarlo",                 "Cuadro semanal — Lunes 6",  9880.00, "Mensual", "CONFIRMADO", "Sucursal C"),
    ("RENTAS", "Renta San Marcos",                 "Cuadro semanal — Lunes 6", 10890.00, "Mensual", "CONFIRMADO", "Sucursal E"),
    ("RENTAS", "Renta Hacienda del Río",           "Cuadro semanal — Martes 7", 16000.00, "Mensual", "CONFIRMADO", "Sucursal B"),
    ("RENTAS", "Renta Cine Curto",                 "Cuadro semanal — Lunes 6", 16983.00, "Mensual", "CONFIRMADO", "La renta más alta de las sucursales"),
    ("RENTAS", "Renta Villas del Rey",             "N/A",              0.00,       "Mensual",   "PENDIENTE",  "No aparece en el cuadro — confirmar con Nancy"),
    ("RENTAS", "Renta Pachelli (almacén)",         "Cuadro semanal — Sábado 11", 8740.35, "Mensual", "CONFIRMADO", "Almacén, no sucursal"),
    # ===== SUELDOS =====
    ("SUELDOS", "Nómina sucursales (17 empleados)","Nómina semanal",  67687.44,    "Semanal",   "CONFIRMADO", "Empleados con sucursal asignada"),
    ("SUELDOS", "Nómina central (9 empleados)",    "Nómina semanal",  32428.63,    "Semanal",   "CONFIRMADO", "Jennifer AM, Carlos, David, Nancy Lizeth, Andrónica, Yazmín, Sandra, Susano"),
    ("SUELDOS", "Retiro personal Don Titi ('Otros gastos')", "Cuadro semanal — Lunes 6", 60000.00, "Semanal", "CONFIRMADO", "Usualmente destinado a American Express"),
    ("SUELDOS", "Abogado Luis",                    "Cuadro semanal — Lunes 6",  2500.00, "Semanal", "PENDIENTE", "¿Es igualmente cada semana o mensual?"),
    ("SUELDOS", "Pascual Omar Domínguez",          "Cuadro semanal — Jueves 9", 3615.00, "Semanal", "PENDIENTE", "¿Empleado extra o pago único?"),
    ("SUELDOS", "Juan Muñoz",                      "Cuadro semanal — Viernes 10", 2000.00, "Semanal", "PENDIENTE", "¿Empleado extra o pago único?"),
    ("SUELDOS", "Vacaciones Toro final",           "Cuadro semanal — Jueves 9", 3900.00, "Único",    "PENDIENTE", "¿Pago único de vacaciones?"),
    # ===== PROVEEDORES DE COMIDA =====
    ("PROVEEDORES", "Bona (carne, proveedor principal)", "Cuadro semanal — Jueves 9", 30000.00, "Semanal", "CONFIRMADO", "Carne principal"),
    ("PROVEEDORES", "Julián Romero (carne secundaria)",  "Cuadro semanal — Lunes 6",  5181.20, "Semanal", "CONFIRMADO", "Carne complementaria"),
    ("PROVEEDORES", "Islas (pollo)",                     "Cuadro semanal",           7000.00, "Semanal", "CONFIRMADO", "Pollo — ~$7-14k semanal"),
    ("PROVEEDORES", "Kowi (tocino) — pedido 1",          "Cuadro semanal — Jueves 9", 7660.00, "Semanal", "CONFIRMADO", "Tocino"),
    ("PROVEEDORES", "Kowi (tocino) — pedido 2",          "Cuadro semanal — Viernes 10", 3940.00, "Semanal", "CONFIRMADO", "Segundo pedido en la semana"),
    ("PROVEEDORES", "McCain (papas) — pedido 1",         "Cuadro semanal — Lunes 6", 12330.00, "Semanal", "CONFIRMADO", "Papas"),
    ("PROVEEDORES", "McCain (papas) — pedido 2",         "Cuadro semanal — Miércoles 8", 2740.00, "Semanal", "CONFIRMADO", "Segundo pedido"),
    ("PROVEEDORES", "McCain (papas) — pedido 3",         "Cuadro semanal — Viernes 10", 2740.00, "Semanal", "CONFIRMADO", "Tercer pedido"),
    ("PROVEEDORES", "Bimbo (pan) — pedido 1",            "Cuadro semanal — Lunes 6",  8964.80, "Semanal", "CONFIRMADO", "Pan"),
    ("PROVEEDORES", "Bimbo (pan) — pedido 2",            "Cuadro semanal — Viernes 10", 8366.40, "Semanal", "CONFIRMADO", "Segundo pedido"),
    ("PROVEEDORES", "Costalonorte",                      "Calendario Don Titi",     42000.00, "Semanal", "CONFIRMADO", "Cae los lunes 29 según calendario"),
    ("PROVEEDORES", "Alimentos Parra — pedido 1",        "Cuadro semanal — Martes 7", 5122.00, "Semanal", "CONFIRMADO", "Verduras"),
    ("PROVEEDORES", "Alimentos Parra — pedido 2",        "Cuadro semanal — Miércoles 8", 5122.00, "Semanal", "CONFIRMADO", "Segundo pedido"),
    ("PROVEEDORES", "Verdura QM del Norte",              "Recibos varios",           5000.00, "Semanal", "CONFIRMADO", "Frutas y verduras — ~2 pedidos/semana"),
    ("PROVEEDORES", "Coca-Cola",                         "Cuadro semanal — Miércoles 8", 5500.00, "Semanal", "CONFIRMADO", "Refrescos"),
    ("PROVEEDORES", "Pepsi",                             "Cuadro semanal — Miércoles 8", 4080.00, "Semanal", "CONFIRMADO", "Refrescos"),
    ("PROVEEDORES", "Peñafiel",                          "Cuadro semanal — Martes 7",  3500.00, "Semanal", "CONFIRMADO", "Refrescos"),
    ("PROVEEDORES", "Quevedo — pedido 1",                "Cuadro semanal — Miércoles 8", 5495.10, "Semanal", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Quevedo — pedido 2",                "Cuadro semanal — Viernes 10", 7195.00, "Semanal", "PENDIENTE", ""),
    ("PROVEEDORES", "Botellas",                          "Cuadro semanal — Martes 7",  7619.40, "Semanal", "PENDIENTE", "Envases"),
    ("PROVEEDORES", "Cascos (envases refresco)",         "Cuadro semanal — Lunes 6",   3000.00, "Semanal", "PENDIENTE", ""),
    ("PROVEEDORES", "Hielos",                            "Cuadro semanal — Sábado 11", 800.00,  "Semanal", "CONFIRMADO", ""),
    ("PROVEEDORES", "Agua de beber (garrafón)",          "Cuadro semanal — Viernes 10", 800.00, "Semanal", "PENDIENTE", "¿Es garrafón semanal?"),
    ("PROVEEDORES", "Grasa Dina",                        "Cuadro semanal — Martes 7",  1200.00, "Semanal", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Jofa",                              "Cuadro semanal — Viernes 10", 1514.83, "Semanal", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Carbón",                            "Cuadro semanal — Miércoles 8", 13453.20, "Semanal", "CONFIRMADO", "Insumo para asado"),
    ("PROVEEDORES", "Compras (concepto genérico)",       "Cuadro semanal — Lunes 6",   6189.00, "Semanal", "PENDIENTE", "¿Qué es? — concepto genérico"),
    ("PROVEEDORES", "Suza Curto",                        "Cuadro semanal — Lunes 6",   4854.14, "Semanal", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Rebajan",                           "Cuadro semanal — Miércoles 8", 6028.00, "Semanal", "PENDIENTE", "Confirmar qué es"),
    ("PROVEEDORES", "Hereberos (pago 1)",                "Cuadro semanal — Martes 7",  1432.00, "Semanal", "PENDIENTE", "Aparece 3 veces con montos distintos"),
    ("PROVEEDORES", "Hereberos (pago 2)",                "Cuadro semanal — Miércoles 8", 4352.20, "Semanal", "PENDIENTE", ""),
    ("PROVEEDORES", "Hereberos (pago 3)",                "Cuadro semanal — Sábado 11", 4000.00, "Semanal", "PENDIENTE", ""),
    # ===== SERVICIOS =====
    ("SERVICIOS", "Luz CFE — Fovissste (2 medidores)",   "Recibos CFE",             19500.00, "Bimestral", "CONFIRMADO", "Suma de 2 recibos: Jesús López Collada + Jesús García"),
    ("SERVICIOS", "Luz CFE — Montecarlo (3 medidores)",  "Recibos CFE",              3301.00, "Bimestral", "CONFIRMADO", "3 recibos"),
    ("SERVICIOS", "Luz CFE — San Marcos",                "Recibo CFE",                741.00, "Bimestral", "CONFIRMADO", ""),
    ("SERVICIOS", "Luz CFE — Montecarlo (viernes)",      "Cuadro semanal — Viernes 10", 2050.00, "Bimestral", "CONFIRMADO", "Duplica los de arriba — mismo recibo"),
    ("SERVICIOS", "Agua CESPM — Fovissste",              "Recibo CESPM",             5436.00, "Mensual",   "CONFIRMADO", ""),
    ("SERVICIOS", "Agua CESPM — Montecarlo",             "Recibo CESPM",             6849.00, "Mensual",   "CONFIRMADO", ""),
    ("SERVICIOS", "Agua CESPM — San Marcos",             "Recibo CESPM",              804.00, "Mensual",   "CONFIRMADO", ""),
    ("SERVICIOS", "Agua CESPM — Villas del Rey",         "Recibo CESPM",              288.00, "Mensual",   "CONFIRMADO", ""),
    ("SERVICIOS", "Gas Ecogas — Fovissste",              "Recibo Ecogas",            5649.00, "Bimestral", "CONFIRMADO", ""),
    ("SERVICIOS", "Gas Ecogas — Montecarlo",             "Recibo Ecogas",             248.00, "Bimestral", "CONFIRMADO", ""),
    ("SERVICIOS", "Gas Ecogas — Villas del Rey",         "Recibo Ecogas",             759.00, "Bimestral", "CONFIRMADO", ""),
    ("SERVICIOS", "Internet Total Play",                 "Cuadro semanal — Lunes 6",  580.00, "Mensual",   "PENDIENTE", "Confirmar si es mensual"),
    ("SERVICIOS", "Licencia Soft Restaurant (6 sucursales)", "Facturas Backup Soluciones", 5561.04, "Mensual", "CONFIRMADO", "6 × $926.84"),
    ("SERVICIOS", "Basura Omar Domínguez",               "Cuadro semanal — Miércoles 8", 4088.00, "Semanal", "PENDIENTE", "Recolección — puede ser mensual"),
    ("SERVICIOS", "Canirac Fovissste",                   "Cuadro semanal — Miércoles 8", 2700.00, "Semanal", "PENDIENTE", "Cámara restauranteros — puede ser mensual"),
    ("SERVICIOS", "Gasolina",                            "Cuadro semanal",           35000.00, "Semanal",   "CONFIRMADO", "Mensajero + rancho"),
    # ===== IMPUESTOS Y CRÉDITOS =====
    ("IMPUESTOS Y CRÉDITOS", "IMSS + Infonavit (Lonchería, 25 cotizantes)", "Recibo IMSS junio 2026", 120578.00, "Mensual", "CONFIRMADO", "Vence 20-jul-2026"),
    ("IMPUESTOS Y CRÉDITOS", "IMSS + Infonavit (Herrería, 3 cotizantes)",    "Recibo IMSS junio 2026",  22116.00, "Mensual", "CONFIRMADO", "Vence 20-jul-2026"),
    ("IMPUESTOS Y CRÉDITOS", "Fonacot (retención)",                          "Cuadro semanal — Lunes 6",  9681.55, "Semanal", "CONFIRMADO", "Retención a empleados"),
    ("IMPUESTOS Y CRÉDITOS", "Santander Andrónica — crédito simple",          "Cuadro semanal — Martes 7", 45000.00, "Mensual", "CONFIRMADO", "Préstamo bancario"),
    ("IMPUESTOS Y CRÉDITOS", "Santander Andrónica — cuenta revolvente",       "Extracto",              92000.00, "Mensual", "CONFIRMADO", "Bloqueada por atrasos"),
    # ===== GASTOS PERSONALES DON TITI =====
    ("GASTOS PERSONALES", "Hipoteca Titi",                   "Cuadro semanal — Lunes 6",  9280.00, "Mensual", "PENDIENTE", "Confirmar frecuencia"),
    ("GASTOS PERSONALES", "Luz CFE — Casa Titi",             "Cuadro semanal — Sábado 11", 1258.00, "Bimestral", "CONFIRMADO", "Recibo CFE de casa"),
    ("GASTOS PERSONALES", "Gas Ecogas — Casa Titi",          "Cuadro semanal — Sábado 11",  235.00, "Bimestral", "CONFIRMADO", "Recibo Ecogas de casa"),
    ("GASTOS PERSONALES", "Liverpool Titi",                  "Cuadro semanal — Sábado 11", 1050.00, "Mensual",   "PENDIENTE", "Plan Liverpool personal"),
    ("GASTOS PERSONALES", "Carola (pago 1)",                 "Cuadro semanal — Lunes 6",  2000.00, "Semanal",   "PENDIENTE", "¿Es esposa? ¿pago recurrente?"),
    ("GASTOS PERSONALES", "Carola (pago 2)",                 "Cuadro semanal — Sábado 11", 1200.00, "Semanal",   "PENDIENTE", "Aparece 2 veces en la semana"),
    ("GASTOS PERSONALES", "Arándano",                        "Cuadro semanal — Lunes 6", 13000.00, "Semanal",   "PENDIENTE", "¿Pago familiar? ¿proveedor personal?"),
    # ===== OTROS =====
    ("OTROS", "Lonas (publicidad)",                          "Cuadro semanal — Lunes 6", 1800.00, "Único",     "PENDIENTE", "¿Es único o recurrente?"),
    ("OTROS", "Mantenimiento (Casa Acero, Carpintero, MJ)",  "Recibos varios",           3000.00, "Mensual",   "CONFIRMADO", "Estimación mensual"),
    ("OTROS", "Uniformes El Halcón",                         "Recibo El Halcón",         1335.00, "Único",     "CONFIRMADO", "Compra ocasional"),
]

# ============ EXCEL ============
wb = Workbook()

# Paleta
VERDE_TITLE   = PatternFill("solid", fgColor="1B5E20")
VERDE_HEADER  = PatternFill("solid", fgColor="388E3C")
VERDE_SUB     = PatternFill("solid", fgColor="A5D6A7")
VERDE_MUY     = PatternFill("solid", fgColor="E8F5E9")
AMARILLO      = PatternFill("solid", fgColor="FFF9C4")
GRIS_ALT      = PatternFill("solid", fgColor="F5F5F5")

FT_TITLE_XL = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
FT_SUB      = Font(name="Calibri", size=11, italic=True, color="424242")
FT_HEAD     = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
FT_CAT      = Font(name="Calibri", size=12, bold=True, color="1B5E20")
FT_BODY     = Font(name="Calibri", size=10)
FT_BOLD     = Font(name="Calibri", size=10, bold=True)

thin = Side(border_style="thin", color="9E9E9E")
medium = Side(border_style="medium", color="1B5E20")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

def money(cell): cell.number_format = '"$"#,##0.00'

ws = wb.active
ws.title = "Catálogo de Gastos"

# Anchos
ws.column_dimensions["A"].width = 42     # Concepto
ws.column_dimensions["B"].width = 26     # Día / fuente
ws.column_dimensions["C"].width = 15     # Monto que aparece
ws.column_dimensions["D"].width = 12     # Frecuencia
ws.column_dimensions["E"].width = 16     # Monto mensual
ws.column_dimensions["F"].width = 13     # Estado
ws.column_dimensions["G"].width = 48     # Notas

# Título grande
ws.merge_cells("A1:G1")
ws["A1"] = "CATÁLOGO DE GASTOS — TITI BURGER"
ws["A1"].font = FT_TITLE_XL; ws["A1"].fill = VERDE_TITLE
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 32

# Subtítulo
ws.merge_cells("A2:G2")
ws["A2"] = "Todos los rubros identificados con su frecuencia y monto mensualizado — Consolidado 10 de julio de 2026"
ws["A2"].font = FT_SUB
ws["A2"].alignment = Alignment(horizontal="center")
ws.row_dimensions[2].height = 20

# Leyenda de estados
ws.merge_cells("A3:G3")
ws["A3"] = "CONFIRMADO = ya verificado con Rafael  •  PENDIENTE = por confirmar frecuencia o monto"
ws["A3"].font = Font(name="Calibri", size=10, italic=True, color="616161")
ws["A3"].alignment = Alignment(horizontal="center")

# Headers fila 5
headers = ["Concepto", "Fuente / día en cuadro", "Monto que aparece", "Frecuencia", "Monto mensual", "Estado", "Notas"]
for i, h in enumerate(headers, start=1):
    c = ws.cell(row=5, column=i, value=h)
    c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[5].height = 28

# Ordenar por categoría en el orden que quiero mostrarla
ORDEN_CATS = ["RENTAS", "SUELDOS", "PROVEEDORES", "SERVICIOS", "IMPUESTOS Y CRÉDITOS", "GASTOS PERSONALES", "OTROS"]
rubros_ordenados = sorted(RUBROS, key=lambda x: (ORDEN_CATS.index(x[0]), x[1]))

r = 6
current_cat = None
category_first_row = {}
for cat, concepto, fuente, monto, freq, estado, notas in rubros_ordenados:
    if cat != current_cat:
        # Fila de categoría
        ws.merge_cells(f"A{r}:G{r}")
        c = ws.cell(row=r, column=1, value=cat)
        c.font = FT_CAT; c.fill = VERDE_SUB
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[r].height = 24
        current_cat = cat
        category_first_row[cat] = r + 1
        r += 1

    # Datos
    ws.cell(row=r, column=1, value=concepto).font = FT_BODY
    ws.cell(row=r, column=2, value=fuente).font = FT_BODY
    c = ws.cell(row=r, column=3, value=monto); money(c); c.font = FT_BODY
    ws.cell(row=r, column=4, value=freq).font = FT_BODY
    ws.cell(row=r, column=4).alignment = Alignment(horizontal="center")

    # Fórmula mensual
    if freq == "Semanal":
        formula = f"=C{r}*4.33"
    elif freq == "Mensual":
        formula = f"=C{r}"
    elif freq == "Bimestral":
        formula = f"=C{r}/2"
    elif freq == "Único":
        formula = f"=C{r}/12"
    else:
        formula = f"=C{r}"
    c = ws.cell(row=r, column=5, value=formula); money(c); c.font = FT_BOLD

    c = ws.cell(row=r, column=6, value=estado)
    c.font = FT_BOLD
    c.alignment = Alignment(horizontal="center")
    if estado == "CONFIRMADO":
        c.fill = VERDE_MUY
    elif estado == "PENDIENTE":
        c.fill = AMARILLO

    c = ws.cell(row=r, column=7, value=notas); c.font = FT_BODY
    c.alignment = Alignment(wrap_text=True, vertical="top")

    # Alterno gris
    if r % 2 == 0:
        for col in range(1, 8):
            if ws.cell(row=r, column=col).fill.fgColor.value in [None, "00000000"]:
                ws.cell(row=r, column=col).fill = GRIS_ALT

    for col in range(1, 8):
        ws.cell(row=r, column=col).border = BOX
    ws.row_dimensions[r].height = 22
    r += 1

# Fila total general
ws.merge_cells(f"A{r}:D{r}")
c = ws.cell(row=r, column=1, value="TOTAL GENERAL MENSUAL (todos los rubros mensualizados)")
c.font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
c.fill = VERDE_TITLE
c.alignment = Alignment(horizontal="right", vertical="center", indent=1)

# Fórmula SUM de todas las filas de datos (excluye las filas de categoría)
# Como las filas de categoría son merges vacíos, SUM las ignora
c = ws.cell(row=r, column=5, value=f"=SUM(E6:E{r-1})")
money(c); c.font = Font(name="Calibri", size=12, bold=True, color="FFFFFF"); c.fill = VERDE_TITLE

for col in [6, 7]:
    ws.cell(row=r, column=col).fill = VERDE_TITLE
ws.row_dimensions[r].height = 28

# Bordes gruesos alrededor del total
for col in range(1, 8):
    ws.cell(row=r, column=col).border = Border(left=medium, right=medium, top=medium, bottom=medium)

# Congelar paneles
ws.freeze_panes = "A6"

# Guardar
wb.save(OUT)
print(f"Guardado: {OUT}", flush=True)

# ============ Actualizar/subir a Drive ============
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)

ANIO_ID = "1vxALi3RxnX-2ApJAVdqUhdmvmdfJimtF"

# Borrar el archivo viejo "Rubros y Frecuencias para revisar" si existe
old = d.files().list(
    q=f"name='Rubros y Frecuencias para revisar' and '{ANIO_ID}' in parents and trashed=false",
    fields="files(id)"
).execute().get("files", [])
for f in old:
    d.files().delete(fileId=f["id"]).execute()
    print(f"Borrado archivo temporal: {f['id']}", flush=True)

file_name = "Catálogo de Gastos - Titi Burger"
media = MediaFileUpload(str(OUT),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)

existing = d.files().list(
    q=f"name='{file_name}' and '{ANIO_ID}' in parents and trashed=false",
    fields="files(id)"
).execute().get("files", [])
if existing:
    d.files().update(fileId=existing[0]["id"], media_body=media).execute()
    print(f"Actualizado: {file_name}", flush=True)
    print(f"Link: https://docs.google.com/spreadsheets/d/{existing[0]['id']}/edit", flush=True)
else:
    f = d.files().create(body={
        "name": file_name, "parents": [ANIO_ID],
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }, media_body=media, fields="id,webViewLink").execute()
    print(f"Subido: {file_name}", flush=True)
    print(f"Link: {f.get('webViewLink')}", flush=True)
