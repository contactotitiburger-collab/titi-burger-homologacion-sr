#!/usr/bin/env python3
"""TITI_BURGER_COCINA — versión 2, estilo Maestro.

Estructura:
  📋 Resumen Cocina       → vista global, % final que va al Maestro
  📦 Costos y Tarifas     → variables + fijos + tarifa MO + servicios prorrateados
  🍗 Boneless             → ficha técnica del proceso
  🧀 Dedos de Queso       → idem
  🍗 Tiras Pollo          → idem
  🥓 Tocino               → idem
  🥩 Patty                → idem
  🍗 Pollo                → idem

Estilo replica el Maestro:
  Header  fondo #375623 / texto blanco bold size 10
  Subtítulo gris #595959 size 10
  ID col F2F2F2 gris claro bold
  Inputs  fondo #E2EFDA verde claro / texto #375623
  Resultado final fondo #A9D08E verde fuerte / negro bold
  Formatos: $#,##0.00 inputs · $#,##0.00;;- fórmulas · 0.0%
"""
import gspread
from google.oauth2 import service_account

SA       = "/home/tito/.openclaw/credentials/google/service-account.json"
SHEET_ID = "1HDZLecg11015vt5bBkhpRtn09Z7I9y2SKksi5v7pPM8"

# Paleta exacta del Maestro
VERDE_OSC   = {"red": 0x37/255, "green": 0x56/255, "blue": 0x23/255}  # #375623
VERDE_CLARO = {"red": 0xE2/255, "green": 0xEF/255, "blue": 0xDA/255}  # #E2EFDA
VERDE_MED   = {"red": 0xC6/255, "green": 0xEF/255, "blue": 0xCE/255}  # #C6EFCE
VERDE_FUE   = {"red": 0xA9/255, "green": 0xD0/255, "blue": 0x8E/255}  # #A9D08E
GRIS_CLARO  = {"red": 0xF2/255, "green": 0xF2/255, "blue": 0xF2/255}  # #F2F2F2
GRIS_OSC    = {"red": 0x59/255, "green": 0x59/255, "blue": 0x59/255}  # #595959
BLANCO      = {"red": 1.0, "green": 1.0, "blue": 1.0}
NEGRO       = {"red": 0.0, "green": 0.0, "blue": 0.0}

FMT_MONEY   = {"type": "CURRENCY", "pattern": "\"$\"#,##0.00"}
FMT_MONEY_F = {"type": "CURRENCY", "pattern": "\"$\"#,##0.00;;\"-\""}
FMT_PCT     = {"type": "PERCENT",  "pattern": "0.0%"}
FMT_INT     = {"type": "NUMBER",   "pattern": "#,##0"}
FMT_DECIMAL = {"type": "NUMBER",   "pattern": "#,##0.000"}  # cantidades de receta

# Procesos (slug, nombre hoja, label, ID-Maestro mapping, unidad)
PROCESOS = [
    # Originales (Staff los quiere mantener todos)
    ("boneless",  "🍗 Boneless",        "Boneless",                     "INS-029", "kg"),
    ("dedos",     "🧀 Dedos de Queso",  "Dedos de queso",               "—",       "pza"),
    ("tiras",     "🍗 Tiras Pollo",     "Tiras de pollo empanizado",    "—",       "kg"),
    ("tocino",    "🥓 Tocino",          "Tocino",                       "INS-037", "kg"),
    ("patty",     "🥩 Patty",           "Patty (carne molida en casa)", "INS-031", "pza"),
    ("pollo",     "🍗 Pollo",           "Pollo (filete)",               "INS-035", "kg"),
    # Nuevos sub-procesos y procesos (de datos reales de Staff)
    ("mezcla_b",  "🌾 Mezcla Harina Boneless", "Mezcla harina (boneless)", "—",      "kg"),
    ("mezcla_t",  "🌾 Mezcla Harina Tiras",    "Mezcla harina (tiras)",    "—",      "kg"),
    ("aderezo",   "🥫 Aderezo Casa",    "Aderezo de la casa",           "INS-001", "gal"),
    ("salsa_soya","🍶 Salsa Soya Prep", "Salsa de soya preparada",      "—",       "lt"),
    ("relleno_c", "🌶️ Relleno Chiles",  "Relleno chiles güeritos",      "—",       "orden"),
    ("chiles_g",  "🌶️ Chiles Güeritos", "Chiles güeritos",              "—",       "orden"),
]

# Filas reservadas para la receta en cada ficha (Staff pidió más espacio 2026-06-02)
RECETA_ROWS = 12

# Recetas semilla — formato con ID-Insumo al inicio (catálogo futuro)
# Cada tupla: (id_insumo, insumo, $presentación, contenido_num, unidad, cantidad_usada, nota)
# IDs: "INS-XXX" para los que ya están en el Maestro; "—" para los que faltan agregar al catálogo.
RECETAS_SEMILLA = {
    # ───── ORIGINALES (1 orden de salida) ─────
    "boneless": [
        ("INS-035", "Pollo",                       59.90,   1,    "kg",     0.366, "$21.94 por orden"),
        ("—",       "Mezcla harina boneless",      2087.66, 471,  "orden",  1,     "ver hoja Mezcla Harina Boneless"),
        ("INS-023", "Manteca (freidora compartida)", 649,   229,  "orden",  1,     "$38.18/lt prorrateado"),
        ("—",       "BBQ (bote 4.7 kg)",           350,    80,   "porción",1,     "rinde 80 por bote — falta en Maestro"),
        ("—",       "Búfalo (bote 4.2 kg)",        219,    70,   "porción",1,     "falta en Maestro"),
        ("INS-048", "Papeleta (paq 500)",          370,    500,  "pza",    1,     ""),
    ],
    "dedos": [
        ("INS-036", "Queso amarillo (paq 72 pza = $169)", 169, 72, "pza",  3,     "~3 dedos por orden"),
        ("—",       "Pan rallado/empanizado",      440,    5,    "kg",     0.05,  "50 gr — falta en Maestro"),
        ("INS-023", "Manteca (freidora compartida)", 649,  229,  "orden",  1,     "prorrateo"),
        ("INS-048", "Papeleta (paq 500)",          370,    500,  "pza",    1,     ""),
    ],
    "tiras": [
        ("INS-035", "Pollo filete",                59.90,  1,    "kg",     0.055, "~18 tiras por kg"),
        ("—",       "Mezcla harina tiras",         1051.91,300,  "orden",  1,     "ver hoja Mezcla Harina Tiras"),
        ("INS-023", "Manteca (freidora compartida)", 649,  229,  "orden",  1,     "prorrateo"),
        ("INS-048", "Papeleta (paq 500)",          370,    500,  "pza",    1,     ""),
    ],
    "tocino": [
        ("INS-037", "Tocino x burger",             186,    23,   "porción",1,     "2 tiras X hamburguesa = ~23/kg"),
        ("INS-039", "Cebolla caramelizada",        260,    160,  "porción",1,     "1/2 cebolla, opcional western"),
    ],
    "patty": [
        ("INS-031", "Carne (paq 20 pza = $120)",   120,    20,   "pza",    1,     "1 patty = 1 pieza"),
        ("—",       "Sazonadores (sal, pimienta)", 240,    1000, "porción",1,     "muy poco por patty"),
    ],
    "pollo": [
        ("INS-035", "Pollo entero crudo",          59.90,  1,    "kg",     1.5,   "1.5 kg crudo por kg filete"),
        ("—",       "Sazonadores",                 240,    1000, "porción",1,     ""),
    ],
    # ───── NUEVOS (sub-procesos y procesos completos) ─────
    "mezcla_b": [
        ("—",       "Leche (caja 10 lt = $235)",   235, 10, "lt",   2,    "2 lt"),
        ("—",       "Harina (saco 44 kg = $500)",  500, 44, "kg",   22,   "22 kg"),
        ("—",       "Huevo (caja 180 pzas = $236)",236, 180,"pza",  15,   "15 huevos"),
        ("—",       "Galleta molida (5 kg = $440)",440, 5,  "kg",   1.5,  "1.5 kg"),
        ("—",       "Sal (20 kg = $271)",          271, 20, "kg",   0.5,  "0.5 kg"),
        ("—",       "Ajo en polvo",                240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Pimienta",                    240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Cayena",                      240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Paprika",                     240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Consomé",                     43,  1,  "kg",   0.2,  "200 gr"),
        ("INS-023", "Manteca (freidora compartida)", 649, 17, "lt", 37.5, "ajustar prorrateo"),
        ("—",       "MO producción (2 días, 2 emp)", 1715, 1, "lote", 1,  "rinde 471 órdenes"),
    ],
    "mezcla_t": [
        ("—",       "Leche (caja 10 lt = $235)",   235, 10, "lt",   2,    "2 lt"),
        ("—",       "Huevo (caja 180 pzas = $236)",236, 180,"pza",  15,   "15 huevos"),
        ("—",       "Galleta molida (5 kg = $440)",440, 5,  "kg",   1.5,  "1.5 kg"),
        ("—",       "Panko (5 kg = $440)",         440, 5,  "kg",   3,    "3 kg"),
        ("—",       "Sal (20 kg = $271)",          271, 20, "kg",   0.5,  "0.5 kg"),
        ("—",       "Ajo en polvo",                240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Pimienta",                    240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Cayena",                      240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Paprika",                     240, 1,  "kg",   0.2,  "200 gr"),
        ("—",       "Consomé",                     43,  1,  "kg",   0.2,  "200 gr"),
        ("INS-023", "Manteca (freidora compartida)", 649, 17, "lt", 37.5, "ajustar prorrateo"),
        ("—",       "MO producción (2 días, 2 emp)", 2000, 1, "lote", 1,  "rinde 300 órdenes"),
    ],
    "aderezo": [
        ("—",       "Mayonesa",                    219, 1,  "gal",  4,    "4 galones"),
        ("—",       "Catsup",                      180, 1,  "kg",   0.5,  "0.5 kg"),
        ("INS-007", "Mostaza",                     129, 1,  "kg",   0.33, "0.33 kg"),
        ("—",       "Sal",                         14.8,1,  "kg",   0.02, "20 gr"),
        ("—",       "Pimienta",                    320, 1,  "kg",   0.1,  "100 gr"),
        ("—",       "Polvo de ajo",                130, 1,  "kg",   0.08, "80 gr"),
    ],
    "salsa_soya": [
        ("—",       "Salsa soya",                  250, 3.78,"lt",  3.78, "$250 / 3.78 lt"),
        ("—",       "Salsa Valentina",             40,  1,  "lt",   0.2,  "200 ml"),
        ("—",       "Limón",                       22,  1,  "kg",   0.3,  "300 gr"),
        ("—",       "Aceite de oliva",             224, 1,  "lt",   0.2,  "200 ml"),
    ],
    "relleno_c": [
        ("—",       "Queso crema (barra 1.9 kg)",  352, 1,  "barra",1,    "1 barra"),
        ("—",       "Cebollín (mazo)",             10,  1,  "mazo", 1,    "1 mazo"),
        ("INS-037", "Tocino",                      186, 1,  "kg",   0.5,  "0.5 kg"),
        ("INS-036", "Queso amarillo (paq 72 pza)", 169, 72, "pza",  36,   "36 rebanadas"),
        ("—",       "Consomé",                     43,  1,  "kg",   0.05, "50 gr"),
        ("—",       "Pimienta",                    240, 1,  "kg",   0.05, "50 gr"),
        ("—",       "MO preparación",              329, 1,  "lote", 1,    "6h 1 persona, rinde 60 órdenes"),
    ],
    "chiles_g": [
        ("—",       "Chiles güeros",               48,  16, "pza",  1,    "rinde 16 por kg"),
        ("—",       "Tocino Nayar",                80,  21, "pza",  1,    "rinde 21 por kg"),
        ("—",       "Salsa soya preparada (botella 500ml)", 38.68, 1, "botella", 1, "ver hoja Salsa Soya"),
        ("—",       "Relleno (de hoja Relleno)",   516.50, 60, "orden", 1, "rinde 60 órdenes"),
        ("INS-023", "Manteca (freidora compartida)", 649, 229, "orden", 1, "prorrateo"),
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de formato (genera batch_update requests al estilo Maestro)
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
                "textFormat": {"foregroundColor": GRIS_OSC, "fontSize": 10, "italic": False},
                "horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}},
    ]

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

def fmt_section_label(sid, row, n_cols, text=None):
    return [
        {"mergeCells": {"range": _rng(sid, row, 0, row+1, n_cols), "mergeType": "MERGE_ALL"}},
        {"repeatCell": {
            "range": _rng(sid, row, 0, row+1, n_cols),
            "cell": {"userEnteredFormat": {
                "backgroundColor": VERDE_CLARO,
                "textFormat": {"foregroundColor": VERDE_OSC, "bold": True, "fontSize": 11},
                "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS", "startIndex": row, "endIndex": row+1},
            "properties": {"pixelSize": 26}, "fields": "pixelSize"}},
    ]

def fmt_input(sid, r1, c1, r2, c2, number_fmt=None):
    cell = {"backgroundColor": VERDE_CLARO,
            "textFormat": {"foregroundColor": VERDE_OSC, "bold": False, "fontSize": 10},
            "horizontalAlignment": "CENTER",
            "borders": {"top": {"style": "SOLID", "color": GRIS_CLARO},
                        "bottom": {"style": "SOLID", "color": GRIS_CLARO},
                        "left": {"style": "SOLID", "color": GRIS_CLARO},
                        "right": {"style": "SOLID", "color": GRIS_CLARO}}}
    fields = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders"
    if number_fmt:
        cell["numberFormat"] = number_fmt
        fields += ",numberFormat"
    fields += ")"
    return [{"repeatCell": {"range": _rng(sid, r1, c1, r2, c2),
                            "cell": {"userEnteredFormat": cell}, "fields": fields}}]

def fmt_formula(sid, r1, c1, r2, c2, number_fmt=None, highlight=False):
    bg = VERDE_FUE if highlight else BLANCO
    fg = NEGRO
    cell = {"backgroundColor": bg,
            "textFormat": {"foregroundColor": fg, "bold": True, "fontSize": 10},
            "horizontalAlignment": "CENTER",
            "borders": {"top": {"style": "SOLID", "color": GRIS_CLARO},
                        "bottom": {"style": "SOLID", "color": GRIS_CLARO},
                        "left": {"style": "SOLID", "color": GRIS_CLARO},
                        "right": {"style": "SOLID", "color": GRIS_CLARO}}}
    fields = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders"
    if number_fmt:
        cell["numberFormat"] = number_fmt
        fields += ",numberFormat"
    fields += ")"
    return [{"repeatCell": {"range": _rng(sid, r1, c1, r2, c2),
                            "cell": {"userEnteredFormat": cell}, "fields": fields}}]

def fmt_label(sid, r1, c1, r2, c2):
    return [{"repeatCell": {
        "range": _rng(sid, r1, c1, r2, c2),
        "cell": {"userEnteredFormat": {
            "textFormat": {"foregroundColor": VERDE_OSC, "bold": True, "fontSize": 10},
            "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP"}},
        "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"}}]

def col_width(sid, idx, width):
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": idx, "endIndex": idx+1},
        "properties": {"pixelSize": width}, "fields": "pixelSize"}}


# ─────────────────────────────────────────────────────────────────────────────
# Builders por hoja
# ─────────────────────────────────────────────────────────────────────────────

def build_resumen(ws, ss):
    """Hoja 📋 Resumen Cocina — vista global con links a cada proceso."""
    sid = ws.id
    ws.clear()

    rows = [
        ["📋 RESUMEN COCINA — Punto de Equilibrio y % Final por Proceso", "", "", "", "", "", "", "", ""],
        ["Vista global. Cada fila jala de la ficha técnica del proceso. El % FINAL es el que va al Maestro col H.", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        ["ID-PROC", "Proceso", "Unidad", "Costo Crudo $/u", "Costo Total $/u\n(Punto Equilibrio)",
         "% Equilibrio\n(real, sin margen)", "Precio Venta Cocina $/u", "% FINAL\n(→ Maestro)", "ID-Maestro"],
    ]
    # Filas datos
    start = 5  # 1-indexed
    for i, (slug, sheet_name, label, ins, unit) in enumerate(PROCESOS):
        r = start + i
        # Posiciones (formato 8 cols en receta con ID):
        #   H[CRUDO] = costo crudo $/u  (col H, al final de los subtotales)
        #   B[TOTAL] = costo total (punto equilibrio)
        #   F[TOTAL] = % equilibrio
        #   B[VENTA] = precio venta cocina
        #   F[VENTA] = % final → Maestro
        CRUDO = 6 + RECETA_ROWS - 1 + 2   # 19
        TOTAL = CRUDO + 11                 # 30
        VENTA = TOTAL + 2                  # 32
        sheet_ref = f"'{sheet_name}'"
        rows.append([
            f"PROC-{i+1:03d}",
            label,
            unit,
            f'=IFERROR({sheet_ref}!H{CRUDO},"")',
            f'=IFERROR({sheet_ref}!B{TOTAL},"")',
            f'=IFERROR({sheet_ref}!F{TOTAL},"")',
            f'=IFERROR({sheet_ref}!B{VENTA},"")',
            f'=IFERROR({sheet_ref}!F{VENTA},"")',
            ins,
        ])

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")

    n_cols = 9
    n_data = len(PROCESOS)
    last = start + n_data - 1
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)
    reqs += fmt_header_row(sid, 3, n_cols)
    # ID col gris claro
    reqs += [{"repeatCell": {
        "range": _rng(sid, 4, 0, last, 1),
        "cell": {"userEnteredFormat": {
            "backgroundColor": GRIS_CLARO,
            "textFormat": {"bold": True, "fontSize": 10, "foregroundColor": GRIS_OSC},
            "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}}]
    # Label proceso (col B) en bold
    reqs += [{"repeatCell": {
        "range": _rng(sid, 4, 1, last, 2),
        "cell": {"userEnteredFormat": {
            "textFormat": {"bold": True, "fontSize": 10, "foregroundColor": VERDE_OSC},
            "horizontalAlignment": "LEFT"}},
        "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}}]
    # Unidad col C centrada
    reqs += [{"repeatCell": {
        "range": _rng(sid, 4, 2, last, 3),
        "cell": {"userEnteredFormat": {
            "textFormat": {"fontSize": 10}, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}}]
    # Cols D, E → fórmulas $ (crudo, costo total equilibrio)
    reqs += fmt_formula(sid, 4, 3, last, 4, FMT_MONEY_F)
    reqs += fmt_formula(sid, 4, 4, last, 5, FMT_MONEY_F)
    # Col F → % equilibrio (verde medio)
    reqs += [{"repeatCell": {
        "range": _rng(sid, 4, 5, last, 6),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_MED,
            "textFormat": {"bold": True, "fontSize": 10, "foregroundColor": VERDE_OSC},
            "horizontalAlignment": "CENTER",
            "numberFormat": FMT_PCT}},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,numberFormat)"}}]
    # Col G → precio venta $
    reqs += fmt_formula(sid, 4, 6, last, 7, FMT_MONEY_F)
    # Col H → % FINAL (verde fuerte, destacado)
    reqs += fmt_formula(sid, 4, 7, last, 8, FMT_PCT, highlight=True)
    # Col I → ID maestro centrada gris
    reqs += [{"repeatCell": {
        "range": _rng(sid, 4, 8, last, 9),
        "cell": {"userEnteredFormat": {
            "backgroundColor": GRIS_CLARO,
            "textFormat": {"fontSize": 10, "bold": False, "foregroundColor": GRIS_OSC},
            "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}}]

    # Anchos
    widths = [90, 220, 70, 120, 130, 110, 130, 110, 100]
    for i, w in enumerate(widths):
        reqs.append(col_width(sid, i, w))

    # Freeze
    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 4}},
        "fields": "gridProperties.frozenRowCount"}})

    ss.batch_update({"requests": reqs})


def build_costos(ws, ss):
    """Hoja 📦 Costos y Tarifas — fijos + variables + tarifa MO + servicios prorrateados."""
    sid = ws.id
    ws.clear()

    rows = []
    rows.append(["📦 COSTOS Y TARIFAS DE COCINA", "", "", ""])
    rows.append(["Costos fijos + variables del mes. De aquí salen $/min MO y servicios $/u que usan las fichas técnicas.", "", "", ""])
    rows.append(["", "", "", ""])

    # === BLOQUE 1: COSTOS FIJOS ===
    rows.append(["COSTOS FIJOS / MES", "", "", ""])
    rows.append(["Concepto", "$ / mes", "% asignado a cocina", "Notas"])
    fijos_start = len(rows) + 1  # primera fila de datos
    fijos = [
        ("Nómina cocineras",        "", 1.0,  "Sueldos brutos + prestaciones"),
        ("Renta — parte cocina",    "", "",   "% del espacio si es compartida"),
        ("Luz cocina (prorrateo)",  "", "",   "Estimado del recibo total"),
        ("Gas",                     "", 1.0,  "Recarga mensual"),
        ("Agua cocina (prorrateo)", "", "",   ""),
        ("Mantenimiento equipo",    "", 1.0,  "Promedio mensual"),
        ("Limpieza / químicos",     "", 1.0,  ""),
        ("Empaques cocina interna", "", 1.0,  ""),
        ("Otros",                   "", 1.0,  ""),
    ]
    for f in fijos:
        rows.append(list(f))
    fijos_last = len(rows)
    # Total
    rows.append(["TOTAL FIJOS / MES", f"=SUMPRODUCT(B{fijos_start}:B{fijos_last},C{fijos_start}:C{fijos_last})", "", ""])
    fijos_total_row = len(rows)

    rows.append(["", "", "", ""])
    rows.append(["", "", "", ""])

    # === BLOQUE 2: TARIFA MO ===
    rows.append(["TARIFA MANO DE OBRA", "", "", ""])
    rows.append(["Concepto", "Valor", "", "Notas"])
    rows.append(["Nómina cocineras / mes", f"=B{fijos_start}", "", "Jalado de fijos arriba"])
    nom_row = len(rows)
    rows.append(["Horas trabajadas / mes (todo el equipo)", "", "", "Ej: 3 × 8h × 26 días = 624"])
    hrs_row = len(rows)
    rows.append(["$/hora MO", f'=IF(OR(B{nom_row}="",B{hrs_row}="",B{hrs_row}=0),"",B{nom_row}/B{hrs_row})', "", "Calculado"])
    hr_row = len(rows)
    rows.append(["$/minuto MO", f'=IF(B{hr_row}="","",B{hr_row}/60)', "", "Para fichas técnicas (col MO)"])
    minuto_mo_row = len(rows)

    rows.append(["", "", "", ""])
    rows.append(["", "", "", ""])

    # === BLOQUE 3: SERVICIOS PRORRATEADOS ===
    rows.append(["SERVICIOS PRORRATEADOS (gas + luz)", "", "", ""])
    rows.append(["Concepto", "Valor", "", "Notas"])
    rows.append(["Gas + Luz cocina / mes",
                 f"=SUMIFS(B{fijos_start}:B{fijos_last},A{fijos_start}:A{fijos_last},\"Luz cocina (prorrateo)\")"
                 f"+SUMIFS(B{fijos_start}:B{fijos_last},A{fijos_start}:A{fijos_last},\"Gas\")",
                 "", "Suma de gas + luz arriba"])
    gas_luz_row = len(rows)
    rows.append(["Unidades totales procesadas / mes", "", "", "Suma de boneless+dedos+tiras+tocino+patty+pollo"])
    vol_row = len(rows)
    rows.append(["Servicios $/u",
                 f'=IF(OR(B{vol_row}="",B{vol_row}=0),"",B{gas_luz_row}/B{vol_row})',
                 "", "Para fichas técnicas (col Servicios)"])
    serv_u_row = len(rows)

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")

    n_cols = 4
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)
    # Headers de cada bloque (filas 4, 14, 21)
    # Bloque fijos header en fila 4 (0-idx=3)
    reqs += fmt_section_label(sid, 3, n_cols)
    reqs += fmt_header_row(sid, 4, n_cols)
    # Inputs fijos: B y C de filas fijos_start..fijos_last
    reqs += fmt_input(sid, fijos_start-1, 1, fijos_last, 2, FMT_MONEY)
    reqs += fmt_input(sid, fijos_start-1, 2, fijos_last, 3, FMT_PCT)
    # Total fila
    reqs += [{"repeatCell": {
        "range": _rng(sid, fijos_total_row-1, 0, fijos_total_row, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_FUE,
            "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, fijos_total_row-1, 1, fijos_total_row, 2),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F}},
        "fields": "userEnteredFormat.numberFormat"}}]

    # Bloque MO
    mo_title_row = fijos_total_row + 3
    reqs += fmt_section_label(sid, mo_title_row-1, n_cols)
    reqs += fmt_header_row(sid, mo_title_row, n_cols)
    reqs += fmt_input(sid, mo_title_row+1, 1, hrs_row, 2, FMT_MONEY)
    reqs += fmt_input(sid, hrs_row-1, 1, hrs_row, 2, FMT_INT)
    reqs += fmt_formula(sid, hr_row-1, 1, hr_row, 2, FMT_MONEY_F)
    reqs += fmt_formula(sid, minuto_mo_row-1, 1, minuto_mo_row, 2, FMT_MONEY_F, highlight=True)

    # Bloque servicios
    serv_title_row = minuto_mo_row + 3
    reqs += fmt_section_label(sid, serv_title_row-1, n_cols)
    reqs += fmt_header_row(sid, serv_title_row, n_cols)
    reqs += fmt_formula(sid, gas_luz_row-1, 1, gas_luz_row, 2, FMT_MONEY_F)
    reqs += fmt_input(sid, vol_row-1, 1, vol_row, 2, FMT_INT)
    reqs += fmt_formula(sid, serv_u_row-1, 1, serv_u_row, 2, FMT_MONEY_F, highlight=True)

    # Cols labels en col A: bold verde oscuro
    reqs += fmt_label(sid, 0, 0, len(rows), 1)

    # Anchos
    for i, w in enumerate([320, 160, 150, 360]):
        reqs.append(col_width(sid, i, w))

    ss.batch_update({"requests": reqs})


def build_ficha_proceso(ws, ss, slug, sheet_name, label, ins, unit):
    """Hoja por proceso — receta (RECETA_ROWS filas) + MO + servicios + mermas + resultado.

    Layout parametrizado con RECETA_ROWS. Las posiciones clave (que jala el Resumen y
    los IMPORTRANGE del Maestro) son:
      B[CRUDO]    Costo Crudo Total $/u
      B[TOTAL]    Costo Total $/u (Punto Equilibrio)
      D[TOTAL]    % Equilibrio vs Crudo
      B[VENTA]    Precio Venta Cocina $/u
      D[VENTA]    % FINAL vs Crudo (→ Maestro)
    """
    sid = ws.id
    ws.clear()

    # Posiciones de fila (1-indexed)
    REC_FIRST = 6
    REC_LAST  = REC_FIRST + RECETA_ROWS - 1            # ej 6 + 12 - 1 = 17
    CRUDO     = REC_LAST + 2                            # 19
    MO_SEC    = CRUDO + 2                               # 21
    MO_HDR    = MO_SEC + 1                              # 22
    MO_MIN    = MO_HDR + 1                              # 23
    MO_PER    = MO_HDR + 2                              # 24
    MO_PERU   = MO_HDR + 3                              # 25
    SERV_PERU = MO_HDR + 4                              # 26
    MERMAS    = MO_HDR + 5                              # 27
    RES_SEC   = MERMAS + 2                              # 29
    TOTAL     = RES_SEC + 1                             # 30
    MARGEN    = RES_SEC + 2                             # 31
    VENTA     = RES_SEC + 3                             # 32

    # Receta semilla — formato (id, insumo, $pres, cont, unidad, cant, nota) → 7 campos
    receta = RECETAS_SEMILLA.get(slug, [])
    receta_padded = list(receta)[:RECETA_ROWS] + [("", "", "", "", "", "", "")] * max(0, RECETA_ROWS - len(receta))

    EMPTY8 = ["", "", "", "", "", "", "", ""]
    rows = [
        [f"🍳 {label.upper()} — Ficha Técnica"] + [""]*7,                                                 # 1
        [f"Receta + costos + margen. ID-Maestro del proceso: {ins}. Los IDs en col A son del catálogo de insumos."] + [""]*7,  # 2
        EMPTY8,                                                                                            # 3
        ["RECETA — Insumos Crudos por unidad de salida"] + [""]*7,                                       # 4
        ["ID-Insumo", "Insumo", "$ Presentación", "Contenido", "Unidad", "$ Unitario\n(= C/D)", "Cantidad usada", "Subtotal $\n(= F×G)"],  # 5
    ]
    # Filas receta: A=ID, B=insumo, C=$presentación, D=contenido, E=unidad, F=$unitario, G=cantidad, H=subtotal
    for i, (id_ins, insumo, pres, cont, unidad_ins, cant, _nota) in enumerate(receta_padded):
        r = REC_FIRST + i
        rows.append([
            id_ins, insumo, pres, cont, unidad_ins,
            f'=IFERROR(C{r}/D{r},0)',
            cant,
            f'=IFERROR(F{r}*G{r},0)',
        ])
    rows.append(EMPTY8)                                                                                    # gap
    # COSTO CRUDO TOTAL: suma col H (subtotales). Valor en col H (al final de subtotales).
    rows.append([f"COSTO CRUDO TOTAL $/{unit}", "", "", "", "", "", "",
                 f"=IFERROR(SUM(H{REC_FIRST}:H{REC_LAST}),0)"])                                           # CRUDO (valor en col H)
    rows.append(EMPTY8)                                                                                    # gap
    rows.append(["MANO DE OBRA · SERVICIOS · MERMAS"] + [""]*7)                                           # MO_SEC
    rows.append(["Concepto", "Valor", "Detalle", "Notas", "", "", "", ""])                                # MO_HDR
    rows.append(["Minutos por unidad",  "",  "",                                  "Tiempo promedio cocineras", "", "", "", ""])  # MO_MIN
    rows.append(["$/min MO",            "='📦 Costos y Tarifas'!$B$23", "",       "Jalado de Costos", "", "", "", ""])           # MO_PER
    rows.append(["Mano de obra $/u",    f"=IFERROR(B{MO_MIN}*B{MO_PER},0)", "min × $/min", "", "", "", "", ""])                  # MO_PERU
    rows.append(["Servicios $/u",       "='📦 Costos y Tarifas'!$B$30", "",       "Jalado de Costos", "", "", "", ""])           # SERV_PERU
    rows.append(["Mermas %",            "",  "",                                  "10% típico", "", "", "", ""])                  # MERMAS
    rows.append(EMPTY8)                                                                                    # gap
    rows.append(["RESULTADO"] + [""]*7)                                                                    # RES_SEC
    # Crudo ahora está en H{CRUDO}. Total y Venta siguen en col B (valor $). % equilibrio/final en col F.
    rows.append([
        "Costo Total $/u (PUNTO EQUILIBRIO)",
        f'=IF(OR(H{CRUDO}="",H{CRUDO}=0),"",(H{CRUDO}+B{MO_PERU}+B{SERV_PERU})/(1-IF(B{MERMAS}="",0,B{MERMAS})))',
        "% Equilibrio vs Crudo →", "", "",
        f'=IF(OR(B{TOTAL}="",H{CRUDO}="",H{CRUDO}=0),"",B{TOTAL}/H{CRUDO}-1)', "", ""
    ])                                                                                                     # TOTAL
    rows.append(["Margen Cocina %",     "",  "Ej: 20%",                           "Ganancia que quiere cocina", "", "", "", ""])  # MARGEN
    rows.append([
        f"Precio Venta Cocina $/{unit}",
        f'=IF(B{TOTAL}="","",B{TOTAL}*(1+IF(B{MARGEN}="",0,B{MARGEN})))',
        "% FINAL vs Crudo (→ Maestro) →", "", "",
        f'=IF(OR(B{VENTA}="",H{CRUDO}="",H{CRUDO}=0),"",B{VENTA}/H{CRUDO}-1)', "", ""
    ])                                                                                                     # VENTA

    ws.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")

    n_cols = 8
    reqs = []
    reqs += fmt_title(sid, 0, n_cols)
    reqs += fmt_subtitle(sid, 1, n_cols)

    # 0-idx helpers (convert 1-idx → 0-idx)
    i0 = lambda r: r - 1

    # Sección RECETA (fila 4) + headers (fila 5)
    reqs += fmt_section_label(sid, i0(4), n_cols)
    reqs += fmt_header_row(sid, i0(5), n_cols)
    # Inputs receta — 8 cols:
    # A ID-Insumo (texto, futuro: VLOOKUP del catálogo), B Insumo, C $pres, D contenido,
    # E unidad, F $unitario (fórmula), G cantidad (input), H subtotal (fórmula)
    reqs += fmt_input(sid, i0(REC_FIRST), 0, REC_LAST, 1)                  # A ID-Insumo
    reqs += fmt_input(sid, i0(REC_FIRST), 1, REC_LAST, 2)                  # B Insumo
    reqs += fmt_input(sid, i0(REC_FIRST), 2, REC_LAST, 3, FMT_MONEY)       # C $presentación
    reqs += fmt_input(sid, i0(REC_FIRST), 3, REC_LAST, 4, FMT_DECIMAL)     # D contenido
    reqs += fmt_input(sid, i0(REC_FIRST), 4, REC_LAST, 5)                  # E unidad (texto)
    reqs += fmt_formula(sid, i0(REC_FIRST), 5, REC_LAST, 6, FMT_MONEY_F)   # F $unitario (calc)
    reqs += fmt_input(sid, i0(REC_FIRST), 6, REC_LAST, 7, FMT_DECIMAL)     # G cantidad usada
    reqs += fmt_formula(sid, i0(REC_FIRST), 7, REC_LAST, 8, FMT_MONEY_F)   # H subtotal (calc)

    # Costo Crudo Total (fila CRUDO) — verde fuerte. Valor en col H (al final de subtotales).
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(CRUDO), 0, CRUDO, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_FUE,
            "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(CRUDO), 7, CRUDO, 8),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F,
            "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]

    # Sección MO (fila MO_SEC) + headers
    reqs += fmt_section_label(sid, i0(MO_SEC), n_cols)
    reqs += fmt_header_row(sid, i0(MO_HDR), n_cols)
    reqs += fmt_input(sid, i0(MO_MIN), 1, MO_MIN, 2, FMT_INT)
    reqs += fmt_formula(sid, i0(MO_PER), 1, MO_PER, 2, FMT_MONEY_F)
    reqs += fmt_formula(sid, i0(MO_PERU), 1, MO_PERU, 2, FMT_MONEY_F)
    reqs += fmt_formula(sid, i0(SERV_PERU), 1, SERV_PERU, 2, FMT_MONEY_F)
    reqs += fmt_input(sid, i0(MERMAS), 1, MERMAS, 2, FMT_PCT)

    # Sección RESULTADO
    reqs += fmt_section_label(sid, i0(RES_SEC), n_cols)
    # TOTAL row: B$ + F%
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(TOTAL), 0, TOTAL, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_MED,
            "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(TOTAL), 1, TOTAL, 2),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(TOTAL), 2, TOTAL, 5),
        "cell": {"userEnteredFormat": {
            "textFormat": {"bold": True, "fontSize": 10, "foregroundColor": VERDE_OSC},
            "horizontalAlignment": "RIGHT"}},
        "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(TOTAL), 5, TOTAL, 6),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_PCT, "horizontalAlignment": "CENTER",
            "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment,textFormat)"}}]

    # MARGEN (input %)
    reqs += fmt_input(sid, i0(MARGEN), 1, MARGEN, 2, FMT_PCT)

    # VENTA row: B$ + F%  (verde fuerte resultado clave)
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(VENTA), 0, VENTA, n_cols),
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_FUE,
            "textFormat": {"bold": True, "fontSize": 13, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(VENTA), 1, VENTA, 2),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_MONEY_F, "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(VENTA), 2, VENTA, 5),
        "cell": {"userEnteredFormat": {
            "textFormat": {"bold": True, "fontSize": 10, "foregroundColor": VERDE_OSC},
            "horizontalAlignment": "RIGHT"}},
        "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}}]
    reqs += [{"repeatCell": {
        "range": _rng(sid, i0(VENTA), 5, VENTA, 6),
        "cell": {"userEnteredFormat": {"numberFormat": FMT_PCT, "horizontalAlignment": "CENTER",
            "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(numberFormat,horizontalAlignment,textFormat)"}}]

    # Labels col A en sección MO
    reqs += fmt_label(sid, i0(MO_HDR), 0, MERMAS, 1)

    # Anchos (8 columnas)
    for i, w in enumerate([85, 240, 120, 90, 75, 100, 95, 110]):
        reqs.append(col_width(sid, i, w))

    # Freeze título (2 filas)
    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
        "fields": "gridProperties.frozenRowCount"}})

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

    # Estructura objetivo
    target = ["📋 Resumen Cocina", "📦 Costos y Tarifas"] + [p[1] for p in PROCESOS]
    existing = {w.title: w for w in ss.worksheets()}

    # Crear las que faltan, en orden
    for name in target:
        if name not in existing:
            ss.add_worksheet(title=name, rows=60, cols=10)
            print(f"  + creada: {name}")
        else:
            print(f"  · existe: {name}")

    # Refresh
    existing = {w.title: w for w in ss.worksheets()}

    # Borrar las que sobran
    for w in ss.worksheets():
        if w.title not in target:
            ss.del_worksheet(w)
            print(f"  - borrada: {w.title}")

    # Refresh
    existing = {w.title: w for w in ss.worksheets()}

    # Reordenar hojas según target
    for i, name in enumerate(target):
        ws = existing[name]
        ss.reorder_worksheets([ws] if i == 0 else
                              [existing[t] for t in target if t in existing])
        break  # solo se hace 1 vez con todas

    # Construir cada hoja (resumen al final para que las refs a otras hojas existan)
    for slug, sheet_name, label, ins, unit in PROCESOS:
        ws = existing[sheet_name]
        print(f"  → ficha: {sheet_name}")
        build_ficha_proceso(ws, ss, slug, sheet_name, label, ins, unit)

    print(f"  → costos")
    build_costos(existing["📦 Costos y Tarifas"], ss)

    print(f"  → resumen")
    build_resumen(existing["📋 Resumen Cocina"], ss)

    print(f"\n✓ Listo")
    print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
