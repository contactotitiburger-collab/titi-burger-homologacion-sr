#!/usr/bin/env python3
"""Excel consolidado — Uber Eats + Rappi + DiDi + Soft Restaurant."""
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
OUT = Path("/home/tito/.openclaw/data/Apps de delivery y Soft Restaurant - Titi Burger.xlsx")

# ============ DATOS ============
# Uber por sucursal
uber = json.loads(Path("/home/tito/.openclaw/data/uber_por_sucursal.json").read_text())["por_sucursal"]

# Ventas Soft Restaurant mayo
sr = json.loads(Path("/home/tito/.openclaw/data/ventas_mayo_2026.json").read_text())
sr_junio = json.loads(Path("/home/tito/.openclaw/data/ventas_junio_2026.json").read_text())

# ============ ESTILOS ============
wb = Workbook()

VERDE_TITLE   = PatternFill("solid", fgColor="1B5E20")
VERDE_HEADER  = PatternFill("solid", fgColor="388E3C")
VERDE_SUB     = PatternFill("solid", fgColor="A5D6A7")
VERDE_MUY     = PatternFill("solid", fgColor="E8F5E9")
AMARILLO      = PatternFill("solid", fgColor="FFF9C4")
NARANJA       = PatternFill("solid", fgColor="FFE0B2")  # Uber
ROSA          = PatternFill("solid", fgColor="F8BBD0")  # Rappi
AZUL_CLARO    = PatternFill("solid", fgColor="B3E5FC")  # DiDi

FT_TITLE_XL = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
FT_SUB      = Font(name="Calibri", size=11, italic=True, color="424242")
FT_HEAD     = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
FT_CAT      = Font(name="Calibri", size=12, bold=True, color="1B5E20")
FT_BODY     = Font(name="Calibri", size=10)
FT_BOLD     = Font(name="Calibri", size=10, bold=True)
FT_TOT      = Font(name="Calibri", size=11, bold=True)

thin = Side(border_style="thin", color="9E9E9E")
medium = Side(border_style="medium", color="1B5E20")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

def money(cell): cell.number_format = '"$"#,##0.00'
def pct(cell): cell.number_format = '0.00%'
def apply_box(ws, r1, c1, r2, c2):
    for r in range(r1, r2+1):
        for c in range(c1, c2+1):
            ws.cell(row=r, column=c).border = BOX

# ============ HOJA 1: RESUMEN COMISIONES POR APP ============
ws = wb.active
ws.title = "Comisiones por app"

ws.column_dimensions["A"].width = 28
for col in ["B","C","D","E","F","G"]:
    ws.column_dimensions[col].width = 18

# Título
ws.merge_cells("A1:G1")
ws["A1"] = "COMISIONES DE LAS APPS DE DELIVERY — TITI BURGER"
ws["A1"].font = FT_TITLE_XL; ws["A1"].fill = VERDE_TITLE
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 28

ws.merge_cells("A2:G2")
ws["A2"] = "Números reales tomados de las liquidaciones — Consolidado 11 de julio de 2026"
ws["A2"].font = FT_SUB
ws["A2"].alignment = Alignment(horizontal="center")
ws.row_dimensions[2].height = 20

# Headers
r = 4
ws.cell(row=r, column=1, value="Concepto").font = FT_HEAD; ws.cell(row=r, column=1).fill = VERDE_HEADER
ws.cell(row=r, column=1).alignment = Alignment(horizontal="center")
for i, app in enumerate(["UBER EATS", "RAPPI", "DIDI FOOD"], start=2):
    c = ws.cell(row=r, column=i, value=app); c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center")
ws.cell(row=r, column=5, value="Notas").font = FT_HEAD; ws.cell(row=r, column=5).fill = VERDE_HEADER
ws.cell(row=r, column=5).alignment = Alignment(horizontal="center")
ws.merge_cells(f"E{r}:G{r}")

r += 1

# Filas de datos
filas = [
    ("Comisión base",           "30.00%", "PENDIENTE", "PENDIENTE (18-30%)",
     "Uber: 48 liquidaciones reales. DiDi: portal accesible pero recibos aún sin datos históricos; % oficial 18-30% según DiDi. Rappi: falta login."),
    ("+ IVA (16% sobre comisión)","4.80%", "PENDIENTE", "~2.88-4.80%",
     "Uber cobra IVA sobre la comisión. DiDi y Rappi: cobran IVA sobre su comisión también."),
    ("Comisión efectiva",       "34.80%", "PENDIENTE", "PENDIENTE",
     "Uber: comisión + IVA confirmado."),
    ("Costo publicidad (anuncios)","~3.00%", "PENDIENTE", "PENDIENTE",
     "Uber lo carga aparte. Rappi y DiDi tienen su equivalente pero pendiente confirmar."),
    ("Otros (misceláneos, ajustes)","~2.00%", "PENDIENTE", "PENDIENTE",
     "Errores en pedido, ajustes, contribuciones. Variable."),
    ("Descuento total sobre venta","~40.00%","PENDIENTE","PENDIENTE",
     "Suma de todo lo anterior. Lo que NO llega de lo que vendió."),
    ("Porcentaje NETO que recibe Titi","~53.00%","PENDIENTE","PENDIENTE",
     "De cada $100 que factura la app, Titi recibe ~$53 (medido en Uber)."),
    ("Frecuencia de pago / facturación","Semanal (lunes)","PENDIENTE","Semanal",
     "Uber: liquida cada lunes. DiDi: ciclo semanal confirmado en el panel. Rappi: pendiente."),
    ("Sucursales activas",      "4 (Fovissste, Montecarlo, Hda Río, San Marcos)","PENDIENTE","3 activas + 6 registradas",
     "Uber: histórico 48 semanas en 4 suc. DiDi: 9 tiendas registradas, solo 3 con ventas 4-10 jul (L Montejano 88, Montecarlo 25, Hda 4)."),
    ("Cuenta destino de depósitos","PENDIENTE","PENDIENTE","BBVA Andrónica CLABE 0140***1049",
     "Uber: no visible aún. DiDi: confirmado a Andrónica Bautista Gomez (misma persona del préstamo Santander)."),
]

for concepto, u, ra, d, nota in filas:
    ws.cell(row=r, column=1, value=concepto).font = FT_BODY
    c = ws.cell(row=r, column=2, value=u); c.font = FT_BODY; c.alignment = Alignment(horizontal="center")
    c.fill = NARANJA
    c = ws.cell(row=r, column=3, value=ra); c.font = FT_BODY; c.alignment = Alignment(horizontal="center")
    c.fill = ROSA
    c = ws.cell(row=r, column=4, value=d); c.font = FT_BODY; c.alignment = Alignment(horizontal="center")
    c.fill = AZUL_CLARO
    ws.merge_cells(f"E{r}:G{r}")
    ws.cell(row=r, column=5, value=nota).font = FT_BODY
    ws.cell(row=r, column=5).alignment = Alignment(wrap_text=True, vertical="top")
    apply_box(ws, r, 1, r, 7)
    ws.row_dimensions[r].height = 26
    r += 1

# ============ HOJA 2: UBER EATS DETALLE ============
ws2 = wb.create_sheet("Uber Eats - detalle")
ws2.column_dimensions["A"].width = 28
for col in ["B","C","D","E","F","G","H","I"]:
    ws2.column_dimensions[col].width = 15

ws2.merge_cells("A1:I1")
ws2["A1"] = "UBER EATS — DETALLE POR SUCURSAL (48 semanas)"
ws2["A1"].font = FT_TITLE_XL; ws2["A1"].fill = VERDE_TITLE
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 26

ws2.merge_cells("A2:I2")
ws2["A2"] = "Fuente: liquidaciones semanales del correo Yahoo (noreply@uber.com)"
ws2["A2"].font = FT_SUB
ws2["A2"].alignment = Alignment(horizontal="center")

headers = ["Sucursal", "Semanas", "Pedidos", "Venta bruta", "Comisión Uber", "IVA sobre comisión",
           "Anuncios", "Otros", "Neto depositado"]
for i, h in enumerate(headers, start=1):
    c = ws2.cell(row=4, column=i, value=h)
    c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws2.row_dimensions[4].height = 30

r = 5
for suc, d in sorted(uber.items(), key=lambda x: -x[1]["venta"]):
    ws2.cell(row=r, column=1, value=suc).font = FT_BODY
    c = ws2.cell(row=r, column=2, value=d["n"]); c.font = FT_BODY; c.alignment = Alignment(horizontal="center")
    c = ws2.cell(row=r, column=3, value=d["pedidos"]); c.font = FT_BODY; c.alignment = Alignment(horizontal="center")
    c = ws2.cell(row=r, column=4, value=d["venta"]); money(c); c.font = FT_BODY
    c = ws2.cell(row=r, column=5, value=d["tarifa"]); money(c); c.font = FT_BODY
    c = ws2.cell(row=r, column=6, value=d["iva"]); money(c); c.font = FT_BODY
    c = ws2.cell(row=r, column=7, value=d["anuncios"]); money(c); c.font = FT_BODY
    c = ws2.cell(row=r, column=8, value=d["misc"]); money(c); c.font = FT_BODY
    c = ws2.cell(row=r, column=9, value=d["neto"]); money(c); c.font = FT_BOLD
    apply_box(ws2, r, 1, r, 9)
    r += 1

# Totales con fórmula
c = ws2.cell(row=r, column=1, value="TOTAL"); c.font = FT_TOT; c.fill = VERDE_SUB
for col_letter in ["B","C","D","E","F","G","H","I"]:
    c = ws2.cell(row=r, column=ord(col_letter)-ord('A')+1, value=f"=SUM({col_letter}5:{col_letter}{r-1})")
    if col_letter in ["D","E","F","G","H","I"]:
        money(c)
    c.font = FT_TOT; c.fill = VERDE_SUB
apply_box(ws2, r, 1, r, 9)
r += 2

# Fila de porcentajes
c = ws2.cell(row=r, column=1, value="% sobre venta bruta"); c.font = FT_BOLD
for col_letter, orig in [("E", "E"), ("F", "F"), ("G", "G"), ("H", "H"), ("I","I")]:
    c = ws2.cell(row=r, column=ord(col_letter)-ord('A')+1,
                 value=f"={orig}{r-2}/D{r-2}")
    pct(c); c.font = FT_BOLD
apply_box(ws2, r, 1, r, 9)

# Notas abajo
r += 3
ws2.merge_cells(f"A{r}:I{r}")
c = ws2.cell(row=r, column=1, value="OBSERVACIONES")
c.font = FT_CAT; c.fill = VERDE_SUB
c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
r += 1

obs = [
    "• Uber Eats deposita SEMANAL — todos los lunes llega el resumen y se paga en los siguientes 5-7 días hábiles.",
    "• Solo 4 sucursales están registradas en Uber Eats: FOVISSTE, MONTECARLO, HACIENDA DEL RÍO, SAN MARCOS.",
    "• Cine Curto y Villas del Rey NO aparecen en Uber (verificar si están registradas).",
    "• Comisión constante 30% del venta bruta + 16% IVA sobre esa comisión = 34.80% efectivo.",
    "• Anuncios varían por sucursal (~3% del bruto en promedio).",
    "• Misceláneos son ajustes por errores, contribuciones, etc. (~2% en promedio).",
    "• Neto real que le llega a Titi: aproximadamente 53% del bruto.",
]
for o in obs:
    ws2.merge_cells(f"A{r}:I{r}")
    ws2.cell(row=r, column=1, value=o).font = FT_BODY
    ws2.cell(row=r, column=1).alignment = Alignment(vertical="center", wrap_text=True)
    ws2.row_dimensions[r].height = 20
    r += 1

# ============ HOJA 3: SOFT RESTAURANT VENTAS ============
ws3 = wb.create_sheet("Soft Restaurant - ventas")
ws3.column_dimensions["A"].width = 28
for col in ["B","C","D","E","F","G"]:
    ws3.column_dimensions[col].width = 15

ws3.merge_cells("A1:G1")
ws3["A1"] = "SOFT RESTAURANT — VENTAS POR SUCURSAL (mayo y junio 2026)"
ws3["A1"].font = FT_TITLE_XL; ws3["A1"].fill = VERDE_TITLE
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 26

ws3.merge_cells("A2:G2")
ws3["A2"] = "Fuente: panel admin.softrestaurant.com — reporte Ventas Mensuales"
ws3["A2"].font = FT_SUB
ws3["A2"].alignment = Alignment(horizontal="center")

r = 4
headers = ["Sucursal", "Mayo tickets", "Mayo venta", "Junio tickets", "Junio venta", "Cambio %", "Ticket promedio"]
for i, h in enumerate(headers, start=1):
    c = ws3.cell(row=r, column=i, value=h)
    c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws3.row_dimensions[r].height = 30

r += 1
suc_orden = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
data_start = r
for s in suc_orden:
    m = sr["sucursales"].get(s, {})
    j = sr_junio["sucursales"].get(s, {})
    ws3.cell(row=r, column=1, value=s).font = FT_BODY
    c = ws3.cell(row=r, column=2, value=m.get("tickets", 0)); c.font = FT_BODY; c.alignment = Alignment(horizontal="center")
    c = ws3.cell(row=r, column=3, value=m.get("total", 0)); money(c); c.font = FT_BODY
    c = ws3.cell(row=r, column=4, value=j.get("tickets", 0)); c.font = FT_BODY; c.alignment = Alignment(horizontal="center")
    c = ws3.cell(row=r, column=5, value=j.get("total", 0)); money(c); c.font = FT_BODY
    c = ws3.cell(row=r, column=6, value=f"=IFERROR((E{r}-C{r})/C{r},0)"); pct(c); c.font = FT_BOLD
    c = ws3.cell(row=r, column=7, value=f"=IFERROR(C{r}/B{r},0)"); money(c); c.font = FT_BODY
    apply_box(ws3, r, 1, r, 7)
    r += 1

# Total con fórmulas
c = ws3.cell(row=r, column=1, value="TOTAL"); c.font = FT_TOT; c.fill = VERDE_SUB
for col_letter in ["B", "C", "D", "E"]:
    c = ws3.cell(row=r, column=ord(col_letter)-ord('A')+1,
                 value=f"=SUM({col_letter}{data_start}:{col_letter}{r-1})")
    if col_letter in ["C","E"]: money(c)
    c.font = FT_TOT; c.fill = VERDE_SUB
c = ws3.cell(row=r, column=6, value=f"=IFERROR((E{r}-C{r})/C{r},0)"); pct(c); c.font = FT_TOT; c.fill = VERDE_SUB
c = ws3.cell(row=r, column=7, value=f"=IFERROR(C{r}/B{r},0)"); money(c); c.font = FT_TOT; c.fill = VERDE_SUB
apply_box(ws3, r, 1, r, 7)

# ============ HOJA 4: CALENDARIO DE PAGOS ============
ws4 = wb.create_sheet("Calendario pagos apps")
ws4.column_dimensions["A"].width = 25
for col in ["B","C","D","E"]:
    ws4.column_dimensions[col].width = 25

ws4.merge_cells("A1:E1")
ws4["A1"] = "CALENDARIO DE PAGOS DE LAS APPS"
ws4["A1"].font = FT_TITLE_XL; ws4["A1"].fill = VERDE_TITLE
ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws4.row_dimensions[1].height = 26

r = 3
for i, h in enumerate(["App", "Frecuencia", "Cuándo llega el resumen", "Cuándo depositan", "Notas"], start=1):
    c = ws4.cell(row=r, column=i, value=h); c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center")
ws4.row_dimensions[r].height = 24
r += 1

filas_cal = [
    ("Uber Eats",  "Semanal",  "Lunes por la mañana", "En los siguientes 5-7 días hábiles",
     "Confirmado con 48 liquidaciones — periodo lun-dom, se cierra 4am del lunes siguiente"),
    ("Rappi",      "PENDIENTE","PENDIENTE", "PENDIENTE",
     "Sin acceso al portal aún. Pedir a Elías el login."),
    ("DiDi Food",  "Semanal",  "PENDIENTE (aún sin datos)", "PENDIENTE",
     "Panel accesible (didi-food.com/es-MX/manager). Ciclo semanal confirmado en Información financiera. Sección Recibos aún vacía — probablemente por retraso en facturación. Depósito a BBVA de Andrónica."),
]
for f in filas_cal:
    for i, v in enumerate(f, start=1):
        c = ws4.cell(row=r, column=i, value=v); c.font = FT_BODY
        c.alignment = Alignment(vertical="center", wrap_text=True)
    if f[0] == "Uber Eats":
        ws4.cell(row=r, column=1).fill = NARANJA
    elif f[0] == "Rappi":
        ws4.cell(row=r, column=1).fill = ROSA
    elif f[0] == "DiDi Food":
        ws4.cell(row=r, column=1).fill = AZUL_CLARO
    apply_box(ws4, r, 1, r, 5)
    ws4.row_dimensions[r].height = 40
    r += 1

# ============ HOJA 5: SOFT RESTAURANT - INFO CLAVE ============
ws5 = wb.create_sheet("Soft Restaurant - clave")
ws5.column_dimensions["A"].width = 40
ws5.column_dimensions["B"].width = 25
ws5.column_dimensions["C"].width = 60

ws5.merge_cells("A1:C1")
ws5["A1"] = "SOFT RESTAURANT — INFORMACIÓN CLAVE"
ws5["A1"].font = FT_TITLE_XL; ws5["A1"].fill = VERDE_TITLE
ws5["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws5.row_dimensions[1].height = 26

r = 3
for i, h in enumerate(["Concepto", "Valor", "Notas"], start=1):
    c = ws5.cell(row=r, column=i, value=h); c.font = FT_HEAD; c.fill = VERDE_HEADER
    c.alignment = Alignment(horizontal="center")
r += 1

t_may = sum(v.get("total",0) for v in sr["sucursales"].values() if v.get("total"))
t_jun = sum(v.get("total",0) for v in sr_junio["sucursales"].values() if v.get("total"))
tk_may = sum(v.get("tickets",0) for v in sr["sucursales"].values() if v.get("tickets"))
tk_jun = sum(v.get("tickets",0) for v in sr_junio["sucursales"].values() if v.get("tickets"))

info = [
    ("Sucursales conectadas al Soft Restaurant", "6", "FOVISSTE, MONTECARLO, SAN MARCOS, HACIENDA DEL RÍO, CINE CURTO, VILLAS DEL REY"),
    ("Sucursales conectadas al panel Analytics", "6", "Ver en admin.softrestaurant.com — todas reportando desde 11-jul-2026"),
    ("Venta total mayo 2026", f"${t_may:,.2f}", f"{tk_may:,} tickets vendidos"),
    ("Venta total junio 2026", f"${t_jun:,.2f}", f"{tk_jun:,} tickets vendidos"),
    ("Ticket promedio general (mayo)", f"${t_may/tk_may:.2f}" if tk_may else "n/a", "Promedio de las 6 sucursales"),
    ("Sucursal con mayor venta", "FOVISSTE (L Montejano)", f"${sr['sucursales']['FOVISSTE']['total']:,.2f} en mayo — 37% del total"),
    ("Sucursal con menor venta", "VILLAS DEL REY", f"${sr['sucursales']['VILLAS DEL REY']['total']:,.2f} en mayo"),
    ("Licencia por sucursal (Backup Soluciones)", "$926.84/mes", "6 sucursales × $926.84 = $5,561/mes"),
    ("Cine Curto licencia", "PAGADA (11-jul-2026)", "Antes estaba impaga y no reportaba — ya reactivada"),
    ("Acceso al panel web", "admin.softrestaurant.com", "Login: titiburger_cordova@yahoo.com.mx"),
    ("Acceso automatizado desde Tito", "SÍ", "Scripts Playwright en ~/.openclaw/scripts/sr_admin_*.py"),
    ("Reportes disponibles", "22 reportes",
     "Ventas por periodo, mensuales, anuales, comparativos, productos más/menos vendidos, ventas por sucursal, ventas por hora/día, cortesías, descuentos"),
]
for concepto, valor, nota in info:
    ws5.cell(row=r, column=1, value=concepto).font = FT_BODY
    c = ws5.cell(row=r, column=2, value=valor); c.font = FT_BOLD
    c.alignment = Alignment(horizontal="center")
    ws5.cell(row=r, column=3, value=nota).font = FT_BODY
    ws5.cell(row=r, column=3).alignment = Alignment(wrap_text=True, vertical="top")
    apply_box(ws5, r, 1, r, 3)
    ws5.row_dimensions[r].height = 24
    r += 1

# ============ HOJA 6: PENDIENTES Y ACCIONES ============
ws6 = wb.create_sheet("Pendientes")
ws6.column_dimensions["A"].width = 40
ws6.column_dimensions["B"].width = 60

ws6.merge_cells("A1:B1")
ws6["A1"] = "PENDIENTES PARA COMPLETAR EL ANÁLISIS"
ws6["A1"].font = FT_TITLE_XL; ws6["A1"].fill = VERDE_TITLE
ws6["A1"].alignment = Alignment(horizontal="center")
ws6.row_dimensions[1].height = 26

r = 3
pends = [
    ("Login Rappi Partners", "Pedir a Elías. Portal: mitienda.rappi.com.mx/login. Sin correos de Rappi en Yahoo — todo llega al portal."),
    ("Comisión exacta DiDi Food", "Portal ACCESIBLE (www.didi-food.com/es-MX/manager). Pestaña 'Recibos' aún vacía — cuando llegue el primer Recibo, se verá el % de comisión aplicado. Revisar en 1-2 semanas."),
    ("Confirmar sucursales en Uber", "Verificar si CINE CURTO y VILLAS DEL REY están registradas en Uber Eats — actualmente no aparecen en las liquidaciones."),
    ("Descargar CSVs detallados de Uber", "El correo de Uber menciona 'nuevo informe descargable' desde el Administrador — pedir login del Uber Merchants para bajar CSV histórico."),
    ("Comisiones reales Rappi", "Pendiente cuando se tenga acceso al portal."),
    ("Ver por qué DiDi solo opera en 3 sucursales", "9 tiendas registradas en DiDi Food Manager pero solo 3 con ventas la semana 4-10 jul (L Montejano, Montecarlo, Hda del Río). Villas/San Marcos/Curto/Almacén: 0 pedidos. Investigar si están pausadas o desconectadas."),
    ("Andrónica y las cuentas de las apps", "DiDi confirma que los depósitos van a la BBVA de Andrónica Bautista Gomez (misma persona del préstamo Santander). Verificar con Uber si es la misma cuenta destino."),
]
for concepto, nota in pends:
    ws6.cell(row=r, column=1, value=concepto).font = FT_BOLD
    ws6.cell(row=r, column=1).fill = AMARILLO
    ws6.cell(row=r, column=2, value=nota).font = FT_BODY
    ws6.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    apply_box(ws6, r, 1, r, 2)
    ws6.row_dimensions[r].height = 40
    r += 1

# Guardar
wb.save(OUT)
print(f"Guardado: {OUT}", flush=True)

# ============ SUBIR A DRIVE ============
td = json.load(open(TOKENS))
c = Credentials(**td)
if not c.valid and c.refresh_token: c.refresh(Request())
d = build("drive", "v3", credentials=c)

TITI_BURGER_FOLDER = "1IA2SK-S0LsCnUvO-ubDQBce0zyPCS9sJ"

def find_or_create_folder(name, parent):
    r = d.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{name}' and '{parent}' in parents and trashed=false",
        fields="files(id)", pageSize=5,
    ).execute()
    if r.get("files"):
        return r["files"][0]["id"]
    folder = d.files().create(body={
        "name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent],
    }, fields="id").execute()
    print(f"Creada: {name}  id={folder['id']}", flush=True)
    return folder["id"]

carpeta_apps = find_or_create_folder("Titi Burger - Apps de delivery", TITI_BURGER_FOLDER)
anio = find_or_create_folder("2026", carpeta_apps)

file_name = "Apps de delivery y Soft Restaurant - Titi Burger"
media = MediaFileUpload(str(OUT),
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    resumable=True)

existing = d.files().list(
    q=f"name='{file_name}' and '{anio}' in parents and trashed=false",
    fields="files(id)"
).execute().get("files", [])
if existing:
    d.files().update(fileId=existing[0]["id"], media_body=media).execute()
    print(f"Actualizado: {file_name}", flush=True)
    print(f"Link: https://docs.google.com/spreadsheets/d/{existing[0]['id']}/edit", flush=True)
else:
    f = d.files().create(body={
        "name": file_name, "parents": [anio],
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }, media_body=media, fields="id,webViewLink").execute()
    print(f"Subido: {file_name}", flush=True)
    print(f"Link: {f.get('webViewLink')}", flush=True)
