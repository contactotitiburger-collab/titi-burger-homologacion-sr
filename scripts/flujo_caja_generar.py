#!/usr/bin/env python3
"""Genera dos Excel para Rafael/Don Titi:
1. Rentabilidad — Últimos 3 meses (abr, may, jun 2026).xlsx
2. Rentabilidad — Junio 2026 detalle.xlsx

Datos usados (todos reales al 16-jul-2026):
- Ventas SR por sucursal por mes: ~/.openclaw/data/ventas_12m_por_sucursal.json
- DiDi junio bruto por sucursal: ~/.openclaw/data/didi_junio_2026.json
- Rentas y nóminas confirmadas: catálogo de gastos
- Comisiones plataformas: memoria comisiones-apps-delivery (30 Uber, 27 Rappi, 20 DiDi + PF)

Huecos marcados en rojo (pendientes de dato):
- Proveedores (Bona, Julián, Kowi, Islas)
- Servicios (luz, gas, agua) por sucursal
- Uber junio 2026 (cuenta huérfana)
- Rappi bruto junio (portal Elías)
- Costo por producto (Excel Cocina vacío)
"""
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DATA = Path.home() / ".openclaw/data"
OUT = Path.home() / ".openclaw/workspace/apps_delivery"
OUT.mkdir(parents=True, exist_ok=True)

# --- Cargar fuentes ---
ventas12 = json.loads((DATA / "ventas_12m_por_sucursal.json").read_text())["meses"]
didi_jun = json.loads((DATA / "didi_junio_2026.json").read_text())

SUCURSALES = ["FOVISSTE", "MONTECARLO", "SAN MARCOS", "HACIENDA DEL RÍO", "CURTO", "VILLAS DEL REY"]
MESES = [("2026-04", "Abril"), ("2026-05", "Mayo"), ("2026-06", "Junio")]

# Rentas mensuales confirmadas (del catálogo de gastos)
RENTAS = {
    "FOVISSTE": 24000,       # PENDIENTE
    "MONTECARLO": 9880,
    "SAN MARCOS": 10890,
    "HACIENDA DEL RÍO": 10000,
    "CURTO": 16983,
    "VILLAS DEL REY": 8000,  # PENDIENTE
}
RENTAS_PACHELLI = 8740.35   # Almacén, no sucursal

# Nómina semanal (catálogo de gastos) — mes ≈ 4.3 semanas
NOMINA_CENTRAL_SEM = 32428.63
NOMINA_SUCS_SEM = 67687.44
NOMINA_MES = (NOMINA_CENTRAL_SEM + NOMINA_SUCS_SEM) * 4.3  # ~433,500

# Otros fijos mensuales
PRESTAMO_ANDRONICA_MES = 137000     # 2 préstamos Santander
RETIRO_DON_TITI_MES = 60000 * 4.3   # $60k/semana → Amex

# Extraordinarios semanales identificados
EXTRA_SEMANAL = {
    "Abogado Luis": 2500,
    "Juan Muñoz (mantenimiento)": 2000,
    "Pascual Omar Domínguez": 3615,
}
EXTRA_MES = sum(EXTRA_SEMANAL.values()) * 4.3

# Comisiones apps (PF) — método Meza confirmado
COMISIONES = {
    "Uber":  {"comision": 0.30, "iva_com": 0.16, "iva_ret": 0.08, "isr_ret": 0.025},
    "DiDi":  {"comision": 0.20, "iva_com": 0.16, "iva_ret": 0.08, "isr_ret": 0.025},
    "Rappi": {"comision": 0.27, "iva_com": 0.16, "iva_ret": 0.08, "isr_ret": 0.025},
}

def neto_pf(bruto: float, app: str) -> float:
    """Aplica método Meza para PF: bruto - (com + iva_com + iva_ret + isr_ret)."""
    c = COMISIONES[app]
    monto_com = bruto * c["comision"]
    iva_com = monto_com * c["iva_com"]
    iva_ret = bruto * c["iva_ret"]
    isr_ret = bruto * c["isr_ret"]
    return bruto - monto_com - iva_com - iva_ret - isr_ret


# --- Estilos ---
TITULO = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
SUBTIT = Font(name="Calibri", size=11, bold=True)
NEG = Font(name="Calibri", size=10, bold=True)
NORM = Font(name="Calibri", size=10)
ROJO = Font(name="Calibri", size=10, bold=True, color="C00000")
VERDE_FONT = Font(name="Calibri", size=10, bold=True, color="006100")
FILL_TIT = PatternFill("solid", fgColor="1F4E78")
FILL_HDR = PatternFill("solid", fgColor="D9E1F2")
FILL_ROJO = PatternFill("solid", fgColor="FFC7CE")
FILL_VERDE = PatternFill("solid", fgColor="C6EFCE")
FILL_TOTAL = PatternFill("solid", fgColor="FFF2CC")
B_SIDE = Side(style="thin", color="808080")
BORDE = Border(left=B_SIDE, right=B_SIDE, top=B_SIDE, bottom=B_SIDE)

def hoja_encabezado(ws, titulo: str, cols: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=cols)
    c = ws.cell(1, 1, titulo)
    c.font = TITULO
    c.fill = FILL_TIT
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

def apply_border(ws, r1, c1, r2, c2):
    for r in range(r1, r2+1):
        for c in range(c1, c2+1):
            ws.cell(r, c).border = BORDE

def moneda(cell):
    cell.number_format = '"$"#,##0.00'
    cell.font = NORM


# ==========================================================
#  ARCHIVO 1: Últimos 3 meses (abr, may, jun 2026)
# ==========================================================
def generar_3meses(path: Path):
    wb = Workbook()

    # --- Hoja: Resumen ---
    ws = wb.active
    ws.title = "Resumen"
    hoja_encabezado(ws, "RENTABILIDAD — Últimos 3 meses (Abril, Mayo, Junio 2026)", 6)

    ws.cell(3, 1, "Concepto").font = NEG; ws.cell(3, 1).fill = FILL_HDR
    for i, (_, nombre) in enumerate(MESES):
        c = ws.cell(3, 2+i, nombre); c.font = NEG; c.fill = FILL_HDR
    ws.cell(3, 5, "Promedio").font = NEG; ws.cell(3, 5).fill = FILL_HDR
    ws.cell(3, 6, "Notas").font = NEG; ws.cell(3, 6).fill = FILL_HDR

    fila = 4
    # INGRESOS
    ws.cell(fila, 1, "INGRESOS").font = NEG
    ws.cell(fila, 1).fill = FILL_TOTAL
    fila += 1

    # Ventas SR por mes
    ws.cell(fila, 1, "Ventas Soft Restaurant (6 sucursales)")
    for i, (m, _) in enumerate(MESES):
        total_sr = sum(v.get("subtotal", 0) for v in ventas12[m].values() if isinstance(v, dict))
        c = ws.cell(fila, 2+i, total_sr); moneda(c)
    ws.cell(fila, 5, f"=AVERAGE(B{fila}:D{fila})"); moneda(ws.cell(fila, 5))
    ws.cell(fila, 6, "Subtotal reportado por SR (sin IVA)")
    fila += 1

    # Apps de delivery — junio real DiDi, resto huecos
    ws.cell(fila, 1, "Apps delivery (bruto — antes de comisiones)")
    for i, (m, _) in enumerate(MESES):
        if m == "2026-06":
            c = ws.cell(fila, 2+i, didi_jun["total_bruto"]); moneda(c)
        else:
            c = ws.cell(fila, 2+i, "PENDIENTE"); c.font = ROJO; c.fill = FILL_ROJO
    ws.cell(fila, 5, f"=IFERROR(AVERAGE(B{fila}:D{fila}), \"—\")"); moneda(ws.cell(fila, 5))
    ws.cell(fila, 6, "Solo DiDi jun completo. Uber cta huérfana, Rappi pend Elías")
    fila += 1

    total_ing_row = fila
    ws.cell(fila, 1, "TOTAL INGRESOS ESTIMADO").font = NEG
    for i in range(3):
        col = get_column_letter(2+i)
        f = f"={col}{fila-2}+IFERROR({col}{fila-1},0)"
        c = ws.cell(fila, 2+i, f); moneda(c); c.font = NEG; c.fill = FILL_TOTAL
    ws.cell(fila, 5, f"=AVERAGE(B{fila}:D{fila})"); moneda(ws.cell(fila, 5)); ws.cell(fila, 5).font = NEG
    fila += 2

    # EGRESOS FIJOS
    ws.cell(fila, 1, "EGRESOS FIJOS CONOCIDOS").font = NEG
    ws.cell(fila, 1).fill = FILL_TOTAL
    fila += 1

    fila_ini_egresos = fila
    rentas_total = sum(RENTAS.values()) + RENTAS_PACHELLI
    fixed = [
        ("Rentas (6 sucursales + almacén Pachelli)", rentas_total, "Curto, Montecarlo, San Marcos, Hda Río, Fovissste*, Villas*, Pachelli"),
        ("Nómina (central + sucursales, mensual ≈ 4.3 sem)", NOMINA_MES, "Central $32,428/sem + Sucs $67,687/sem"),
        ("Extraordinarios (Abogado + Muñoz + Pascual)", EXTRA_MES, "$8,115/sem × 4.3"),
        ("Préstamos Andrónica Santander", PRESTAMO_ANDRONICA_MES, "2 préstamos Santander"),
        ("Retiro Don Titi (al Amex)", RETIRO_DON_TITI_MES, "$60k/sem × 4.3"),
    ]
    for concepto, monto, nota in fixed:
        ws.cell(fila, 1, concepto)
        for i in range(3):
            c = ws.cell(fila, 2+i, monto); moneda(c)
        ws.cell(fila, 5, f"=AVERAGE(B{fila}:D{fila})"); moneda(ws.cell(fila, 5))
        ws.cell(fila, 6, nota)
        fila += 1
    fila_fin_egresos = fila - 1

    total_eg_row = fila
    ws.cell(fila, 1, "TOTAL EGRESOS CONOCIDOS").font = NEG
    for i in range(3):
        col = get_column_letter(2+i)
        c = ws.cell(fila, 2+i, f"=SUM({col}{fila_ini_egresos}:{col}{fila_fin_egresos})"); moneda(c); c.font = NEG; c.fill = FILL_TOTAL
    ws.cell(fila, 5, f"=AVERAGE(B{fila}:D{fila})"); moneda(ws.cell(fila, 5)); ws.cell(fila, 5).font = NEG
    fila += 2

    # UTILIDAD ANTES DE PROVEEDORES/SERVICIOS
    ws.cell(fila, 1, "UTILIDAD ANTES DE PROVEEDORES/SERVICIOS").font = NEG
    for i in range(3):
        col = get_column_letter(2+i)
        c = ws.cell(fila, 2+i, f"={col}{total_ing_row}-{col}{total_eg_row}"); moneda(c); c.font = NEG; c.fill = FILL_VERDE
    ws.cell(fila, 5, f"=AVERAGE(B{fila}:D{fila})"); moneda(ws.cell(fila, 5)); ws.cell(fila, 5).font = NEG
    fila += 2

    # HUECOS
    ws.cell(fila, 1, "GASTOS FALTANTES POR CARGAR").font = ROJO
    ws.cell(fila, 1).fill = FILL_ROJO
    fila += 1
    for hueco in [
        ("Proveedores carne (Bona + Julián)", "Pendiente Nancy / facturas Yahoo"),
        ("Proveedor pollo (Islas)", "Pendiente factura"),
        ("Proveedor tocino (Kowi)", "Pendiente factura"),
        ("Insumos, empaques, papelería", "Pendiente"),
        ("Servicios (luz, gas, agua)", "Pizarrón gastos Rafael (13-jul) — Ecogas confirmado, resto pendiente"),
        ("Comisiones apps (deducción sobre bruto)", "Al confirmar bruto Uber+Rappi"),
        ("SAT / IMSS / IVA", "Despacho contable — no tenemos monto"),
    ]:
        ws.cell(fila, 1, hueco[0]).font = ROJO
        for i in range(3):
            c = ws.cell(fila, 2+i, "?"); c.font = ROJO; c.fill = FILL_ROJO
        ws.cell(fila, 6, hueco[1])
        fila += 1

    apply_border(ws, 3, 1, fila-1, 6)

    # anchos columna
    for col, w in [(1, 45), (2, 15), (3, 15), (4, 15), (5, 15), (6, 55)]:
        ws.column_dimensions[get_column_letter(col)].width = w

    # --- Hoja: Ingresos detalle ---
    ws2 = wb.create_sheet("Ingresos detalle")
    hoja_encabezado(ws2, "INGRESOS DETALLE POR SUCURSAL — Últimos 3 meses", 5)
    ws2.cell(3, 1, "Sucursal").font = NEG; ws2.cell(3, 1).fill = FILL_HDR
    for i, (_, nombre) in enumerate(MESES):
        c = ws2.cell(3, 2+i, nombre); c.font = NEG; c.fill = FILL_HDR
    ws2.cell(3, 5, "Tendencia").font = NEG; ws2.cell(3, 5).fill = FILL_HDR

    fila = 4
    for suc in SUCURSALES:
        ws2.cell(fila, 1, suc)
        for i, (m, _) in enumerate(MESES):
            v = ventas12[m].get(suc, {}).get("subtotal", 0)
            c = ws2.cell(fila, 2+i, v); moneda(c)
        col_ult = get_column_letter(2+len(MESES)-1)
        col_pen = get_column_letter(2+len(MESES)-2)
        ws2.cell(fila, 5, f"=IFERROR(({col_ult}{fila}/{col_pen}{fila})-1, \"\")")
        ws2.cell(fila, 5).number_format = "0.0%"
        fila += 1

    ws2.cell(fila, 1, "TOTAL").font = NEG
    for i in range(3):
        col = get_column_letter(2+i)
        c = ws2.cell(fila, 2+i, f"=SUM({col}{fila-6}:{col}{fila-1})"); moneda(c); c.font = NEG; c.fill = FILL_TOTAL

    apply_border(ws2, 3, 1, fila, 5)
    for col, w in [(1, 22), (2, 16), (3, 16), (4, 16), (5, 14)]:
        ws2.column_dimensions[get_column_letter(col)].width = w

    wb.save(path)
    print(f"Guardado: {path}")


# ==========================================================
#  ARCHIVO 2: Junio 2026 detalle
# ==========================================================
def generar_junio(path: Path):
    wb = Workbook()

    # --- Hoja: Resumen junio ---
    ws = wb.active
    ws.title = "Junio detalle"
    hoja_encabezado(ws, "RENTABILIDAD — Junio 2026 detallado por sucursal", 8)

    hdr = ["Sucursal", "Venta SR", "DiDi bruto", "Uber bruto", "Rappi bruto", "Total bruto", "Renta", "% renta/venta"]
    for i, h in enumerate(hdr, 1):
        c = ws.cell(3, i, h); c.font = NEG; c.fill = FILL_HDR

    fila = 4
    ventas_jun = ventas12["2026-06"]
    for suc in SUCURSALES:
        ws.cell(fila, 1, suc)
        sr = ventas_jun.get(suc, {}).get("subtotal", 0)
        moneda(ws.cell(fila, 2, sr))

        didi_key = {
            "FOVISSTE": "L Montejano", "MONTECARLO": "Montecarlo",
            "SAN MARCOS": "San Marcos", "HACIENDA DEL RÍO": "Hda del Río",
            "CURTO": "Curto", "VILLAS DEL REY": "Villas del Rey"
        }.get(suc)
        didi = didi_jun["sucursales"].get(didi_key, {}).get("ingresos_brutos", 0)
        moneda(ws.cell(fila, 3, didi))

        c = ws.cell(fila, 4, "?"); c.font = ROJO; c.fill = FILL_ROJO
        c = ws.cell(fila, 5, "?"); c.font = ROJO; c.fill = FILL_ROJO

        f = f"=B{fila}+C{fila}"
        c = ws.cell(fila, 6, f); moneda(c); c.font = NEG

        moneda(ws.cell(fila, 7, RENTAS[suc]))
        c = ws.cell(fila, 8, f"=G{fila}/B{fila}"); c.number_format = "0.0%"
        fila += 1

    # Totales
    ws.cell(fila, 1, "TOTAL").font = NEG
    for col_i in [2, 3, 6, 7]:
        col = get_column_letter(col_i)
        c = ws.cell(fila, col_i, f"=SUM({col}4:{col}{fila-1})"); moneda(c); c.font = NEG; c.fill = FILL_TOTAL

    apply_border(ws, 3, 1, fila, 8)
    for col, w in [(1, 20), (2, 15), (3, 13), (4, 13), (5, 13), (6, 15), (7, 12), (8, 14)]:
        ws.column_dimensions[get_column_letter(col)].width = w

    fila += 2

    # --- Aplicación método Meza a junio ---
    ws.cell(fila, 1, "APLICACIÓN MÉTODO MEZA (PF) A APPS DE JUNIO").font = SUBTIT
    fila += 1
    hdr2 = ["App", "Bruto", "% Comisión", "Comisión", "IVA comisión (16%)", "IVA retenido (8%)", "ISR retenido (2.5%)", "Neto PF"]
    for i, h in enumerate(hdr2, 1):
        c = ws.cell(fila, i, h); c.font = NEG; c.fill = FILL_HDR
    fila += 1

    total_didi = didi_jun["total_bruto"]
    for app_name, bruto in [("DiDi", total_didi), ("Uber", "?"), ("Rappi", "?")]:
        ws.cell(fila, 1, app_name)
        if isinstance(bruto, (int, float)):
            moneda(ws.cell(fila, 2, bruto))
            c = COMISIONES[app_name]
            ws.cell(fila, 3, c["comision"]).number_format = "0.0%"
            moneda(ws.cell(fila, 4, f"=B{fila}*C{fila}"))
            moneda(ws.cell(fila, 5, f"=D{fila}*0.16"))
            moneda(ws.cell(fila, 6, f"=B{fila}*0.08"))
            moneda(ws.cell(fila, 7, f"=B{fila}*0.025"))
            c8 = ws.cell(fila, 8, f"=B{fila}-D{fila}-E{fila}-F{fila}-G{fila}")
            moneda(c8); c8.font = NEG; c8.fill = FILL_VERDE
        else:
            for i in range(2, 9):
                c = ws.cell(fila, i, "?"); c.font = ROJO; c.fill = FILL_ROJO
        fila += 1

    apply_border(ws, fila-4, 1, fila-1, 8)

    fila += 2

    # --- Top productos (con hueco de costo) ---
    ws.cell(fila, 1, "TOP 10 PRODUCTOS JUNIO 2026 (todas las sucursales) — Costos por definir en Excel Cocina").font = SUBTIT
    fila += 1
    hdr3 = ["Clave", "Producto", "Cantidad", "Precio prom", "Importe s/IVA", "Costo unitario", "Costo total", "Margen"]
    for i, h in enumerate(hdr3, 1):
        c = ws.cell(fila, i, h); c.font = NEG; c.fill = FILL_HDR
    fila += 1

    productos = [
        ("03001", "#2 PAPAS A LA FRANCESA", 1397.00, 3.19, 4455.00),
        ("01001", "#1 TITI CLASICA", 1047.00, 132.42, 138639.00),
        ("01048", "TITI COMBO CLASICA", 763.00, 201.31, 153597.00),
        ("04003", "COCA COLA", 381.00, 13.64, 5195.00),
        ("04002", "JAMAICA", 331.00, 11.51, 3810.00),
        ("04001", "TE", 279.00, 9.14, 2550.00),
        ("01002", "#5 TITI DOBLE CARNE", 221.00, 200.00, 44200.00),
        ("01037", "TITI COMBO DOBLE CARNE", 205.00, 260.00, 53300.00),
        ("04010", "ROOT BEER", 188.00, 8.93, 1679.00),
        ("01039", "TITI COMBO TOCINO", 137.00, 235.00, 32195.00),
    ]
    for clave, prod, cant, precio, importe in productos:
        ws.cell(fila, 1, clave)
        ws.cell(fila, 2, prod)
        ws.cell(fila, 3, cant); ws.cell(fila, 3).number_format = "#,##0"
        moneda(ws.cell(fila, 4, precio))
        moneda(ws.cell(fila, 5, importe))
        c = ws.cell(fila, 6, "?"); c.font = ROJO; c.fill = FILL_ROJO
        c = ws.cell(fila, 7, f'=IFERROR(C{fila}*F{fila}, "")'); moneda(c)
        c = ws.cell(fila, 8, f'=IFERROR(E{fila}-G{fila}, "")'); moneda(c)
        fila += 1

    ws.cell(fila, 1, "→ Para completar 'Costo unitario' hay que llenar el Excel Cocina (~/.openclaw/workspace/TITI_BURGER_COCINA.xlsx)").font = ROJO
    apply_border(ws, fila-11, 1, fila-1, 8)

    # --- Hoja: Egresos junio ---
    ws3 = wb.create_sheet("Egresos junio")
    hoja_encabezado(ws3, "EGRESOS FIJOS — Junio 2026", 4)
    hdr = ["Concepto", "Monto mensual", "Frecuencia origen", "Notas"]
    for i, h in enumerate(hdr, 1):
        c = ws3.cell(3, i, h); c.font = NEG; c.fill = FILL_HDR

    fila = 4
    rows = [
        ("Renta Cine Curto", 16983, "Mensual", "Confirmado"),
        ("Renta Fovissste (est.)", 24000, "Mensual", "PENDIENTE confirmar"),
        ("Renta Hacienda del Río", 10000, "Mensual", "Confirmado"),
        ("Renta Montecarlo", 9880, "Mensual", "Confirmado"),
        ("Renta San Marcos", 10890, "Mensual", "Confirmado"),
        ("Renta Villas del Rey (est.)", 8000, "Mensual", "PENDIENTE confirmar"),
        ("Renta Pachelli (almacén)", 8740.35, "Mensual", "Confirmado"),
        ("Nómina central (9 empl)", NOMINA_CENTRAL_SEM * 4.3, "Semanal x 4.3", "Jennifer, Carlos, David, +6"),
        ("Nómina sucursales (17 empl)", NOMINA_SUCS_SEM * 4.3, "Semanal x 4.3", "Empleados con sucursal fija"),
        ("Abogado Luis", 2500 * 4.3, "Semanal x 4.3", ""),
        ("Juan Muñoz (mantenimiento)", 2000 * 4.3, "Semanal x 4.3", ""),
        ("Pascual Omar Domínguez", 3615 * 4.3, "Semanal x 4.3", "¿Rol pendiente?"),
        ("Préstamo Santander #1 (Andrónica)", 45000, "Mensual", "Del par de préstamos $137k"),
        ("Préstamo Santander #2 (Andrónica)", 92000, "Mensual", "Del par de préstamos $137k"),
        ("Retiro semanal Don Titi (Amex)", 60000 * 4.3, "Semanal x 4.3", "Nómina personal"),
    ]
    for concepto, monto, freq, nota in rows:
        ws3.cell(fila, 1, concepto)
        moneda(ws3.cell(fila, 2, monto))
        ws3.cell(fila, 3, freq)
        ws3.cell(fila, 4, nota)
        fila += 1

    ws3.cell(fila, 1, "TOTAL EGRESOS FIJOS CONOCIDOS").font = NEG
    ws3.cell(fila, 1).fill = FILL_TOTAL
    c = ws3.cell(fila, 2, f"=SUM(B4:B{fila-1})"); moneda(c); c.font = NEG; c.fill = FILL_TOTAL
    fila += 2

    ws3.cell(fila, 1, "GASTOS PENDIENTES (no incluidos arriba)").font = ROJO
    ws3.cell(fila, 1).fill = FILL_ROJO
    fila += 1
    for pend in [
        "Proveedores carne (Bona, Julián)",
        "Proveedor pollo (Islas)",
        "Proveedor tocino (Kowi)",
        "Insumos, empaques, papelería",
        "Servicios: luz, gas, agua (por sucursal)",
        "Comisiones apps (~40% del bruto Uber/DiDi/Rappi)",
        "SAT / IMSS / IVA (despacho contable)",
        "Otros gastos operativos por sucursal",
    ]:
        c = ws3.cell(fila, 1, pend); c.font = ROJO; c.fill = FILL_ROJO
        fila += 1

    apply_border(ws3, 3, 1, fila-1, 4)
    for col, w in [(1, 35), (2, 16), (3, 20), (4, 40)]:
        ws3.column_dimensions[get_column_letter(col)].width = w

    wb.save(path)
    print(f"Guardado: {path}")


if __name__ == "__main__":
    generar_3meses(OUT / "Rentabilidad ultimos 3 meses.xlsx")
    generar_junio(OUT / "Rentabilidad junio detalle.xlsx")
    print("Listo.")
