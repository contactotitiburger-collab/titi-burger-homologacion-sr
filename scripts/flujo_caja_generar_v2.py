#!/usr/bin/env python3
"""Excel de Rentabilidad Titi Burger v2 — con dashboard, gráficas y estilo profesional.

Dos archivos:
1. Rentabilidad - Últimos 3 meses.xlsx (Abr, May, Jun 2026)
2. Rentabilidad - Junio 2026.xlsx  (detalle por sucursal + producto)

Estilo: bordes uniformes, colores azul marino/gris, tipografía Calibri 10-11,
gráficas nativas Excel (barras, línea, pie, waterfall visual).
"""
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, PieChart, Reference, BarChart3D
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.layout import Layout, ManualLayout

DATA = Path.home() / ".openclaw/data"
OUT = Path.home() / ".openclaw/workspace/apps_delivery"
OUT.mkdir(parents=True, exist_ok=True)

# ---- Fuentes ----
ventas12 = json.loads((DATA / "ventas_12m_por_sucursal.json").read_text())["meses"]
didi_jun = json.loads((DATA / "didi_junio_2026.json").read_text())

SUCURSALES = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
MESES = [("2026-04", "Abril"), ("2026-05", "Mayo"), ("2026-06", "Junio")]

RENTAS = {
    "FOVISSTE": 24000, "MONTECARLO": 9880, "SAN MARCOS": 10890,
    "HACIENDA DEL RÍO": 10000, "CURTO": 16983, "VILLAS DEL REY": 8000,
}
RENTA_PACHELLI = 8740.35
NOMINA_CENTRAL_SEM = 32428.63
NOMINA_SUCS_SEM = 67687.44
NOMINA_MES = (NOMINA_CENTRAL_SEM + NOMINA_SUCS_SEM) * 4.3
EXTRAS_SEM = 2500 + 2000 + 3615
EXTRAS_MES = EXTRAS_SEM * 4.3
PRESTAMO_ANDRONICA = 137000
RETIRO_DON_TITI = 60000 * 4.3

COMISIONES = {
    "Uber":  {"comision": 0.30},
    "DiDi":  {"comision": 0.20},
    "Rappi": {"comision": 0.27},
}

# ---- Paleta profesional ----
AZUL_MARINO = "1F3864"
AZUL_MEDIO = "2E5C99"
AZUL_CLARO = "D9E2F3"
GRIS_HEADER = "E7E6E6"
GRIS_CLARO = "F2F2F2"
ROJO_ALERTA = "C00000"
ROJO_SUAVE = "F8CBAD"
VERDE_OK = "548235"
VERDE_SUAVE = "C6E0B4"
AMARILLO_TOTAL = "FFE699"
BLANCO = "FFFFFF"

# ---- Estilos ----
F_TITULO = Font(name="Calibri", size=16, bold=True, color=BLANCO)
F_SUBTITULO = Font(name="Calibri", size=12, bold=True, color=AZUL_MARINO)
F_HEADER = Font(name="Calibri", size=10, bold=True, color=BLANCO)
F_LABEL = Font(name="Calibri", size=10, bold=True, color=AZUL_MARINO)
F_NORMAL = Font(name="Calibri", size=10)
F_TOTAL = Font(name="Calibri", size=10, bold=True)
F_ROJO = Font(name="Calibri", size=10, bold=True, color=ROJO_ALERTA)
F_VERDE = Font(name="Calibri", size=10, bold=True, color=VERDE_OK)
F_KPI_LABEL = Font(name="Calibri", size=10, bold=True, color="595959")
F_KPI_VALUE = Font(name="Calibri", size=18, bold=True, color=AZUL_MARINO)
F_KPI_VALUE_NEG = Font(name="Calibri", size=18, bold=True, color=ROJO_ALERTA)
F_NOTA = Font(name="Calibri", size=9, italic=True, color="595959")

FILL_TITULO = PatternFill("solid", fgColor=AZUL_MARINO)
FILL_HEADER = PatternFill("solid", fgColor=AZUL_MEDIO)
FILL_LABEL = PatternFill("solid", fgColor=AZUL_CLARO)
FILL_ROW_ALT = PatternFill("solid", fgColor=GRIS_CLARO)
FILL_TOTAL = PatternFill("solid", fgColor=AMARILLO_TOTAL)
FILL_ROJO = PatternFill("solid", fgColor=ROJO_SUAVE)
FILL_VERDE = PatternFill("solid", fgColor=VERDE_SUAVE)
FILL_KPI = PatternFill("solid", fgColor=GRIS_HEADER)

B_LADO = Side(style="thin", color="BFBFBF")
BORDE = Border(left=B_LADO, right=B_LADO, top=B_LADO, bottom=B_LADO)

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", indent=1)
RIGHT = Alignment(horizontal="right", vertical="center")

FMT_MON = '"$"#,##0'
FMT_MON_D = '"$"#,##0.00'
FMT_PCT = "0.0%"


def title_bar(ws, texto, fila, cols):
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=cols)
    c = ws.cell(fila, 1, texto)
    c.font = F_TITULO
    c.fill = FILL_TITULO
    c.alignment = CENTER
    ws.row_dimensions[fila].height = 32


def section_bar(ws, texto, fila, cols):
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=cols)
    c = ws.cell(fila, 1, texto)
    c.font = F_SUBTITULO
    c.fill = FILL_LABEL
    c.alignment = LEFT
    ws.row_dimensions[fila].height = 22


def header_row(ws, textos, fila, col_start=1):
    for i, t in enumerate(textos):
        c = ws.cell(fila, col_start + i, t)
        c.font = F_HEADER
        c.fill = FILL_HEADER
        c.alignment = CENTER
        c.border = BORDE
    ws.row_dimensions[fila].height = 24


def bordear(ws, r1, c1, r2, c2, zebra=True):
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            ws.cell(r, c).border = BORDE
            if zebra and (r - r1) % 2 == 1:
                if ws.cell(r, c).fill.fgColor.rgb in (None, "00000000"):
                    ws.cell(r, c).fill = FILL_ROW_ALT


def moneda(cell, decimales=False):
    cell.number_format = FMT_MON_D if decimales else FMT_MON
    if not cell.font.bold:
        cell.font = F_NORMAL
    cell.alignment = RIGHT


def kpi_box(ws, fila_top, col_top, label, valor, decimales=False, negativo=False):
    # 2 filas: label (1 fila) + valor (1 fila), ancho 2 cols
    ws.merge_cells(start_row=fila_top, start_column=col_top,
                   end_row=fila_top, end_column=col_top + 1)
    ws.merge_cells(start_row=fila_top + 1, start_column=col_top,
                   end_row=fila_top + 1, end_column=col_top + 1)
    l = ws.cell(fila_top, col_top, label)
    l.font = F_KPI_LABEL
    l.fill = FILL_KPI
    l.alignment = CENTER
    v = ws.cell(fila_top + 1, col_top, valor)
    v.font = F_KPI_VALUE_NEG if negativo else F_KPI_VALUE
    v.fill = FILL_KPI
    v.alignment = CENTER
    v.number_format = FMT_MON_D if decimales else FMT_MON
    ws.row_dimensions[fila_top].height = 20
    ws.row_dimensions[fila_top + 1].height = 34
    # bordes
    for r in (fila_top, fila_top + 1):
        for c in range(col_top, col_top + 2):
            ws.cell(r, c).border = BORDE


# ==========================================================
#  ARCHIVO 1: Rentabilidad — Últimos 3 meses
# ==========================================================
def gen_3meses(path: Path):
    wb = Workbook()

    # ============== DASHBOARD ==============
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_view.showGridLines = False

    # anchos
    for i, w in enumerate([3, 22, 18, 18, 18, 18, 18, 3], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    title_bar(ws, "TITI BURGER — Rentabilidad · Últimos 3 meses (Abr–Jun 2026)", 2, 8)

    # KPIs
    ing_prom = sum(sum(v.get("subtotal", 0) for v in ventas12[m].values() if isinstance(v, dict))
                   for m, _ in MESES) / 3
    egr_fijos = (sum(RENTAS.values()) + RENTA_PACHELLI + NOMINA_MES + EXTRAS_MES
                 + PRESTAMO_ANDRONICA + RETIRO_DON_TITI)
    util_prom = ing_prom - egr_fijos

    kpi_box(ws, 4, 2, "Venta promedio / mes", ing_prom)
    kpi_box(ws, 4, 4, "Egresos fijos / mes", egr_fijos)
    kpi_box(ws, 4, 6, "Utilidad antes de proveedores", util_prom, negativo=(util_prom < 0))

    # nota debajo KPIs
    ws.merge_cells(start_row=7, start_column=2, end_row=7, end_column=7)
    c = ws.cell(7, 2, "Egresos fijos: rentas + nóminas + extraordinarios + préstamos Andrónica + retiro Don Titi. Antes de proveedores, servicios, comisiones apps e impuestos.")
    c.font = F_NOTA; c.alignment = LEFT

    # === Sección: Ventas por mes ===
    section_bar(ws, "Ventas por sucursal — comparativo", 9, 8)
    header_row(ws, ["Sucursal", "Abril", "Mayo", "Junio", "Promedio", "Δ May→Jun"], 10, col_start=2)

    fila = 11
    for suc in SUCURSALES:
        ws.cell(fila, 2, suc).font = F_LABEL
        ws.cell(fila, 2).alignment = LEFT
        vals = []
        for i, (m, _) in enumerate(MESES):
            v = ventas12[m].get(suc, {}).get("subtotal", 0)
            vals.append(v)
            moneda(ws.cell(fila, 3 + i, v))
        # promedio
        moneda(ws.cell(fila, 6, f"=AVERAGE(C{fila}:E{fila})"))
        # delta may→jun
        d = ws.cell(fila, 7, f"=(E{fila}/D{fila})-1")
        d.number_format = FMT_PCT
        d.alignment = RIGHT
        d.font = F_NORMAL
        fila += 1

    # total
    ws.cell(fila, 2, "TOTAL").font = F_TOTAL
    ws.cell(fila, 2).alignment = LEFT
    ws.cell(fila, 2).fill = FILL_TOTAL
    for col_i in [3, 4, 5, 6]:
        col = get_column_letter(col_i)
        c = ws.cell(fila, col_i, f"=SUM({col}11:{col}{fila-1})")
        moneda(c); c.font = F_TOTAL; c.fill = FILL_TOTAL
    tot_fila = fila
    fila += 1

    bordear(ws, 10, 2, tot_fila, 7)

    # === Gráfica: Ventas por sucursal, comparación por mes (barras agrupadas) ===
    chart = BarChart()
    chart.type = "col"
    chart.style = 11
    chart.title = "Ventas por sucursal — Abr/May/Jun 2026"
    chart.y_axis.title = "Pesos"
    chart.x_axis.title = None
    data_ref = Reference(ws, min_col=3, min_row=10, max_col=5, max_row=10 + len(SUCURSALES))
    cats_ref = Reference(ws, min_col=2, min_row=11, max_row=10 + len(SUCURSALES))
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.height = 10
    chart.width = 22
    chart.legend.position = "b"
    ws.add_chart(chart, f"B{fila + 1}")

    fila_after_chart = fila + 22

    # === Sección: Egresos fijos (composición) ===
    section_bar(ws, "Egresos fijos mensuales — composición", fila_after_chart, 8)
    header_row(ws, ["Concepto", "Monto / mes", "% del total"], fila_after_chart + 1, col_start=2)

    fila = fila_after_chart + 2
    fila_ini_e = fila
    egresos = [
        ("Nómina (central + sucursales)", NOMINA_MES),
        ("Retiro semanal Don Titi (Amex)", RETIRO_DON_TITI),
        ("Préstamos Andrónica Santander", PRESTAMO_ANDRONICA),
        ("Rentas (6 sucs + Pachelli)", sum(RENTAS.values()) + RENTA_PACHELLI),
        ("Extraordinarios (Abogado + Muñoz + Pascual)", EXTRAS_MES),
    ]
    for concepto, monto in egresos:
        ws.cell(fila, 2, concepto).font = F_NORMAL
        ws.cell(fila, 2).alignment = LEFT
        moneda(ws.cell(fila, 3, monto))
        p = ws.cell(fila, 4, f"=C{fila}/SUM($C${fila_ini_e}:$C${fila_ini_e + len(egresos) - 1})")
        p.number_format = FMT_PCT
        p.alignment = RIGHT
        fila += 1
    tot_e_fila = fila
    ws.cell(fila, 2, "TOTAL").font = F_TOTAL; ws.cell(fila, 2).fill = FILL_TOTAL; ws.cell(fila, 2).alignment = LEFT
    c = ws.cell(fila, 3, f"=SUM(C{fila_ini_e}:C{fila-1})"); moneda(c); c.font = F_TOTAL; c.fill = FILL_TOTAL
    ws.cell(fila, 4).fill = FILL_TOTAL
    bordear(ws, fila_after_chart + 1, 2, fila, 4)

    # === Pie chart de egresos ===
    pie = PieChart()
    pie.title = "Egresos fijos — dónde va la lana"
    labels_ref = Reference(ws, min_col=2, min_row=fila_ini_e, max_row=tot_e_fila - 1)
    data_ref = Reference(ws, min_col=3, min_row=fila_ini_e, max_row=tot_e_fila - 1)
    pie.add_data(data_ref, titles_from_data=False)
    pie.set_categories(labels_ref)
    pie.dataLabels = DataLabelList(showPercent=True)
    pie.height = 10
    pie.width = 15
    ws.add_chart(pie, f"F{fila_after_chart + 1}")

    # === Notas al final ===
    fila_notas = max(fila + 2, fila_after_chart + 20)
    section_bar(ws, "Qué falta para cerrar el cuadre", fila_notas, 8)
    faltantes = [
        "Proveedores carne (Bona, Julián) — pendiente facturas Yahoo o Nancy",
        "Proveedor pollo (Islas) y tocino (Kowi) — pendiente factura",
        "Servicios: luz, gas, agua por sucursal — Ecogas confirmado, resto en pizarrón Rafael",
        "Comisiones apps: Uber (cta huérfana), Rappi (portal Elías) — DiDi ya real",
        "SAT / IMSS / IVA — despacho contable",
        "Costo por producto — Excel Cocina vacío, hay que llenarlo",
    ]
    for i, txt in enumerate(faltantes):
        ws.merge_cells(start_row=fila_notas + 1 + i, start_column=2,
                       end_row=fila_notas + 1 + i, end_column=7)
        c = ws.cell(fila_notas + 1 + i, 2, "•  " + txt)
        c.font = F_ROJO; c.fill = FILL_ROJO; c.alignment = LEFT

    # ============== HOJA 2: DETALLE VENTAS ==============
    ws2 = wb.create_sheet("Ventas detalle")
    ws2.sheet_view.showGridLines = False
    for i, w in enumerate([3, 22, 15, 15, 15, 15, 15, 15, 3], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    title_bar(ws2, "Ventas Soft Restaurant — 12 meses móviles por sucursal", 2, 9)

    # Todos los meses disponibles (últimos 12)
    all_meses = sorted(ventas12.keys())[-12:]
    header_row(ws2, ["Sucursal"] + all_meses, 4, col_start=2)

    fila = 5
    for suc in SUCURSALES:
        ws2.cell(fila, 2, suc).font = F_LABEL; ws2.cell(fila, 2).alignment = LEFT
        for i, m in enumerate(all_meses):
            v = ventas12[m].get(suc, {}).get("subtotal", 0)
            moneda(ws2.cell(fila, 3 + i, v))
        fila += 1
    ws2.cell(fila, 2, "TOTAL").font = F_TOTAL; ws2.cell(fila, 2).fill = FILL_TOTAL; ws2.cell(fila, 2).alignment = LEFT
    for i in range(len(all_meses)):
        col = get_column_letter(3 + i)
        c = ws2.cell(fila, 3 + i, f"=SUM({col}5:{col}{fila-1})")
        moneda(c); c.font = F_TOTAL; c.fill = FILL_TOTAL
    bordear(ws2, 4, 2, fila, 2 + len(all_meses))

    # Gráfica de línea: tendencia total mes a mes
    line = LineChart()
    line.title = "Tendencia venta total — 12 meses"
    line.y_axis.title = "Pesos"
    data_ref = Reference(ws2, min_col=3, min_row=fila, max_col=2 + len(all_meses), max_row=fila)
    cats_ref = Reference(ws2, min_col=3, min_row=4, max_col=2 + len(all_meses), max_row=4)
    line.add_data(data_ref, titles_from_data=False)
    line.set_categories(cats_ref)
    line.height = 10; line.width = 24
    line.legend = None
    ws2.add_chart(line, f"B{fila + 3}")

    wb.save(path)
    print(f"Guardado: {path}")


# ==========================================================
#  ARCHIVO 2: Rentabilidad — Junio 2026 detalle
# ==========================================================
def gen_junio(path: Path):
    wb = Workbook()

    # ============ DASHBOARD JUNIO ============
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_view.showGridLines = False
    for i, w in enumerate([3, 22, 15, 15, 15, 15, 15, 15, 3], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    title_bar(ws, "TITI BURGER — Rentabilidad · Junio 2026", 2, 9)

    ventas_jun = ventas12["2026-06"]
    total_sr = sum(v.get("subtotal", 0) for v in ventas_jun.values() if isinstance(v, dict))
    total_didi = didi_jun["total_bruto"]
    # Neto DiDi PF
    def neto_pf(bruto, app):
        com = COMISIONES[app]["comision"]
        return bruto - bruto * com - bruto * com * 0.16 - bruto * 0.08 - bruto * 0.025

    egr_fijos_jun = (sum(RENTAS.values()) + RENTA_PACHELLI + NOMINA_MES + EXTRAS_MES
                     + PRESTAMO_ANDRONICA + RETIRO_DON_TITI)
    ingresos_neto = total_sr + neto_pf(total_didi, "DiDi")
    util_bruta = ingresos_neto - egr_fijos_jun

    kpi_box(ws, 4, 2, "Venta SR Junio", total_sr)
    kpi_box(ws, 4, 4, "Neto DiDi (post-comisión)", neto_pf(total_didi, "DiDi"))
    kpi_box(ws, 4, 6, "Utilidad antes proveedores", util_bruta, negativo=(util_bruta < 0))

    # === Detalle por sucursal ===
    section_bar(ws, "Detalle por sucursal — Junio 2026", 8, 9)
    header_row(ws, ["Sucursal", "Venta SR", "DiDi bruto", "Uber bruto", "Rappi bruto",
                    "Total bruto", "Renta", "% renta/venta"], 9, col_start=2)

    fila = 10
    fila_ini = fila
    for suc in SUCURSALES:
        ws.cell(fila, 2, suc).font = F_LABEL; ws.cell(fila, 2).alignment = LEFT
        sr = ventas_jun.get(suc, {}).get("subtotal", 0)
        moneda(ws.cell(fila, 3, sr))
        didi_key = {
            "FOVISSTE": "L Montejano", "MONTECARLO": "Montecarlo",
            "SAN MARCOS": "San Marcos", "HACIENDA DEL RÍO": "Hda del Río",
            "CURTO": "Curto", "VILLAS DEL REY": "Villas del Rey",
        }[suc]
        d = didi_jun["sucursales"].get(didi_key, {}).get("ingresos_brutos", 0)
        moneda(ws.cell(fila, 4, d))
        c = ws.cell(fila, 5, "?"); c.font = F_ROJO; c.fill = FILL_ROJO; c.alignment = CENTER
        c = ws.cell(fila, 6, "?"); c.font = F_ROJO; c.fill = FILL_ROJO; c.alignment = CENTER
        moneda(ws.cell(fila, 7, f"=C{fila}+D{fila}"))
        moneda(ws.cell(fila, 8, RENTAS[suc]))
        p = ws.cell(fila, 9, f"=H{fila}/C{fila}"); p.number_format = FMT_PCT; p.alignment = RIGHT
        fila += 1
    ws.cell(fila, 2, "TOTAL").font = F_TOTAL; ws.cell(fila, 2).fill = FILL_TOTAL; ws.cell(fila, 2).alignment = LEFT
    for col_i in [3, 4, 7, 8]:
        col = get_column_letter(col_i)
        c = ws.cell(fila, col_i, f"=SUM({col}{fila_ini}:{col}{fila-1})")
        moneda(c); c.font = F_TOTAL; c.fill = FILL_TOTAL
    tot_fila = fila
    fila += 1
    bordear(ws, 9, 2, tot_fila, 9)

    # Gráfica: venta SR por sucursal
    bar = BarChart()
    bar.type = "bar"
    bar.style = 11
    bar.title = "Venta SR por sucursal — Junio 2026"
    data_ref = Reference(ws, min_col=3, min_row=9, max_row=tot_fila - 1)
    cats_ref = Reference(ws, min_col=2, min_row=fila_ini, max_row=tot_fila - 1)
    bar.add_data(data_ref, titles_from_data=True)
    bar.set_categories(cats_ref)
    bar.height = 9; bar.width = 22
    bar.legend = None
    ws.add_chart(bar, f"B{fila + 1}")

    fila = fila + 20

    # === Método Meza aplicado a apps ===
    section_bar(ws, "Método Meza (PF) aplicado a apps — Junio 2026", fila, 9)
    fila += 1
    header_row(ws, ["App", "Bruto", "% Comisión", "Comisión", "IVA com. 16%",
                    "IVA ret. 8%", "ISR ret. 2.5%", "Neto PF"], fila, col_start=2)
    fila_hdr = fila
    fila += 1
    fila_ini_meza = fila
    for app_name, bruto in [("DiDi", total_didi), ("Uber", None), ("Rappi", None)]:
        ws.cell(fila, 2, app_name).font = F_LABEL; ws.cell(fila, 2).alignment = LEFT
        if bruto is not None:
            moneda(ws.cell(fila, 3, bruto))
            p = ws.cell(fila, 4, COMISIONES[app_name]["comision"]); p.number_format = FMT_PCT; p.alignment = RIGHT
            moneda(ws.cell(fila, 5, f"=C{fila}*D{fila}"))
            moneda(ws.cell(fila, 6, f"=E{fila}*0.16"))
            moneda(ws.cell(fila, 7, f"=C{fila}*0.08"))
            moneda(ws.cell(fila, 8, f"=C{fila}*0.025"))
            c = ws.cell(fila, 9, f"=C{fila}-E{fila}-F{fila}-G{fila}-H{fila}")
            moneda(c); c.font = F_VERDE; c.fill = FILL_VERDE
        else:
            for i in range(3, 10):
                c = ws.cell(fila, i, "?"); c.font = F_ROJO; c.fill = FILL_ROJO; c.alignment = CENTER
        fila += 1
    bordear(ws, fila_hdr, 2, fila - 1, 9)

    fila += 2

    # === Waterfall estilo tabla: cómo se desmenuza el peso ===
    section_bar(ws, "De la venta bruta al bolsillo — Cascada Junio (por cada $100 vendidos en app)", fila, 9)
    fila += 1
    header_row(ws, ["Paso", "Uber (30%)", "DiDi (20%)", "Rappi (27%)"], fila, col_start=2)
    fila += 1
    fila_ini_cascada = fila
    pasos = [
        ("Bruto vendido", [100, 100, 100]),
        ("−  Comisión app", [-30, -20, -27]),
        ("−  IVA de la comisión (16%)", [-4.80, -3.20, -4.32]),
        ("−  IVA retenido (8%)", [-8, -8, -8]),
        ("−  ISR retenido (2.5%)", [-2.50, -2.50, -2.50]),
    ]
    for etiq, vals in pasos:
        ws.cell(fila, 2, etiq).font = F_NORMAL; ws.cell(fila, 2).alignment = LEFT
        for i, v in enumerate(vals):
            c = ws.cell(fila, 3 + i, v); moneda(c, decimales=True)
        fila += 1
    # neto
    ws.cell(fila, 2, "=  Neto que llega").font = F_TOTAL; ws.cell(fila, 2).fill = FILL_VERDE; ws.cell(fila, 2).alignment = LEFT
    for i, v in enumerate([54.70, 66.30, 58.18]):
        c = ws.cell(fila, 3 + i, v); moneda(c, decimales=True); c.font = F_VERDE; c.fill = FILL_VERDE
    fila += 1
    bordear(ws, fila_ini_cascada - 1, 2, fila - 1, 5)

    # ============ HOJA 2: PRODUCTOS ============
    ws2 = wb.create_sheet("Productos junio")
    ws2.sheet_view.showGridLines = False
    for i, w in enumerate([3, 10, 28, 12, 14, 14, 14, 14, 14, 3], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    title_bar(ws2, "Top 10 productos junio 2026 · Costo pendiente (llenar TITI_BURGER_COCINA.xlsx)", 2, 10)

    header_row(ws2, ["Clave", "Producto", "Cantidad", "Precio prom", "Importe s/IVA",
                     "Costo unit.", "Costo total", "Margen $", "Margen %"], 4, col_start=2)

    productos = [
        ("03001", "#2 PAPAS A LA FRANCESA", 1397, 3.19, 4455),
        ("01001", "#1 TITI CLASICA", 1047, 132.42, 138639),
        ("01048", "TITI COMBO CLASICA", 763, 201.31, 153597),
        ("04003", "COCA COLA", 381, 13.64, 5195),
        ("04002", "JAMAICA", 331, 11.51, 3810),
        ("04001", "TE", 279, 9.14, 2550),
        ("01002", "#5 TITI DOBLE CARNE", 221, 200.00, 44200),
        ("01037", "TITI COMBO DOBLE CARNE", 205, 260.00, 53300),
        ("04010", "ROOT BEER", 188, 8.93, 1679),
        ("01039", "TITI COMBO TOCINO", 137, 235.00, 32195),
    ]
    fila = 5
    for clave, prod, cant, precio, importe in productos:
        ws2.cell(fila, 2, clave).font = F_NORMAL
        ws2.cell(fila, 3, prod).font = F_NORMAL; ws2.cell(fila, 3).alignment = LEFT
        c = ws2.cell(fila, 4, cant); c.number_format = "#,##0"; c.alignment = RIGHT
        moneda(ws2.cell(fila, 5, precio), decimales=True)
        moneda(ws2.cell(fila, 6, importe))
        c = ws2.cell(fila, 7, "?"); c.font = F_ROJO; c.fill = FILL_ROJO; c.alignment = CENTER
        moneda(ws2.cell(fila, 8, f'=IFERROR(D{fila}*G{fila}, "")'))
        moneda(ws2.cell(fila, 9, f'=IFERROR(F{fila}-H{fila}, "")'))
        c = ws2.cell(fila, 10, f'=IFERROR(I{fila}/F{fila}, "")'); c.number_format = FMT_PCT; c.alignment = RIGHT
        fila += 1
    bordear(ws2, 4, 2, fila - 1, 10)

    # Gráfica: cantidad top 10
    bar = BarChart()
    bar.type = "bar"; bar.style = 12
    bar.title = "Unidades vendidas — Top 10 productos junio"
    data_ref = Reference(ws2, min_col=4, min_row=4, max_row=fila - 1)
    cats_ref = Reference(ws2, min_col=3, min_row=5, max_row=fila - 1)
    bar.add_data(data_ref, titles_from_data=True)
    bar.set_categories(cats_ref)
    bar.height = 12; bar.width = 24
    bar.legend = None
    ws2.add_chart(bar, f"B{fila + 2}")

    # ============ HOJA 3: EGRESOS DETALLE ============
    ws3 = wb.create_sheet("Egresos junio")
    ws3.sheet_view.showGridLines = False
    for i, w in enumerate([3, 40, 18, 20, 40, 3], start=1):
        ws3.column_dimensions[get_column_letter(i)].width = w

    title_bar(ws3, "Egresos fijos — Junio 2026", 2, 6)

    header_row(ws3, ["Concepto", "Monto mes", "Frecuencia origen", "Notas"], 4, col_start=2)

    rows = [
        ("Renta Cine Curto", 16983, "Mensual", "Confirmado"),
        ("Renta Fovissste (est.)", 24000, "Mensual", "PENDIENTE confirmar con Nancy"),
        ("Renta Hacienda del Río", 10000, "Mensual", "Confirmado"),
        ("Renta Montecarlo", 9880, "Mensual", "Confirmado"),
        ("Renta San Marcos", 10890, "Mensual", "Confirmado"),
        ("Renta Villas del Rey (est.)", 8000, "Mensual", "PENDIENTE confirmar"),
        ("Renta Pachelli (almacén)", 8740.35, "Mensual", "Confirmado"),
        ("Nómina central (9 empleados)", NOMINA_CENTRAL_SEM * 4.3, "Semanal × 4.3", "Jennifer, Carlos, David, +6"),
        ("Nómina sucursales (17 empleados)", NOMINA_SUCS_SEM * 4.3, "Semanal × 4.3", "Empleados con sucursal fija"),
        ("Abogado Luis", 2500 * 4.3, "Semanal × 4.3", ""),
        ("Juan Muñoz (mantenimiento)", 2000 * 4.3, "Semanal × 4.3", ""),
        ("Pascual Omar Domínguez", 3615 * 4.3, "Semanal × 4.3", "¿Rol pendiente?"),
        ("Préstamo Santander #1 (Andrónica)", 45000, "Mensual", "Del par de préstamos $137k"),
        ("Préstamo Santander #2 (Andrónica)", 92000, "Mensual", "Del par de préstamos $137k"),
        ("Retiro semanal Don Titi (Amex)", 60000 * 4.3, "Semanal × 4.3", "Nómina personal"),
    ]
    fila = 5
    for concepto, monto, freq, nota in rows:
        ws3.cell(fila, 2, concepto).font = F_NORMAL; ws3.cell(fila, 2).alignment = LEFT
        moneda(ws3.cell(fila, 3, monto))
        ws3.cell(fila, 4, freq).font = F_NORMAL; ws3.cell(fila, 4).alignment = CENTER
        ws3.cell(fila, 5, nota).font = F_NOTA; ws3.cell(fila, 5).alignment = LEFT
        fila += 1
    ws3.cell(fila, 2, "TOTAL EGRESOS FIJOS CONOCIDOS").font = F_TOTAL; ws3.cell(fila, 2).fill = FILL_TOTAL; ws3.cell(fila, 2).alignment = LEFT
    c = ws3.cell(fila, 3, f"=SUM(C5:C{fila-1})"); moneda(c); c.font = F_TOTAL; c.fill = FILL_TOTAL
    ws3.cell(fila, 4).fill = FILL_TOTAL; ws3.cell(fila, 5).fill = FILL_TOTAL
    tot_fila = fila
    fila += 2

    section_bar(ws3, "Pendientes por cargar (no incluidos arriba)", fila, 6)
    fila += 1
    for pend in [
        "Proveedores carne (Bona, Julián)",
        "Proveedor pollo (Islas)",
        "Proveedor tocino (Kowi)",
        "Insumos, empaques, papelería",
        "Servicios: luz, gas, agua por sucursal",
        "Comisiones apps (~35-45% del bruto Uber/DiDi/Rappi)",
        "SAT / IMSS / IVA — despacho contable",
        "Otros gastos operativos por sucursal",
    ]:
        ws3.merge_cells(start_row=fila, start_column=2, end_row=fila, end_column=5)
        c = ws3.cell(fila, 2, "•  " + pend); c.font = F_ROJO; c.fill = FILL_ROJO; c.alignment = LEFT
        fila += 1

    bordear(ws3, 4, 2, tot_fila, 5)

    # Pie: composición de egresos fijos
    pie = PieChart()
    pie.title = "Composición egresos fijos"
    # 3 grandes bloques: nómina completa, retiro Don Titi, préstamos, rentas totales, extraordinarios
    # armamos tabla oculta lateral con los agregados
    fila_pie = 5
    ws3.cell(fila_pie, 7, "Bloque").font = F_LABEL
    ws3.cell(fila_pie, 8, "Monto").font = F_LABEL
    bloques = [
        ("Nómina total", NOMINA_MES),
        ("Retiro Don Titi", RETIRO_DON_TITI),
        ("Préstamos Andrónica", PRESTAMO_ANDRONICA),
        ("Rentas", sum(RENTAS.values()) + RENTA_PACHELLI),
        ("Extraordinarios", EXTRAS_MES),
    ]
    for i, (b, m) in enumerate(bloques):
        ws3.cell(fila_pie + 1 + i, 7, b).font = F_NORMAL
        moneda(ws3.cell(fila_pie + 1 + i, 8, m))
    labels_ref = Reference(ws3, min_col=7, min_row=fila_pie + 1, max_row=fila_pie + len(bloques))
    data_ref = Reference(ws3, min_col=8, min_row=fila_pie + 1, max_row=fila_pie + len(bloques))
    pie.add_data(data_ref, titles_from_data=False)
    pie.set_categories(labels_ref)
    pie.dataLabels = DataLabelList(showPercent=True)
    pie.height = 10; pie.width = 15
    ws3.add_chart(pie, f"G{fila_pie + 8}")

    wb.save(path)
    print(f"Guardado: {path}")


if __name__ == "__main__":
    gen_3meses(OUT / "Rentabilidad ultimos 3 meses.xlsx")
    gen_junio(OUT / "Rentabilidad junio detalle.xlsx")
    print("Listo.")
