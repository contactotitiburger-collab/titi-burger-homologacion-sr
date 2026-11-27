#!/usr/bin/env python3
"""Excel con TODOS los rubros y la frecuencia que asumí, para que Staff corrija."""
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
OUT = Path("/home/tito/.openclaw/data/Rubros y Frecuencias para revisar.xlsx")

# ============ RUBROS: (concepto, día/fuente, monto, frecuencia asumida, estado, notas) ============
# Estado: "CONFIRMADO" (Staff ya me lo aclaró) o "ASUMIDO" (por confirmar)
RUBROS = [
    # ---- LUNES 6 ----
    ("OTROS GASTOS (retiro Don Titi)",       "Lunes 6",     60000.00, "Semanal",  "CONFIRMADO", "Nómina personal Don Titi, usualmente para American Express"),
    ("BIMBO",                                 "Lunes 6",      8964.80, "Semanal",  "ASUMIDO",    "Proveedor de pan — asumo semanal (pedido recurrente)"),
    ("ABOGADO LUIS",                          "Lunes 6",      2500.00, "Semanal",  "ASUMIDO",    "¿Es igualmente cada semana o mensual/único?"),
    ("TOTAL PLAY",                            "Lunes 6",       580.00, "Mensual",  "ASUMIDO",    "Internet — probablemente mensual"),
    ("LONAS",                                 "Lunes 6",      1800.00, "Único",    "ASUMIDO",    "Publicidad/anuncios — probablemente único"),
    ("MC CAIN (papas)",                       "Lunes 6",     12330.00, "Semanal",  "ASUMIDO",    "Proveedor de papas — pedido semanal recurrente"),
    ("COMPRAS",                               "Lunes 6",      6189.00, "Semanal",  "ASUMIDO",    "Concepto genérico — ¿qué es?"),
    ("SUZA CURTO",                            "Lunes 6",      4854.14, "Semanal",  "ASUMIDO",    "No sé qué es — ¿proveedor?"),
    ("FONACOT (retención)",                   "Lunes 6",      9681.55, "Semanal",  "CONFIRMADO", "Retención semanal a empleados afiliados"),
    ("JULIÁN ROMERO (carne)",                 "Lunes 6",      5181.20, "Semanal",  "CONFIRMADO", "Proveedor secundario de carne"),
    ("CASCOS",                                "Lunes 6",      3000.00, "Semanal",  "ASUMIDO",    "¿Envases/cascos de refresco?"),
    ("RENTA SAN MARCOS",                      "Lunes 6",     10890.00, "Mensual",  "CONFIRMADO", "Renta mensual de la sucursal E"),
    ("RENTA CURTO",                           "Lunes 6",     16983.00, "Mensual",  "CONFIRMADO", "Renta mensual de Cine Curto"),
    ("RENTA MONTECARLO",                      "Lunes 6",      9880.00, "Mensual",  "CONFIRMADO", "Renta mensual de la sucursal C"),
    ("HIPOTECA TITI",                         "Lunes 6",      9280.00, "Mensual",  "ASUMIDO",    "Hipoteca personal — asumo mensual"),
    ("CAROLA",                                "Lunes 6",      2000.00, "Semanal",  "ASUMIDO",    "No sé qué es — ¿esposa? ¿mesada?"),
    ("ARÁNDANO",                              "Lunes 6",     13000.00, "Semanal",  "ASUMIDO",    "No sé qué es — ¿pago familiar? ¿proveedor?"),
    # ---- MARTES 7 ----
    ("BOTELLAS",                              "Martes 7",     7619.40, "Semanal",  "ASUMIDO",    "Envases de botella — asumo semanal"),
    ("SANTANDER ANDRÓNICA (crédito simple)",  "Martes 7",    45500.00, "Mensual",  "CONFIRMADO", "1 de 2 préstamos — el otro es $92k (revolvente) que cae en día distinto"),
    ("PEÑAFIEL",                              "Martes 7",     3500.00, "Semanal",  "ASUMIDO",    "Refrescos — asumo semanal"),
    ("RENTA HACIENDA DEL RÍO",                "Martes 7",    16000.00, "Mensual",  "CONFIRMADO", "Renta mensual sucursal B"),
    ("PARRA",                                 "Martes 7",     5122.00, "Semanal",  "ASUMIDO",    "Alimentos Parra — asumo semanal"),
    ("GRASA DINA",                            "Martes 7",     1200.00, "Semanal",  "ASUMIDO",    "No sé qué es"),
    ("HEREBEROS",                             "Martes 7",     1432.00, "Semanal",  "ASUMIDO",    "No sé qué es — aparece varios días con montos distintos"),
    # ---- MIÉRCOLES 8 ----
    ("COCA COLA",                             "Miércoles 8",  5500.00, "Semanal",  "ASUMIDO",    "Refresco — asumo semanal"),
    ("QUEVEDO",                               "Miércoles 8",  5495.10, "Semanal",  "ASUMIDO",    "No sé qué es exactamente"),
    ("PEPSI",                                 "Miércoles 8",  4080.00, "Semanal",  "ASUMIDO",    "Refresco — asumo semanal"),
    ("CANIRAC FOVISSSTE",                     "Miércoles 8",  2700.00, "Semanal",  "ASUMIDO",    "¿Cámara restauranteros? — puede ser mensual"),
    ("BASURA OMAR DOMÍNGUEZ",                 "Miércoles 8",  4088.00, "Semanal",  "ASUMIDO",    "Recolección de basura — puede ser mensual"),
    ("HEREBEROS",                             "Miércoles 8",  4352.20, "Semanal",  "ASUMIDO",    "Aparece otra vez — mismo concepto?"),
    ("REBAJAN",                               "Miércoles 8",  6028.00, "Semanal",  "ASUMIDO",    "No sé qué es"),
    ("CARBÓN",                                "Miércoles 8", 13453.20, "Semanal",  "CONFIRMADO", "Insumo para asado — semanal recurrente"),
    ("PARRA (segunda)",                       "Miércoles 8",  5122.00, "Semanal",  "ASUMIDO",    "Aparece 2 veces en la semana"),
    ("MC CAIN (segunda)",                     "Miércoles 8",  2740.00, "Semanal",  "ASUMIDO",    "Aparece 2 veces en la semana"),
    # ---- JUEVES 9 ----
    ("NÓMINA TITI BURGER",                   "Jueves 9",   105000.00, "Semanal",  "CONFIRMADO", "Nómina semanal — coincide con SR ($102k)"),
    ("VACACIONES TORO FINAL",                 "Jueves 9",     3900.00, "Único",    "ASUMIDO",    "¿Pago único de vacaciones a alguien llamado 'Toro'?"),
    ("KOWI (tocino)",                         "Jueves 9",     7660.00, "Semanal",  "CONFIRMADO", "Proveedor de tocino"),
    ("PASCUAL OMAR DOMÍNGUEZ",                "Jueves 9",     3615.00, "Semanal",  "ASUMIDO",    "No sé qué es — ¿empleado, pago único?"),
    ("BONA (carne)",                          "Jueves 9",    30000.00, "Semanal",  "CONFIRMADO", "Proveedor principal de carne"),
    # ---- VIERNES 10 ----
    ("BIMBO (segundo)",                       "Viernes 10",   8366.40, "Semanal",  "ASUMIDO",    "Bimbo aparece 2 veces en la semana"),
    ("AGUA DE BEBER",                         "Viernes 10",    800.00, "Semanal",  "ASUMIDO",    "¿Garrafón de agua? — semanal"),
    ("JOFA",                                  "Viernes 10",   1514.83, "Semanal",  "ASUMIDO",    "No sé qué es"),
    ("KOWI (segundo)",                        "Viernes 10",   3940.00, "Semanal",  "ASUMIDO",    "Kowi aparece 2 veces en la semana"),
    ("CFE MONTECARLO (recibo)",               "Viernes 10",   2050.00, "Bimestral","ASUMIDO",    "CFE es bimestral por naturaleza — divido /2 para mensual"),
    ("QUEVEDO (segundo)",                     "Viernes 10",   7195.00, "Semanal",  "ASUMIDO",    "Quevedo aparece 2 veces"),
    ("JUAN MUÑOZ",                            "Viernes 10",   2000.00, "Semanal",  "ASUMIDO",    "No sé qué es — ¿empleado extra? ¿pago único?"),
    ("MC CAIN (tercero)",                     "Viernes 10",   2740.00, "Semanal",  "ASUMIDO",    "McCain 3ra vez"),
    # ---- SÁBADO 11 ----
    ("CAROLA (segunda)",                      "Sábado 11",    1200.00, "Semanal",  "ASUMIDO",    "Carola aparece 2 veces"),
    ("HIELOS",                                "Sábado 11",     800.00, "Semanal",  "ASUMIDO",    "Insumo — semanal"),
    ("HEREBEROS (tercera)",                   "Sábado 11",    4000.00, "Semanal",  "ASUMIDO",    "Hereberos 3ra vez"),
    ("RENTA PACHELLI (almacén)",              "Sábado 11",    8740.35, "Mensual",  "CONFIRMADO", "Almacén, NO sucursal — mensual"),
    ("CFE CASA TITI (personal)",              "Sábado 11",    1258.00, "Bimestral","ASUMIDO",    "Recibo CFE de la casa personal de Don Titi — no operativo"),
    ("ECO GAS CASA TITI (personal)",          "Sábado 11",     235.00, "Bimestral","ASUMIDO",    "Recibo Ecogas casa personal Don Titi — no operativo"),
    ("LIVERPOOL TITI (personal)",             "Sábado 11",    1050.00, "Mensual",  "ASUMIDO",    "Plan Liverpool personal Don Titi — no operativo"),
    # ---- RECIBOS INDEPENDIENTES (no del cuadro) ----
    ("SANTANDER ANDRÓNICA (revolvente)",      "Recibo",     92000.00, "Mensual",  "CONFIRMADO", "2do préstamo Santander — mensual"),
    ("IMSS + Infonavit (Lonchería)",          "Recibo IMSS",120578.00, "Mensual",  "CONFIRMADO", "25 cotizantes — recibo IMSS junio 2026"),
    ("IMSS + Infonavit (Herrería)",           "Recibo IMSS", 22116.00, "Mensual",  "CONFIRMADO", "3 cotizantes — recibo IMSS junio 2026"),
    ("Licencia Soft Restaurant x6",           "Recibo Backup", 5561.04,"Mensual",  "CONFIRMADO", "6 sucursales × $926.84 (Backup Soluciones)"),
    ("CFE Fovissste (2 medidores)",           "Recibos CFE", 19500.00, "Bimestral","CONFIRMADO", "Suma de 2 recibos bimestrales — divido /2 para mensual"),
    ("CFE Montecarlo (3 medidores)",          "Recibos CFE",  3301.00, "Bimestral","CONFIRMADO", "3 recibos"),
    ("CFE San Marcos",                        "Recibo CFE",   741.00,  "Bimestral","CONFIRMADO", "1 recibo"),
    ("Agua CESPM Fovissste",                  "Recibo CESPM", 5436.00, "Mensual",  "CONFIRMADO", "Recibo mensual"),
    ("Agua CESPM Montecarlo",                 "Recibo CESPM", 6849.00, "Mensual",  "CONFIRMADO", "Recibo mensual"),
    ("Agua CESPM San Marcos",                 "Recibo CESPM", 804.00,  "Mensual",  "CONFIRMADO", "Recibo mensual"),
    ("Agua CESPM Villas del Rey",             "Recibo CESPM", 288.00,  "Mensual",  "CONFIRMADO", "Recibo mensual"),
    ("Gas Ecogas Fovissste",                  "Recibo Ecogas",5649.00, "Bimestral","CONFIRMADO", "Recibo bimestral"),
    ("Gas Ecogas Montecarlo",                 "Recibo Ecogas", 248.00, "Bimestral","CONFIRMADO", "Recibo bimestral"),
    ("Gas Ecogas Villas del Rey",             "Recibo Ecogas", 759.00, "Bimestral","CONFIRMADO", "Recibo bimestral"),
    ("Sueldos empleados centrales",           "Nómina",     32428.63, "Semanal",  "CONFIRMADO", "9 empleados (AM Jennifer, Carlos, David, Nancy Lizeth, Andrónica, Yazmín, Sandra, Susano)"),
    ("Gasolina",                              "Cuadro semanal (implícito)", 35000, "Semanal", "ASUMIDO", "Aparece en el cuadro pero no lo listé arriba — semanal ~$35k"),
]

# ============ EXCEL ============
wb = Workbook()

VERDE_HEADER = PatternFill("solid", fgColor="388E3C")
VERDE_SUB    = PatternFill("solid", fgColor="C8E6C9")
AMARILLO_ASU = PatternFill("solid", fgColor="FFF9C4")   # amarillo suave para ASUMIDO
VERDE_CONF   = PatternFill("solid", fgColor="E8F5E9")   # verde muy claro para CONFIRMADO

FT_TITLE = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
FT_HEAD  = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
FT_BODY  = Font(name="Calibri", size=10)
FT_BOLD  = Font(name="Calibri", size=10, bold=True)

thin = Side(border_style="thin", color="9E9E9E")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

def money(cell): cell.number_format = '"$"#,##0.00'

ws = wb.active
ws.title = "Rubros y frecuencias"

# Anchos
ws.column_dimensions["A"].width = 42     # Concepto
ws.column_dimensions["B"].width = 20     # Día / fuente
ws.column_dimensions["C"].width = 15     # Monto que aparece
ws.column_dimensions["D"].width = 12     # Frecuencia asumida
ws.column_dimensions["E"].width = 15     # Monto mensual (fórmula)
ws.column_dimensions["F"].width = 14     # Estado
ws.column_dimensions["G"].width = 20     # Frecuencia CORRECTA (para llenar)
ws.column_dimensions["H"].width = 45     # Notas

# Título
ws.merge_cells("A1:H1")
ws["A1"] = "RUBROS Y FRECUENCIAS PARA REVISAR — Rafael, corrige la columna G"
ws["A1"].font = FT_TITLE; ws["A1"].fill = VERDE_HEADER
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 26

# Instrucciones fila 2
ws.merge_cells("A2:H2")
ws["A2"] = "Marca en 'FRECUENCIA CORRECTA' (col G) si mi asunción está mal. Ejemplo: si asumí Semanal y era Mensual, escribe 'Mensual' ahí. Amarillo = asumido (por confirmar). Verde claro = ya confirmado."
ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="424242")
ws["A2"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[2].height = 30

# Headers fila 3
headers = ["Concepto", "Día / fuente", "Monto que aparece", "Frecuencia ASUMIDA", "Monto mensual (fórmula)", "Estado", "FRECUENCIA CORRECTA (Rafael)", "Notas"]
for i, h in enumerate(headers, start=1):
    c = ws.cell(row=3, column=i, value=h)
    c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[3].height = 34

# Filas de datos
r = 4
for concepto, fuente, monto, freq, estado, notas in RUBROS:
    ws.cell(row=r, column=1, value=concepto).font = FT_BODY
    ws.cell(row=r, column=2, value=fuente).font = FT_BODY
    c = ws.cell(row=r, column=3, value=monto); money(c); c.font = FT_BODY
    ws.cell(row=r, column=4, value=freq).font = FT_BODY
    ws.cell(row=r, column=4).alignment = Alignment(horizontal="center")

    # Monto mensual con fórmula según frecuencia
    if freq == "Semanal":
        formula = f"=C{r}*4.33"
    elif freq == "Mensual":
        formula = f"=C{r}"
    elif freq == "Bimestral":
        formula = f"=C{r}/2"
    elif freq == "Único":
        formula = f"=C{r}/12"  # amortizar en el año
    else:
        formula = f"=C{r}"
    c = ws.cell(row=r, column=5, value=formula); money(c); c.font = FT_BOLD

    # Estado con color
    c = ws.cell(row=r, column=6, value=estado)
    c.font = FT_BOLD
    c.alignment = Alignment(horizontal="center")
    if estado == "CONFIRMADO":
        c.fill = VERDE_CONF
    else:  # ASUMIDO
        c.fill = AMARILLO_ASU

    # Col G vacía para que Staff llene
    ws.cell(row=r, column=7, value="").fill = PatternFill("solid", fgColor="FFFFFF")

    # Notas
    c = ws.cell(row=r, column=8, value=notas); c.font = FT_BODY
    c.alignment = Alignment(wrap_text=True, vertical="top")

    for col in range(1, 9):
        ws.cell(row=r, column=col).border = BOX
    ws.row_dimensions[r].height = 22
    r += 1

# Congelar paneles
ws.freeze_panes = "A4"

# Guardar
wb.save(OUT)
print(f"Guardado local: {OUT}", flush=True)

# Subir a Drive
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)

TITI_BURGER_FOLDER = "1IA2SK-S0LsCnUvO-ubDQBce0zyPCS9sJ"
CARPETA_ANALISIS = "1HQgpreQsh9S39_7sNsPxbwzVyD21gSAm"  # Titi Burger - Ganancias y Gastos
ANIO_ID = "1vxALi3RxnX-2ApJAVdqUhdmvmdfJimtF"  # 2026

file_name = "Rubros y Frecuencias para revisar"
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
