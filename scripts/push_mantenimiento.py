#!/usr/bin/env python3
"""TITI_BURGER_MANTENIMIENTO — Excel de mantenimiento de planta y equipo.

Estructura:
  📋 Resumen Mantenimiento  — vista global, $ anual por sucursal
  📅 Calendario Anual       — qué toca cada mes
  💸 Costos Anuales         — total programado + prorrateo de mixtos
  🍳 Cocina Central         — equipos grandes (cuartos fríos, refri industrial)
  🏪 A · L Montejano        — equipos de esa carreta
  🏪 B · Hacienda del Río
  🏪 C · Montecarlo
  🏪 D · Villas del Rey
  🏪 E · San Marcos
  🏪 Cine Curto
  🔄 Mixtos / Compartidos   — equipos compartidos con % de prorrateo

Estilo Maestro: header #375623, inputs #E2EFDA, valores clave #A9D08E.
Locale en_US para que las fórmulas con coma funcionen.
"""
import gspread
from google.oauth2 import service_account
from time import sleep

SA       = "/home/tito/.openclaw/credentials/google/service-account.json"
SHEET_ID = "1ib8yMqhrpbdxb771t0W-97CD6sPmqGBkN8kjT_pTWLQ"

# Paleta del Maestro
VERDE_OSC   = {"red": 0x37/255, "green": 0x56/255, "blue": 0x23/255}
VERDE_CLARO = {"red": 0xE2/255, "green": 0xEF/255, "blue": 0xDA/255}
VERDE_MED   = {"red": 0xC6/255, "green": 0xEF/255, "blue": 0xCE/255}
VERDE_FUE   = {"red": 0xA9/255, "green": 0xD0/255, "blue": 0x8E/255}
GRIS_CLARO  = {"red": 0xF2/255, "green": 0xF2/255, "blue": 0xF2/255}
GRIS_OSC    = {"red": 0x59/255, "green": 0x59/255, "blue": 0x59/255}
BLANCO      = {"red": 1.0, "green": 1.0, "blue": 1.0}
NEGRO       = {"red": 0.0, "green": 0.0, "blue": 0.0}

FMT_MONEY   = {"type": "CURRENCY", "pattern": "\"$\"#,##0.00"}
FMT_MONEY_F = {"type": "CURRENCY", "pattern": "\"$\"#,##0.00;;\"-\""}
FMT_PCT     = {"type": "PERCENT",  "pattern": "0%"}
FMT_INT     = {"type": "NUMBER",   "pattern": "#,##0"}
FMT_DATE    = {"type": "DATE",     "pattern": "dd/mm/yyyy"}


# Sucursales (slug, nombre hoja, label corto para Resumen)
SUCURSALES = [
    ("cocina_central", "🍳 Cocina Central",      "Cocina Central"),
    ("a_montejano",    "🏪 A · L Montejano",     "L Montejano (A)"),
    ("b_hacienda",     "🏪 B · Hacienda del Río","Hacienda del Río (B)"),
    ("c_montecarlo",   "🏪 C · Montecarlo",      "Montecarlo (C)"),
    ("d_villas",       "🏪 D · Villas del Rey",  "Villas del Rey (D)"),
    ("e_san_marcos",   "🏪 E · San Marcos",      "San Marcos (E)"),
    ("f_cine_curto",   "🏪 Cine Curto",          "Cine Curto"),
]

# Equipos típicos para CADA CARRETA (no Cocina Central)
# (equipo, frecuencia_texto, veces_al_año, notas)
EQUIPOS_CARRETA = [
    ("Trampa de grasa",          "Mensual",        12, "Limpieza periódica"),
    ("Campana de cocina",        "Mensual",        12, "Desengrase + filtros"),
    ("Extractor",                "Mensual",        12, "Limpieza + revisión"),
    ("Plancha / parrilla",       "Mensual",        12, "Limpieza profunda"),
    ("Freidora",                 "Mensual",        12, "Cambio aceite + limpieza"),
    ("Refrigeración (refri/congelador)", "Anual",  1,  "Revisión compresor + gas"),
    ("Extintores (recarga)",     "Anual",          1,  "Obligatorio por NOM"),
    ("POS / Computadora",        "Anual",          1,  "Mantenimiento técnico"),
    ("Iluminación / Eléctrico",  "Semestral",      2,  "Revisión instalación"),
    ("Plomería / Baños",         "Extraordinario", 0,  "Solo cuando falla"),
]

# Cocina Central — equipos más grandes
EQUIPOS_COCINA_CENTRAL = [
    ("Cuartos fríos",            "Semestral",      2,  "Revisión compresor + cierres"),
    ("Refrigeración industrial", "Anual",          1,  "Compresores grandes"),
    ("Trampa de grasa central",  "Mensual",        12, "Mayor capacidad que carretas"),
    ("Campana industrial",       "Mensual",        12, "Desengrase pesado"),
    ("Extractor industrial",     "Mensual",        12, ""),
    ("Plancha industrial",       "Mensual",        12, ""),
    ("Hornos / Estufas",         "Trimestral",     4,  ""),
    ("Lavavajillas",             "Trimestral",     4,  ""),
    ("Molino de carne",          "Mensual",        12, "Crítico para patty"),
    ("Freidora industrial",      "Mensual",        12, ""),
    ("Báscula / Balanzas",       "Anual",          1,  "Calibración"),
    ("Extintores cocina",        "Anual",          1,  "Obligatorio"),
]

# Mixtos — contratos compartidos entre sucursales (con prorrateo)
EQUIPOS_MIXTOS = [
    ("Fumigación / Control de plagas",  "Mensual",   12, "Contrato cubre todas las sucursales"),
    ("Limpieza profunda contratada",    "Trimestral", 4, "Empresa que va a todas"),
    ("Internet / Telefonía",            "Mensual",   12, "Servicio general"),
    ("Sistema de cámaras / Vigilancia", "Anual",     1,  "Mantenimiento técnico"),
    ("Tinacos / Cisternas / Agua",      "Semestral", 2,  "Limpieza y revisión"),
    ("Letreros / Rótulos exteriores",   "Anual",     1,  "Pintura y luz"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de formato (genera batch_update requests)
# ─────────────────────────────────────────────────────────────────────────────

def _rng(sid, r1, c1, r2, c2):
    return {"sheetId": sid, "startRowIndex": r1, "endRowIndex": r2,
            "startColumnIndex": c1, "endColumnIndex": c2}

def fmt_title(sid, row, n_cols):
    return [
        {"mergeCells": {"range": _rng(sid, row, 0, row+1, n_cols), "mergeType": "MERGE_ALL"}},
        {"repeatCell": {
            "range": _rng(sid, row, 0, row+1, n_cols),
            "cell": {"userEnteredFormat": {
                "backgroundColor": VERDE_OSC,
                "textFormat": {"foregroundColor": BLANCO, "bold": True, "fontSize": 14},
                "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS", "startIndex": row, "endIndex": row+1},
            "properties": {"pixelSize": 32}, "fields": "pixelSize"}},
    ]

def fmt_subtitle(sid, row, n_cols):
    return [
        {"mergeCells": {"range": _rng(sid, row, 0, row+1, n_cols), "mergeType": "MERGE_ALL"}},
        {"repeatCell": {
            "range": _rng(sid, row, 0, row+1, n_cols),
            "cell": {"userEnteredFormat": {
                "textFormat": {"foregroundColor": GRIS_OSC, "fontSize": 10},
                "horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}}]

def fmt_header_row(sid, row, n_cols):
    return [{"repeatCell": {
        "range": _rng(sid, row, 0, row+1, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_OSC,
            "textFormat": {"foregroundColor": BLANCO, "bold": True, "fontSize": 10},
            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP",
            "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"},
                        "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy,borders)"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS", "startIndex": row, "endIndex": row+1},
            "properties": {"pixelSize": 38}, "fields": "pixelSize"}}]

def fmt_section_label(sid, row, n_cols):
    return [
        {"mergeCells": {"range": _rng(sid, row, 0, row+1, n_cols), "mergeType": "MERGE_ALL"}},
        {"repeatCell": {
            "range": _rng(sid, row, 0, row+1, n_cols),
            "cell": {"userEnteredFormat": {
                "backgroundColor": VERDE_CLARO,
                "textFormat": {"foregroundColor": VERDE_OSC, "bold": True, "fontSize": 11},
                "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"}}]

def fmt_input(sid, r1, c1, r2, c2, number_fmt=None):
    cell = {"backgroundColor": VERDE_CLARO,
            "textFormat": {"foregroundColor": VERDE_OSC, "fontSize": 10},
            "horizontalAlignment": "CENTER"}
    fields = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment"
    if number_fmt:
        cell["numberFormat"] = number_fmt
        fields += ",numberFormat"
    fields += ")"
    return [{"repeatCell": {"range": _rng(sid, r1, c1, r2, c2),
                            "cell": {"userEnteredFormat": cell}, "fields": fields}}]

def fmt_formula(sid, r1, c1, r2, c2, number_fmt=None, highlight=False):
    bg = VERDE_FUE if highlight else BLANCO
    cell = {"backgroundColor": bg,
            "textFormat": {"foregroundColor": NEGRO, "bold": True, "fontSize": 10},
            "horizontalAlignment": "CENTER"}
    fields = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment"
    if number_fmt:
        cell["numberFormat"] = number_fmt
        fields += ",numberFormat"
    fields += ")"
    return [{"repeatCell": {"range": _rng(sid, r1, c1, r2, c2),
                            "cell": {"userEnteredFormat": cell}, "fields": fields}}]

def col_width(sid, idx, width):
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": idx, "endIndex": idx+1},
        "properties": {"pixelSize": width}, "fields": "pixelSize"}}


# ─────────────────────────────────────────────────────────────────────────────
# Builders por hoja
# ─────────────────────────────────────────────────────────────────────────────

def build_hoja_sucursal(ws, ss, slug, sheet_name, label, equipos):
    """Hoja de equipos de una sucursal/carreta (o Cocina Central) — 12 cols.

    Columnas:
      A ID | B Equipo | C Frecuencia | D Veces/año | E Último | F Próximo SUGERIDO
      G Próximo REAL (override) | H Estado | I Proveedor | J $/servicio | K $ Anual | L Notas
    """
    sid = ws.id
    ws.clear()

    headers = ["ID", "Equipo", "Frecuencia", "Veces /\naño", "Último servicio",
               "Próximo\nSUGERIDO\n(auto)", "Próximo REAL\n(override)", "Estado",
               "Proveedor", "$ por servicio", "$ Anual\n(= J × D)", "Notas"]
    n_cols = 12

    rows = [
        [f"🛠️ {label.upper()} — Mantenimiento y Equipo"] + [""]*(n_cols-1),
        ["Próximo SUGERIDO se calcula solo. Para aplazar: meta fecha en Próximo REAL. Marque Estado al hacer/aplazar."] + [""]*(n_cols-1),
        [""] * n_cols,
        ["EQUIPOS PROGRAMADOS"] + [""]*(n_cols-1),
        headers,
    ]

    REC_FIRST = 6
    for i, (equipo, freq, veces, notas) in enumerate(equipos):
        r = REC_FIRST + i
        rows.append([
            f"MTN-{slug[:3].upper()}-{i+1:03d}",
            equipo,
            freq,
            veces if veces > 0 else "",
            "",  # E último servicio (input fecha)
            f'=IF(OR(E{r}="",D{r}="",D{r}=0),"",EDATE(E{r},12/D{r}))',  # F próximo sugerido
            "",  # G próximo REAL (override input)
            "Pendiente",  # H estado default
            "",  # I proveedor
            "",  # J $ servicio
            f'=IF(OR(J{r}="",D{r}=""),0,J{r}*D{r})',  # K $ anual
            notas,
        ])
    REC_LAST = REC_FIRST + len(equipos) - 1

    # Total anual
    rows.append([""]*n_cols)
    total_row = len(rows) + 1
    rows.append(["", "TOTAL ANUAL PROGRAMADO", "", "", "", "", "", "", "", "",
                 f"=SUM(K{REC_FIRST}:K{REC_LAST})", ""])

    # Sección Extraordinarios
    rows.append([""]*n_cols)
    rows.append([""]*n_cols)
    extra_header_row = len(rows) + 1
    rows.append(["EXTRAORDINARIOS (cuando algo se descompone fuera de calendario)"] + [""]*(n_cols-1))
    rows.append(["Fecha", "Equipo", "Descripción del problema", "", "", "", "", "",
                 "Proveedor", "$ Pagado", "", "Notas"])
    extra_first = len(rows) + 1
    for _ in range(8):
        rows.append([""]*n_cols)
    extra_last = len(rows)
    rows.append([""]*n_cols)
    rows.append(["", "TOTAL EXTRAORDINARIOS", "", "", "", "", "", "", "",
                 f"=SUM(J{extra_first}:J{extra_last})", "", ""])
    extra_total_row = len(rows)

    rows.append([""]*n_cols)
    rows.append(["", "TOTAL GENERAL (programado + extraordinario)", "", "", "", "", "", "", "",
                 f"=K{total_row}+J{extra_total_row}", "", ""])
    gran_total_row = len(rows)

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")

    i0 = lambda r: r - 1
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)
    reqs += fmt_section_label(sid, i0(4), n_cols)
    reqs += fmt_header_row(sid, i0(5), n_cols)

    # Inputs en filas equipos
    reqs += fmt_input(sid, i0(REC_FIRST), 0, REC_LAST, 1)                # A ID
    reqs += fmt_input(sid, i0(REC_FIRST), 1, REC_LAST, 2)                # B Equipo
    reqs += fmt_input(sid, i0(REC_FIRST), 2, REC_LAST, 3)                # C Frecuencia
    reqs += fmt_input(sid, i0(REC_FIRST), 3, REC_LAST, 4, FMT_INT)       # D Veces/año
    reqs += fmt_input(sid, i0(REC_FIRST), 4, REC_LAST, 5, FMT_DATE)      # E Último
    reqs += fmt_formula(sid, i0(REC_FIRST), 5, REC_LAST, 6, FMT_DATE)    # F Próx Sugerido
    reqs += fmt_input(sid, i0(REC_FIRST), 6, REC_LAST, 7, FMT_DATE)      # G Próx REAL (override)
    reqs += fmt_input(sid, i0(REC_FIRST), 7, REC_LAST, 8)                # H Estado
    reqs += fmt_input(sid, i0(REC_FIRST), 8, REC_LAST, 9)                # I Proveedor
    reqs += fmt_input(sid, i0(REC_FIRST), 9, REC_LAST, 10, FMT_MONEY)    # J $/servicio
    reqs += fmt_formula(sid, i0(REC_FIRST), 10, REC_LAST, 11, FMT_MONEY_F) # K $ Anual
    reqs += fmt_input(sid, i0(REC_FIRST), 11, REC_LAST, 12)              # L Notas

    # Data validation para Estado (dropdown)
    reqs += [{"setDataValidation": {
        "range": _rng(sid, i0(REC_FIRST), 7, REC_LAST, 8),
        "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [
                {"userEnteredValue": "Pendiente"},
                {"userEnteredValue": "Hecho"},
                {"userEnteredValue": "Aplazado"},
                {"userEnteredValue": "N/A"},
            ]},
            "strict": False, "showCustomUi": True,
        }}}]

    # Total anual
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(total_row), 0, total_row, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_FUE,
            "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(total_row), 10, total_row, 11),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]

    # Section Extraordinarios
    reqs += fmt_section_label(sid, i0(extra_header_row), n_cols)
    reqs += fmt_header_row(sid, i0(extra_header_row+1), n_cols)
    reqs += fmt_input(sid, i0(extra_first), 0, extra_last, 9, FMT_DATE)
    reqs += fmt_input(sid, i0(extra_first), 9, extra_last, 10, FMT_MONEY)
    reqs += fmt_input(sid, i0(extra_first), 10, extra_last, 12)

    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(extra_total_row), 0, extra_total_row, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_MED,
            "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(extra_total_row), 9, extra_total_row, 10),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]

    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(gran_total_row), 0, gran_total_row, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_FUE,
            "textFormat": {"bold": True, "fontSize": 13, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(gran_total_row), 9, gran_total_row, 10),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]

    widths = [110, 220, 100, 65, 100, 110, 110, 95, 130, 105, 105, 180]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))

    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 5}},
        "fields": "gridProperties.frozenRowCount"}})

    ss.batch_update({"requests": reqs})


def build_hoja_mixtos(ws, ss):
    """Hoja Mixtos — equipos compartidos con prorrateo % entre sucursales."""
    sid = ws.id
    ws.clear()

    sucursales_labels = [s[2] for s in SUCURSALES]
    n_sucs = len(SUCURSALES)  # 7

    headers = ["ID", "Equipo / Servicio", "Frecuencia", "Veces/año",
               "Proveedor", "$ por servicio", "$ Anual\n(= F × D)"] + \
              [f"% {l}" for l in sucursales_labels] + \
              ["Validación %", "Notas"]
    n_cols = len(headers)  # 7 + 7 + 2 = 16

    rows = [
        ["🔄 MIXTOS / COMPARTIDOS — Mantenimiento que se reparte entre sucursales"] + [""]*(n_cols-1),
        ["Asigne % de cada equipo a cada sucursal. Validación = 100% (suma de los %)."] + [""]*(n_cols-1),
        [""] * n_cols,
        ["EQUIPOS COMPARTIDOS"] + [""]*(n_cols-1),
        headers,
    ]

    REC_FIRST = 6
    # Por default todo va prorrateado parejo (1/n)
    default_pct = round(1/n_sucs, 4)
    for i, (equipo, freq, veces, notas) in enumerate(EQUIPOS_MIXTOS):
        r = REC_FIRST + i
        # Cols A-G como en sucursal
        row = [
            f"MIX-{i+1:03d}",
            equipo,
            freq,
            veces if veces > 0 else "",
            "",  # proveedor
            "",  # $ servicio
            f'=IF(OR(F{r}="",D{r}=""),0,F{r}*D{r})',  # $ anual
        ]
        # 7 cols de % (default = 1/7 cada una)
        for _ in range(n_sucs):
            row.append(default_pct)
        # Validación = suma de los 7 %s
        sum_range = f"H{r}:N{r}"  # cols 8-14 (H..N) son las 7 sucursales
        row.append(f"=SUM({sum_range})")
        row.append(notas)
        rows.append(row)
    REC_LAST = REC_FIRST + len(EQUIPOS_MIXTOS) - 1

    # Total general anual de mixtos
    rows.append([""] * n_cols)
    total_row = len(rows) + 1
    total_row_data = ["", "TOTAL MIXTOS / AÑO", "", "", "", "",
                      f"=SUM(G{REC_FIRST}:G{REC_LAST})"]
    # Total $ asignado a cada sucursal: G * % de esa col
    for col_idx in range(n_sucs):
        col_letter = chr(ord("H") + col_idx)  # H, I, J, K, L, M, N
        total_row_data.append(
            f"=SUMPRODUCT(G{REC_FIRST}:G{REC_LAST},{col_letter}{REC_FIRST}:{col_letter}{REC_LAST})"
        )
    total_row_data.append("")  # validación
    total_row_data.append("")  # notas
    rows.append(total_row_data)

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")

    i0 = lambda r: r - 1
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)
    reqs += fmt_section_label(sid, i0(4), n_cols)
    reqs += fmt_header_row(sid, i0(5), n_cols)

    # Inputs A-F
    reqs += fmt_input(sid, i0(REC_FIRST), 0, REC_LAST, 1)            # ID
    reqs += fmt_input(sid, i0(REC_FIRST), 1, REC_LAST, 2)            # Equipo
    reqs += fmt_input(sid, i0(REC_FIRST), 2, REC_LAST, 3)            # Frecuencia
    reqs += fmt_input(sid, i0(REC_FIRST), 3, REC_LAST, 4, FMT_INT)   # Veces/año
    reqs += fmt_input(sid, i0(REC_FIRST), 4, REC_LAST, 5)            # Proveedor
    reqs += fmt_input(sid, i0(REC_FIRST), 5, REC_LAST, 6, FMT_MONEY) # $ servicio
    reqs += fmt_formula(sid, i0(REC_FIRST), 6, REC_LAST, 7, FMT_MONEY_F) # $ Anual
    # % por sucursal (7 cols)
    reqs += fmt_input(sid, i0(REC_FIRST), 7, REC_LAST, 7+n_sucs, FMT_PCT)
    # Validación
    reqs += fmt_formula(sid, i0(REC_FIRST), 7+n_sucs, REC_LAST, 8+n_sucs, FMT_PCT)
    # Notas
    reqs += fmt_input(sid, i0(REC_FIRST), 8+n_sucs, REC_LAST, 9+n_sucs)

    # Total
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(total_row), 0, total_row, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_FUE,
            "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(total_row), 6, total_row, 7+n_sucs),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]

    # Anchos
    widths = [85, 240, 100, 70, 130, 110, 110] + [110]*n_sucs + [100, 180]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))

    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 5}},
        "fields": "gridProperties.frozenRowCount"}})

    ss.batch_update({"requests": reqs})


def build_resumen(ws, ss):
    """Resumen — $ anual por sucursal (programado + extraordinario + prorrateo mixtos)."""
    sid = ws.id
    ws.clear()

    rows = [
        ["📋 RESUMEN MANTENIMIENTO — Gasto Anual por Sucursal"] + [""]*5,
        ["Cada fila jala $ anual de la hoja de la sucursal + su parte de mixtos."] + [""]*5,
        [""] * 6,
        ["Sucursal", "$ Programado / año", "$ Extraordinarios", "$ Mixtos asignados",
         "$ TOTAL / año", "Notas"],
    ]

    REC_FIRST = 5
    for i, (slug, sheet_name, label) in enumerate(SUCURSALES):
        r = REC_FIRST + i
        col_mix = chr(ord("H") + i)  # H..N en hoja Mixtos
        rows.append([
            label,
            # $ programado: del total anual de la hoja (depende del layout — usamos suma de col I)
            f'=IFERROR(SUMIF(\'{sheet_name}\'!B:B,"TOTAL ANUAL PROGRAMADO",\'{sheet_name}\'!I:I),0)',
            # $ extraordinarios
            f'=IFERROR(SUMIF(\'{sheet_name}\'!B:B,"TOTAL EXTRAORDINARIOS",\'{sheet_name}\'!H:H),0)',
            # $ mixtos: total row de Mixtos col correspondiente
            f'=IFERROR(SUMIF(\'🔄 Mixtos\'!B:B,"TOTAL MIXTOS / AÑO",\'🔄 Mixtos\'!{col_mix}:{col_mix}),0)',
            f"=B{r}+C{r}+D{r}",
            "",
        ])
    REC_LAST = REC_FIRST + len(SUCURSALES) - 1

    rows.append([""] * 6)
    total_row = len(rows) + 1
    rows.append([
        "TOTAL GENERAL",
        f"=SUM(B{REC_FIRST}:B{REC_LAST})",
        f"=SUM(C{REC_FIRST}:C{REC_LAST})",
        f"=SUM(D{REC_FIRST}:D{REC_LAST})",
        f"=SUM(E{REC_FIRST}:E{REC_LAST})",
        "",
    ])

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")

    n_cols = 6
    i0 = lambda r: r - 1
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)
    reqs += fmt_header_row(sid, i0(4), n_cols)

    # Filas datos
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(REC_FIRST), 0, REC_LAST, 1),
        "cell": {"userEnteredFormat": {
            "backgroundColor": GRIS_CLARO,
            "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": VERDE_OSC},
            "horizontalAlignment": "LEFT"}},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}}]
    reqs += fmt_formula(sid, i0(REC_FIRST), 1, REC_LAST, 4, FMT_MONEY_F)
    reqs += fmt_formula(sid, i0(REC_FIRST), 4, REC_LAST, 5, FMT_MONEY_F, highlight=True)
    reqs += fmt_input(sid, i0(REC_FIRST), 5, REC_LAST, 6)

    # Total
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(total_row), 0, total_row, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_FUE,
            "textFormat": {"bold": True, "fontSize": 13, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(total_row), 1, total_row, 5),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]

    widths = [200, 160, 160, 160, 170, 200]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))

    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 4}},
        "fields": "gridProperties.frozenRowCount"}})

    ss.batch_update({"requests": reqs})


def build_esta_semana(ws, ss):
    """Hoja Esta Semana — una mini-tabla por sucursal usando FILTER local.

    Por sucursal: muestra equipos cuyo Próximo efectivo (REAL si tiene, sino SUGERIDO)
    cae entre HOY y HOY+7, y Estado != "Hecho".
    """
    sid = ws.id
    ws.clear()

    rows = [
        ["📋 ESTA SEMANA — Hoja del Técnico"] + [""]*6,
        ["Equipos cuyo Próximo (real o sugerido) cae en los próximos 7 días. Excluye 'Hecho'. Se actualiza solo al abrir el Sheet."] + [""]*6,
        [""] * 7,
    ]

    # Por cada sucursal, una sección con FILTER local
    for slug, sheet_name, label in SUCURSALES:
        ref = f"'{sheet_name}'"
        rows.append([f"━━ {label} ━━"] + [""]*6)
        rows.append(["ID", "Equipo", "Próximo", "Frecuencia", "Estado", "Proveedor", "Notas"])
        # Fórmula FILTER: muestra A,B, [F/G], C, H, I, L cuando los criterios se cumplen
        filtro = (
            f"=IFERROR("
                f"FILTER("
                    f'{{{ref}!A6:A30,'                                          # ID
                    f"{ref}!B6:B30,"                                            # Equipo
                    f"IF({ref}!G6:G30=\"\",{ref}!F6:F30,{ref}!G6:G30),"        # Próximo
                    f"{ref}!C6:C30,"                                            # Frecuencia
                    f"{ref}!H6:H30,"                                            # Estado
                    f"{ref}!I6:I30,"                                            # Proveedor
                    f"{ref}!L6:L30}},"                                          # Notas
                    f"{ref}!A6:A30<>\"\","                                      # tiene ID
                    f"IF({ref}!G6:G30=\"\",{ref}!F6:F30,{ref}!G6:G30)>=TODAY(),"
                    f"IF({ref}!G6:G30=\"\",{ref}!F6:F30,{ref}!G6:G30)<=TODAY()+7,"
                    f"{ref}!H6:H30<>\"Hecho\""
                f"),"
                f'"— sin pendientes esta semana —"'
            f")"
        )
        rows.append([filtro] + [""]*6)
        # 5 filas vacías de buffer (por si FILTER devuelve varias filas)
        for _ in range(5):
            rows.append([""] * 7)

    # Espacio para firmas al final
    rows.append([""] * 7)
    rows.append([""] * 7)
    rows.append(["Firma del técnico:", "______________________________", "",
                 "Firma del encargado:", "______________________________", "", ""])

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")

    n_cols = 7
    i0 = lambda r: r - 1
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)

    # Aplicar formato a cada sección (header + datos)
    SECTION_HEIGHT = 7  # 1 separador + 1 header + 5 filas data
    for i in range(len(SUCURSALES)):
        sec_start = 4 + i * SECTION_HEIGHT  # 1-idx fila del separador
        # Separador (label sucursal)
        reqs += [{"mergeCells": {"range": _rng(sid, i0(sec_start), 0, sec_start, n_cols), "mergeType": "MERGE_ALL"}}]
        reqs += [{"repeatCell": {
            "range": _rng(sid, i0(sec_start), 0, sec_start, n_cols),
            "cell": {"userEnteredFormat": {
                "backgroundColor": VERDE_CLARO,
                "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": VERDE_OSC},
                "horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}}]
        # Header de tabla (fila +1)
        reqs += fmt_header_row(sid, i0(sec_start + 1), n_cols)
        # Filas de datos: la fila del FILTER + 5 buffer (índices sec_start+2 a sec_start+6)
        data_start_0idx = i0(sec_start + 2)
        data_end_0idx = sec_start + 6  # exclusive
        reqs += [{"repeatCell": {
            "range": _rng(sid, data_start_0idx, 0, data_end_0idx, n_cols),
            "cell": {"userEnteredFormat": {
                "backgroundColor": BLANCO,
                "textFormat": {"fontSize": 10},
                "horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}}]
        # Col C (Próximo) formato fecha
        reqs += [{"repeatCell": {
            "range": _rng(sid, data_start_0idx, 2, data_end_0idx, 3),
            "cell": {"userEnteredFormat": {"numberFormat": FMT_DATE, "horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]

    widths = [110, 240, 110, 110, 110, 130, 200]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))

    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 3}},
        "fields": "gridProperties.frozenRowCount"}})

    ss.batch_update({"requests": reqs})


def build_calendario(ws, ss):
    """Calendario — qué toca cada mes (informativo, Staff lo arma según fechas reales)."""
    sid = ws.id
    ws.clear()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    rows = [
        ["📅 CALENDARIO ANUAL DE MANTENIMIENTO"] + [""]*3,
        ["Lista mensual. Llene a mano lo que toca o jale automáticamente con fechas de cada hoja."] + [""]*3,
        [""] * 4,
        ["Mes", "Equipos / Servicios programados", "$ Estimado del mes", "Notas"],
    ]
    for mes in meses:
        rows.append([mes, "", "", ""])

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")
    n_cols = 4
    i0 = lambda r: r - 1
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)
    reqs += fmt_header_row(sid, i0(4), n_cols)
    reqs += fmt_input(sid, 4, 1, 16, 4)
    reqs += fmt_input(sid, 4, 2, 16, 3, FMT_MONEY)
    reqs += [{"repeatCell": {
        "range": _rng(sid, 4, 0, 16, 1),
        "cell": {"userEnteredFormat": {
            "backgroundColor": GRIS_CLARO,
            "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    for i, w in enumerate([130, 500, 160, 250]):
        reqs.append(col_width(sid, i, w))
    ss.batch_update({"requests": reqs})


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    creds = service_account.Credentials.from_service_account_file(SA, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SHEET_ID)
    print(f"Conectado: {ss.title}")

    # Locale en_US (memoria sheets-locale-es-mx-formulas)
    ss.batch_update({"requests": [{
        "updateSpreadsheetProperties": {
            "properties": {"locale": "en_US"},
            "fields": "locale"}}]})

    target = ["📋 Esta Semana", "📋 Resumen", "📅 Calendario", "🔄 Mixtos"] + [s[1] for s in SUCURSALES]

    existing = {w.title: w for w in ss.worksheets()}
    for name in target:
        if name not in existing:
            ss.add_worksheet(title=name, rows=60, cols=20)
            print(f"  + creada: {name}")
    existing = {w.title: w for w in ss.worksheets()}
    for w in ss.worksheets():
        if w.title not in target:
            ss.del_worksheet(w)
            print(f"  - borrada: {w.title}")
    existing = {w.title: w for w in ss.worksheets()}

    # Construir cada sucursal (con sleep para no toparse rate limit)
    for slug, sheet_name, label in SUCURSALES:
        equipos = EQUIPOS_COCINA_CENTRAL if slug == "cocina_central" else EQUIPOS_CARRETA
        print(f"  → {sheet_name}")
        build_hoja_sucursal(existing[sheet_name], ss, slug, sheet_name, label, equipos)
        sleep(2)

    sleep(10)
    print(f"  → Mixtos")
    build_hoja_mixtos(existing["🔄 Mixtos"], ss)

    sleep(10)
    print(f"  → Calendario")
    build_calendario(existing["📅 Calendario"], ss)

    sleep(10)
    print(f"  → Resumen")
    build_resumen(existing["📋 Resumen"], ss)

    sleep(10)
    print(f"  → Esta Semana")
    build_esta_semana(existing["📋 Esta Semana"], ss)

    print(f"\n✓ Listo")
    print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
