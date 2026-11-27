#!/usr/bin/env python3
"""Construye TITI_BURGER_COCINA.xlsx — auxiliar para calcular el % Cocina del Maestro.

Estructura alineada al MAESTRO (paleta, reglas, IF para evitar #DIV/0):
  Hoja 1: 🥩 Costo Cocina  (procesos individuales)
  Hoja 2: 💰 Costos Fijos Cocina (referencia mensual)
  Hoja 3: 📖 Cómo usar (instrucciones cortas)
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

OUT = "/home/tito/.openclaw/workspace/TITI_BURGER_COCINA.xlsx"

# Paleta heredada del Maestro
VERDE_OSC   = "375623"
VERDE_CLARO = "E2EFDA"
VERDE_K     = "C6EFCE"
VERDE_L     = "A9D08E"
BLANCO      = "FFFFFF"
GRIS_HEAD   = "70AD47"

font_white_bold = Font(name="Calibri", size=11, bold=True, color=BLANCO)
font_input      = Font(name="Calibri", size=11, color=VERDE_OSC, bold=True)
font_formula    = Font(name="Calibri", size=11, color="000000")
font_title      = Font(name="Calibri", size=16, bold=True, color=VERDE_OSC)
font_subtitle   = Font(name="Calibri", size=11, italic=True, color="595959")

fill_header   = PatternFill("solid", fgColor=VERDE_OSC)
fill_input    = PatternFill("solid", fgColor=VERDE_CLARO)
fill_formula  = PatternFill("solid", fgColor=BLANCO)
fill_k        = PatternFill("solid", fgColor=VERDE_K)
fill_l        = PatternFill("solid", fgColor=VERDE_L)

center = Alignment(horizontal="center", vertical="center", wrap_text=True)
left   = Alignment(horizontal="left",   vertical="center", wrap_text=True)
right  = Alignment(horizontal="right",  vertical="center", wrap_text=True)

thin  = Side(border_style="thin", color="BFBFBF")
border_all = Border(left=thin, right=thin, top=thin, bottom=thin)


def style_header_row(ws, row, last_col):
    for c in range(1, last_col + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = font_white_bold
        cell.fill = fill_header
        cell.alignment = center
        cell.border = border_all
    ws.row_dimensions[row].height = 38


def build_hoja_costo_cocina(wb):
    ws = wb.active
    ws.title = "🥩 Costo Cocina"

    # Título + bajada
    ws["A1"] = "🥩 COSTO COCINA — Cálculo del % Cocina por proceso"
    ws["A1"].font = font_title
    ws.merge_cells("A1:N1")
    ws["A1"].alignment = left

    ws["A2"] = ("Cocina compra crudo, transforma y entrega a Titi Burger. "
                "Calculamos DOS números: el % del PUNTO DE EQUILIBRIO (col K, lo que cuesta "
                "producir sin ganar) y el % FINAL (col L, equilibrio + margen). El L se "
                "linkea al Maestro col H usando el ID-Maestro de la col M.")
    ws["A2"].font = font_subtitle
    ws.merge_cells("A2:N2")
    ws["A2"].alignment = left
    ws.row_dimensions[2].height = 32

    # Encabezados (fila 4)
    headers = [
        ("A", "ID-PROC",                   12),
        ("B", "Producto procesado",        28),
        ("C", "Unidad\n(kg / lt / pza)",   12),
        ("D", "Costo crudo\n$/unidad",     14),
        ("E", "Mano de obra\n$/unidad",    14),
        ("F", "Servicios\n$/unidad",       13),
        ("G", "Mermas %",                  11),
        ("H", "Costo total\n$/unidad\n(= PUNTO EQUILIBRIO $)", 16),
        ("I", "Margen Cocina %",           14),
        ("J", "Precio Venta Cocina\n$/unidad", 18),
        ("K", "% Punto Equilibrio\nvs Crudo (real)", 18),
        ("L", "% Final vs Crudo\n(→ Maestro col H)", 18),
        ("M", "ID-Maestro\n(mapeo)",       14),
        ("N", "Notas",                     30),
    ]
    for col_letter, label, width in headers:
        ws[f"{col_letter}4"] = label
        ws.column_dimensions[col_letter].width = width
    style_header_row(ws, 4, len(headers))

    # Datos semilla — productos reales que procesa la cocina (Staff dictó)
    # CONFIRMAR unidades (kg vs pza) con Staff.
    # ID-Maestro: mapeo al TITI_BURGER_MAESTRO.xlsx para linkear el % Cocina (col L)
    seed = [
        ("Boneless",                "kg",  None, None, None, None, None, "INS-029", "Pollo empanizado. INS-029 = 320g; INS-030 = 180g (1/2 orden) jala mismo %"),
        ("Dedos de queso",          "pza", None, None, None, None, None, "—",       "⚠️ NO existe en Maestro — agregar fila INS nueva o quitar"),
        ("Tiras de pollo empanizado","kg", None, None, None, None, None, "—",       "⚠️ NO existe en Maestro — agregar fila INS nueva o quitar"),
        ("Tocino",                  "kg",  None, None, None, None, None, "INS-037", ""),
        ("Patty (carne molida en casa)","pza",None,None,None,None,None,"INS-031",  "INS-031 = CARNE PAQ / 20 PZA. Se muele y mezcla en cocina."),
        ("Pollo",                   "kg",  None, None, None, None, None, "INS-035", "Filete / pieza"),
    ]

    start_row = 5
    for i, row_data in enumerate(seed):
        r = start_row + i
        producto, unidad, d, e, f, g, ide_margen, id_maestro, notas = row_data
        ws.cell(row=r, column=1, value=f"PROC-{i+1:03d}")
        ws.cell(row=r, column=2, value=producto)
        ws.cell(row=r, column=3, value=unidad)
        ws.cell(row=r, column=4, value=d)
        ws.cell(row=r, column=5, value=e)
        ws.cell(row=r, column=6, value=f)
        ws.cell(row=r, column=7, value=g)
        # H: Costo total = (D + E + F) / (1 - G)  ← PUNTO DE EQUILIBRIO en $
        ws.cell(row=r, column=8,
                value=f'=IF(OR(D{r}="",E{r}="",F{r}="",G{r}=""),"",(D{r}+E{r}+F{r})/(1-G{r}))')
        ws.cell(row=r, column=9, value=ide_margen)
        # J: Precio venta cocina = H * (1 + I)
        ws.cell(row=r, column=10,
                value=f'=IF(OR(H{r}="",I{r}=""),"",H{r}*(1+I{r}))')
        # K: % Punto Equilibrio vs Crudo = H/D - 1   (lo que cuesta producir, sin margen)
        ws.cell(row=r, column=11,
                value=f'=IF(OR(H{r}="",D{r}="",D{r}=0),"",H{r}/D{r}-1)')
        # L: % Final vs Crudo = J/D - 1   (el que va al Maestro)
        ws.cell(row=r, column=12,
                value=f'=IF(OR(J{r}="",D{r}="",D{r}=0),"",J{r}/D{r}-1)')
        # M: ID-Maestro (mapeo)
        ws.cell(row=r, column=13, value=id_maestro)
        # N: Notas
        ws.cell(row=r, column=14, value=notas)

    # Estilos por columna (filas 5..start_row+len(seed)-1) + 10 extras vacías para crecer
    last_row = start_row + len(seed) - 1 + 10
    for r in range(start_row, last_row + 1):
        for c in range(1, 15):
            cell = ws.cell(row=r, column=c)
            cell.border = border_all
            cell.alignment = center if c not in (2, 14) else left
            # Por columna
            if c == 1:  # ID
                cell.fill = fill_formula
                cell.font = Font(name="Calibri", size=10, color="808080", bold=True)
                if cell.value is None:
                    cell.value = f"PROC-{r-start_row+1:03d}"
            elif c == 2:  # Producto
                cell.fill = fill_input
                cell.font = font_input
            elif c == 3:  # Unidad
                cell.fill = fill_input
                cell.font = font_input
            elif c in (4, 5, 6):  # D, E, F = inputs $
                cell.fill = fill_input
                cell.font = font_input
                cell.number_format = '"$"#,##0.00'
            elif c == 7:  # G = input %
                cell.fill = fill_input
                cell.font = font_input
                cell.number_format = "0.0%"
            elif c == 8:  # H = fórmula $  ← Punto equilibrio
                cell.fill = fill_k
                cell.font = font_formula
                cell.number_format = '"$"#,##0.00'
            elif c == 9:  # I = input %
                cell.fill = fill_input
                cell.font = font_input
                cell.number_format = "0.0%"
            elif c == 10:  # J = fórmula $
                cell.fill = fill_k
                cell.font = font_formula
                cell.number_format = '"$"#,##0.00'
            elif c == 11:  # K = % Punto Equilibrio (sin margen)
                cell.fill = fill_k
                cell.font = Font(name="Calibri", size=11, bold=True, color="595959")
                cell.number_format = "0.0%"
            elif c == 12:  # L = % Final (→ Maestro), el dato clave
                cell.fill = fill_l
                cell.font = Font(name="Calibri", size=11, bold=True)
                cell.number_format = "0.0%"
            elif c == 13:  # M = ID-Maestro (mapeo)
                cell.fill = fill_input
                cell.font = font_input
            elif c == 14:  # N = Notas
                cell.fill = fill_input
                cell.font = font_input
        ws.row_dimensions[r].height = 22

    # Asegurar IDs para las filas extras
    for i in range(len(seed), len(seed) + 10):
        r = start_row + i
        ws.cell(row=r, column=1, value=f"PROC-{i+1:03d}")
        ws.cell(row=r, column=1).fill = fill_formula
        ws.cell(row=r, column=1).font = Font(name="Calibri", size=10, color="808080", bold=True)

    # Freeze header
    ws.freeze_panes = "B5"


def build_hoja_costos_fijos(wb):
    ws = wb.create_sheet("💰 Costos Fijos Cocina")

    ws["A1"] = "💰 COSTOS FIJOS DE COCINA (referencia mensual)"
    ws["A1"].font = font_title
    ws.merge_cells("A1:D1")
    ws["A1"].alignment = left

    ws["A2"] = ("Sirve para estimar 'Mano de obra $/unidad' y 'Servicios $/unidad' "
                "de la otra hoja. Total $/mes ÷ volumen mensual = costo por unidad.")
    ws["A2"].font = font_subtitle
    ws.merge_cells("A2:D2")
    ws["A2"].alignment = left
    ws.row_dimensions[2].height = 32

    headers = [("A", "Concepto", 32), ("B", "$ / mes", 16), ("C", "% asignado a cocina", 18),
               ("D", "Notas", 40)]
    for col_letter, label, width in headers:
        ws[f"{col_letter}4"] = label
        ws.column_dimensions[col_letter].width = width
    style_header_row(ws, 4, len(headers))

    rows = [
        ("Nómina cocineros",         None, 1.0,  "Sueldos brutos + prestaciones"),
        ("Renta — parte cocina",     None, None, "Si la cocina es compartida, % del espacio"),
        ("Luz cocina",               None, None, "Estimado o % del recibo"),
        ("Gas",                      None, 1.0,  "Recarga mensual de tanque"),
        ("Agua cocina",              None, None, ""),
        ("Mantenimiento equipo",     None, 1.0,  "Promedio mensual"),
        ("Limpieza / químicos",      None, 1.0,  ""),
        ("Empaques cocina interna",  None, 1.0,  "Bolsas, film, contenedores"),
        ("Mermas no registradas",    None, 1.0,  "Buffer por desperdicios sin contabilizar"),
        ("Otros (especificar)",      None, 1.0,  ""),
    ]
    start = 5
    for i, (concepto, monto, pct, notas) in enumerate(rows):
        r = start + i
        ws.cell(row=r, column=1, value=concepto)
        ws.cell(row=r, column=2, value=monto)
        ws.cell(row=r, column=3, value=pct)
        ws.cell(row=r, column=4, value=notas)
    last = start + len(rows) - 1

    # Total
    total_row = last + 2
    ws.cell(row=total_row, column=1, value="TOTAL costos fijos / mes asignados a cocina")
    ws.cell(row=total_row, column=2, value=f"=SUMPRODUCT(B{start}:B{last},C{start}:C{last})")

    # Estilos
    for r in range(start, last + 1):
        for c in range(1, 5):
            cell = ws.cell(row=r, column=c)
            cell.border = border_all
            cell.alignment = left if c in (1, 4) else center
            if c == 1:
                cell.fill = fill_formula
                cell.font = Font(name="Calibri", size=11, bold=True, color=VERDE_OSC)
            elif c == 2:
                cell.fill = fill_input
                cell.font = font_input
                cell.number_format = '"$"#,##0.00'
            elif c == 3:
                cell.fill = fill_input
                cell.font = font_input
                cell.number_format = "0%"
            else:
                cell.fill = fill_input
                cell.font = font_input
        ws.row_dimensions[r].height = 22

    # Fila total
    for c in range(1, 5):
        cell = ws.cell(row=total_row, column=c)
        cell.border = border_all
        cell.fill = fill_l
        cell.font = Font(name="Calibri", size=12, bold=True, color=VERDE_OSC)
    ws.cell(row=total_row, column=2).number_format = '"$"#,##0.00'
    ws.cell(row=total_row, column=2).alignment = right

    # Bloque MO calculada (driver principal según Staff)
    mo_title = total_row + 3
    ws.cell(row=mo_title, column=1, value="🧮 TARIFA MANO DE OBRA (driver principal)")
    ws.cell(row=mo_title, column=1).font = font_title
    ws.merge_cells(start_row=mo_title, end_row=mo_title, start_column=1, end_column=4)

    mo_rows = [
        ("Nómina cocineras / mes (total)", None, '"$"#,##0.00',
         "Sueldos brutos del equipo de cocina"),
        ("Horas trabajadas / mes (todo el equipo)", None, "#,##0",
         "Ej: 3 cocineras × 8h × 26 días = 624 h"),
        ("$/hora MO", None, '"$"#,##0.00', "Calculado"),
        ("$/minuto MO ← este lo usa en la hoja Costo Cocina (col E)",
         None, '"$"#,##0.00', "Multiplique por los min/unidad de cada proceso"),
    ]
    for i, (concepto, val, fmt, notas) in enumerate(mo_rows):
        r = mo_title + 1 + i
        ws.cell(row=r, column=1, value=concepto)
        ws.cell(row=r, column=4, value=notas)
        c2 = ws.cell(row=r, column=2)
        c2.number_format = fmt
        if i < 2:
            c2.value = val
            c2.fill = fill_input
            c2.font = font_input
        elif i == 2:
            c2.value = f'=IF(OR(B{mo_title+1}="",B{mo_title+2}="",B{mo_title+2}=0),"",B{mo_title+1}/B{mo_title+2})'
            c2.fill = fill_k
            c2.font = font_formula
        else:
            c2.value = f'=IF(B{mo_title+3}="","",B{mo_title+3}/60)'
            c2.fill = fill_l
            c2.font = Font(name="Calibri", size=12, bold=True, color=VERDE_OSC)
        for c in range(1, 5):
            cell = ws.cell(row=r, column=c)
            cell.border = border_all
            cell.alignment = left if c in (1, 4) else right
            if c == 1:
                cell.font = Font(name="Calibri", size=11, bold=True, color=VERDE_OSC)
        ws.row_dimensions[r].height = 22

    # Bloque de volumen mensual (debajo del total) — para servicios prorrateados
    vol_title = mo_title + len(mo_rows) + 2
    ws.cell(row=vol_title, column=1, value="📦 VOLUMEN MENSUAL (para prorratear gas/luz en col F de hoja 1)")
    ws.cell(row=vol_title, column=1).font = font_title
    ws.merge_cells(start_row=vol_title, end_row=vol_title, start_column=1, end_column=4)

    ws.cell(row=vol_title + 1, column=1, value="Unidades totales procesadas / mes")
    ws.cell(row=vol_title + 1, column=2, value=None)
    ws.cell(row=vol_title + 1, column=2).fill = fill_input
    ws.cell(row=vol_title + 1, column=2).font = font_input
    ws.cell(row=vol_title + 1, column=2).number_format = "#,##0"

    ws.cell(row=vol_title + 2, column=1, value="Servicios $/unidad sugerido (gas+luz prorrateados)")
    ws.cell(row=vol_title + 2, column=2,
            value=(f'=IF(OR(B{vol_title+1}="",B{vol_title+1}=0),"",'
                   f'(SUMIFS(B{start}:B{last},A{start}:A{last},"Gas")+'
                   f'SUMIFS(B{start}:B{last},A{start}:A{last},"Luz cocina"))/B{vol_title+1})'))
    ws.cell(row=vol_title + 2, column=2).fill = fill_l
    ws.cell(row=vol_title + 2, column=2).font = Font(name="Calibri", size=12, bold=True, color=VERDE_OSC)
    ws.cell(row=vol_title + 2, column=2).number_format = '"$"#,##0.00'

    for r in [vol_title + 1, vol_title + 2]:
        for c in range(1, 5):
            cell = ws.cell(row=r, column=c)
            cell.border = border_all
            cell.alignment = left if c == 1 else right
            if c == 1:
                cell.font = Font(name="Calibri", size=11, bold=True, color=VERDE_OSC)
        ws.row_dimensions[r].height = 22


def build_hoja_como_usar(wb):
    ws = wb.create_sheet("📖 Cómo usar")

    ws["A1"] = "📖 CÓMO USAR ESTE EXCEL"
    ws["A1"].font = font_title
    ws.merge_cells("A1:B1")
    ws["A1"].alignment = left

    pasos = [
        ("1.",  "Llene COSTOS FIJOS COCINA (hoja 2) primero — meta los $/mes reales."),
        ("",    "    Incluya el volumen mensual total de unidades que sale de cocina."),
        ("",    "    Eso le da un 'costo fijo $/unidad sugerido' (al final de la hoja 2)."),
        ("2.",  "Vaya a COSTO COCINA (hoja 1). Por cada producto que cocina procesa:"),
        ("",    "    D = Costo crudo $/unidad (del Maestro de costos, ya tiene los insumos)."),
        ("",    "    E = Mano de obra $/unidad (estimado por receta o promedio)."),
        ("",    "    F = Servicios $/unidad (puede usar el sugerido de la hoja 2)."),
        ("",    "    G = Mermas % (10% típico; el desperdicio que se va a la basura)."),
        ("",    "    I = Margen Cocina % (ganancia que quiere cocina, 15–25% sugerido)."),
        ("3.",  "El Excel calcula solo: H (punto equilibrio $), J (precio venta cocina), K, L."),
        ("4.",  "Dos números clave:"),
        ("",    "    K = % PUNTO EQUILIBRIO vs crudo (lo que cuesta producirlo, SIN ganar nada)."),
        ("",    "    L = % FINAL vs crudo (equilibrio + margen). Este es el que va al Maestro."),
        ("",    "    M = ID-Maestro (mapeo). Le dice al Maestro a qué fila linkear el L."),
        ("",    ""),
        ("REGLAS:", ""),
        ("•", "Celdas VERDE CLARO = inputs (las llena usted)."),
        ("•", "Celdas BLANCAS = fórmulas (no las toque)."),
        ("•", "Celdas VERDE FUERTE (K) = el resultado clave que va al Maestro."),
        ("•", "No renombre las hojas ni borre las columnas — las fórmulas dependen."),
    ]

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 100

    for i, (num, texto) in enumerate(pasos):
        r = 3 + i
        ws.cell(row=r, column=1, value=num).font = Font(name="Calibri", size=11, bold=True, color=VERDE_OSC)
        ws.cell(row=r, column=2, value=texto).font = Font(name="Calibri", size=11)
        ws.cell(row=r, column=1).alignment = left
        ws.cell(row=r, column=2).alignment = left
        ws.row_dimensions[r].height = 20


def main():
    wb = Workbook()
    build_hoja_costo_cocina(wb)
    build_hoja_costos_fijos(wb)
    build_hoja_como_usar(wb)
    wb.save(OUT)
    print(f"OK: {OUT}")


if __name__ == "__main__":
    main()
