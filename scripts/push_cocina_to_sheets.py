#!/usr/bin/env python3
"""Sube/actualiza el contenido del Excel Cocina al Sheet nativo en Drive.

Sheet ID:  1HDZLecg11015vt5bBkhpRtn09Z7I9y2SKksi5v7pPM8
SA:        tito-144@titi-burger-497707.iam.gserviceaccount.com

Replica las 3 hojas del openpyxl local en formato Sheets nativo.
Las fórmulas se mantienen iguales (sintaxis Excel == Google Sheets para IF/SUMIFS/etc).
"""
import gspread
from google.oauth2 import service_account

SA       = "/home/tito/.openclaw/credentials/google/service-account.json"
SHEET_ID = "1HDZLecg11015vt5bBkhpRtn09Z7I9y2SKksi5v7pPM8"

VERDE_OSC   = {"red": 0.216, "green": 0.337, "blue": 0.137}  # #375623
VERDE_CLARO = {"red": 0.886, "green": 0.937, "blue": 0.855}  # #E2EFDA
VERDE_L     = {"red": 0.663, "green": 0.816, "blue": 0.557}  # #A9D08E
VERDE_K     = {"red": 0.776, "green": 0.937, "blue": 0.808}  # #C6EFCE
BLANCO      = {"red": 1.0,   "green": 1.0,   "blue": 1.0}


def main():
    creds = service_account.Credentials.from_service_account_file(
        SA, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SHEET_ID)
    print(f"Conectado a: {ss.title}")

    # 1. Limpiar todas las hojas existentes y crear las 3 que queremos
    sheet_names = ["🥩 Costo Cocina", "💰 Costos Fijos Cocina", "📖 Cómo usar"]
    existing = [w.title for w in ss.worksheets()]
    print(f"Hojas existentes: {existing}")

    # Crear las nuevas (si no existen)
    for name in sheet_names:
        if name not in [w.title for w in ss.worksheets()]:
            ss.add_worksheet(title=name, rows=100, cols=20)
            print(f"  + Creada hoja: {name}")

    # Borrar hojas que no son las nuestras (incluyendo "Hoja 1" por default)
    for w in ss.worksheets():
        if w.title not in sheet_names:
            ss.del_worksheet(w)
            print(f"  - Borrada hoja: {w.title}")

    # 2. Hoja 1: 🥩 Costo Cocina
    ws1 = ss.worksheet("🥩 Costo Cocina")
    ws1.clear()
    build_costo_cocina(ws1, ss)

    # 3. Hoja 2: 💰 Costos Fijos Cocina
    ws2 = ss.worksheet("💰 Costos Fijos Cocina")
    ws2.clear()
    build_costos_fijos(ws2, ss)

    # 4. Hoja 3: 📖 Cómo usar
    ws3 = ss.worksheet("📖 Cómo usar")
    ws3.clear()
    build_como_usar(ws3, ss)

    print(f"\nLink: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    print("✓ Listo. El Sheet está actualizado en Drive.")


def build_costo_cocina(ws, ss):
    headers = [
        "ID-PROC", "Producto procesado", "Unidad", "Costo crudo $/u",
        "Mano de obra $/u", "Servicios $/u", "Mermas %",
        "Costo total $/u (= PUNTO EQUILIBRIO $)",
        "Margen Cocina %", "Precio Venta Cocina $/u",
        "% Punto Equilibrio vs Crudo", "% Final vs Crudo (→ Maestro col H)",
        "ID-Maestro (mapeo)", "Notas",
    ]

    # Título + bajada (filas 1-2 mergeadas)
    rows = []
    rows.append([
        "🥩 COSTO COCINA — Cálculo del % Cocina por proceso", "", "", "", "", "",
        "", "", "", "", "", "", "", ""])
    rows.append([
        "Cocina compra crudo, transforma y entrega. Calculamos PUNTO DE EQUILIBRIO "
        "(col K, sin ganar) y % FINAL (col L, equilibrio + margen). El L se linkea al "
        "Maestro col H usando el ID-Maestro de la col M.",
        "", "", "", "", "", "", "", "", "", "", "", "", ""])
    rows.append([""] * 14)  # fila vacía
    rows.append(headers)    # fila 4 = encabezados

    # Datos semilla
    seed = [
        ("PROC-001", "Boneless",                     "kg",  "", "", "", "", "", "INS-029", "Pollo empanizado. INS-029 = 320g; INS-030 = 180g jala mismo %"),
        ("PROC-002", "Dedos de queso",               "pza", "", "", "", "", "", "—",       "⚠️ NO existe en Maestro — agregar fila INS nueva o quitar"),
        ("PROC-003", "Tiras de pollo empanizado",    "kg",  "", "", "", "", "", "—",       "⚠️ NO existe en Maestro — agregar fila INS nueva o quitar"),
        ("PROC-004", "Tocino",                       "kg",  "", "", "", "", "", "INS-037", ""),
        ("PROC-005", "Patty (carne molida en casa)", "pza", "", "", "", "", "", "INS-031", "INS-031 = CARNE PAQ / 20 PZA. Se muele en cocina."),
        ("PROC-006", "Pollo",                        "kg",  "", "", "", "", "", "INS-035", "Filete / pieza"),
    ]
    start = 5
    for i, row in enumerate(seed):
        r = start + i
        id_p, producto, unidad, d, e, f, g, ide_margen, id_maestro, notas = (
            row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9])
        # Filas con fórmulas — usar fórmulas en cada celda
        rows.append([
            id_p, producto, unidad, d, e, f, g,
            # H = costo total = (D+E+F)/(1-G)
            f'=IF(OR(D{r}="",E{r}="",F{r}="",G{r}=""),"",(D{r}+E{r}+F{r})/(1-G{r}))',
            ide_margen,
            # J = H*(1+I)
            f'=IF(OR(H{r}="",I{r}=""),"",H{r}*(1+I{r}))',
            # K = H/D - 1
            f'=IF(OR(H{r}="",D{r}="",D{r}=0),"",H{r}/D{r}-1)',
            # L = J/D - 1
            f'=IF(OR(J{r}="",D{r}="",D{r}=0),"",J{r}/D{r}-1)',
            id_maestro,
            notas,
        ])

    # 10 filas extras vacías
    for i in range(len(seed), len(seed) + 10):
        r = start + i
        rows.append([
            f"PROC-{i+1:03d}", "", "", "", "", "", "",
            f'=IF(OR(D{r}="",E{r}="",F{r}="",G{r}=""),"",(D{r}+E{r}+F{r})/(1-G{r}))',
            "",
            f'=IF(OR(H{r}="",I{r}=""),"",H{r}*(1+I{r}))',
            f'=IF(OR(H{r}="",D{r}="",D{r}=0),"",H{r}/D{r}-1)',
            f'=IF(OR(J{r}="",D{r}="",D{r}=0),"",J{r}/D{r}-1)',
            "", "",
        ])

    ws.update("A1", rows, value_input_option="USER_ENTERED")

    # Formato
    sid = ws.id
    requests = []
    # Merge título y subtítulo
    requests.append({"mergeCells": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 14},
        "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {
        "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 14},
        "mergeType": "MERGE_ALL"}})
    # Título grande
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 14},
        "cell": {"userEnteredFormat": {
            "textFormat": {"fontSize": 16, "bold": True, "foregroundColor": VERDE_OSC},
            "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE"}},
        "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"}})
    # Subtítulo
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 14},
        "cell": {"userEnteredFormat": {
            "textFormat": {"fontSize": 10, "italic": True},
            "wrapStrategy": "WRAP", "horizontalAlignment": "LEFT"}},
        "fields": "userEnteredFormat(textFormat,wrapStrategy,horizontalAlignment)"}})
    # Encabezados (fila 4 → idx 3)
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 14},
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_OSC,
            "textFormat": {"foregroundColor": BLANCO, "bold": True, "fontSize": 10},
            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP"}},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"}})
    # Inputs (D,E,F,G,I,M,N) = fondo verde claro. Cols 4,5,6,7,9,13,14 (1-indexed) → idx 3,4,5,6,8,12,13
    for col_idx in [1, 2, 3, 4, 5, 6, 8, 12, 13]:  # B,C,D,E,F,G,I,M,N
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 5 + len(seed) + 10,
                      "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
            "cell": {"userEnteredFormat": {"backgroundColor": VERDE_CLARO,
                "textFormat": {"foregroundColor": VERDE_OSC, "bold": True}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    # Cols K y L (idx 10, 11) — resaltadas. L con verde fuerte (el dato clave)
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 5 + len(seed) + 10,
                  "startColumnIndex": 10, "endColumnIndex": 11},
        "cell": {"userEnteredFormat": {"backgroundColor": VERDE_K,
            "textFormat": {"bold": True}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 5 + len(seed) + 10,
                  "startColumnIndex": 11, "endColumnIndex": 12},
        "cell": {"userEnteredFormat": {"backgroundColor": VERDE_L,
            "textFormat": {"bold": True, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    # H (idx 7) costo total = también resaltado (punto equilibrio $)
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 5 + len(seed) + 10,
                  "startColumnIndex": 7, "endColumnIndex": 8},
        "cell": {"userEnteredFormat": {"backgroundColor": VERDE_K,
            "textFormat": {"bold": True}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    # J (idx 9) precio venta = también resaltado
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 5 + len(seed) + 10,
                  "startColumnIndex": 9, "endColumnIndex": 10},
        "cell": {"userEnteredFormat": {"backgroundColor": VERDE_K,
            "textFormat": {"bold": True}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    # Formatos numéricos: $ para D,E,F,H,J (idx 3,4,5,7,9). % para G,I,K,L (idx 6,8,10,11)
    for col_idx in [3, 4, 5, 7, 9]:
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 5 + len(seed) + 10,
                      "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "\"$\"#,##0.00"}}},
            "fields": "userEnteredFormat.numberFormat"}})
    for col_idx in [6, 8, 10, 11]:
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 5 + len(seed) + 10,
                      "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}},
            "fields": "userEnteredFormat.numberFormat"}})

    # Anchos de columna
    widths = [85, 220, 65, 100, 100, 95, 75, 130, 95, 130, 130, 140, 100, 220]
    for i, w in enumerate(widths):
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": w},
            "fields": "pixelSize"}})

    # Altura del encabezado
    requests.append({"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "ROWS", "startIndex": 3, "endIndex": 4},
        "properties": {"pixelSize": 50},
        "fields": "pixelSize"}})

    # Freeze (solo filas — no se puede congelar columnas con título mergeado)
    requests.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 4}},
        "fields": "gridProperties.frozenRowCount"}})

    ss.batch_update({"requests": requests})


def build_costos_fijos(ws, ss):
    rows = []
    rows.append(["💰 COSTOS FIJOS COCINA (referencia mensual)", "", "", ""])
    rows.append(["Estima MO $/u y Servicios $/u de la hoja Costo Cocina. Total $/mes ÷ volumen = costo por unidad.", "", "", ""])
    rows.append(["", "", "", ""])
    rows.append(["Concepto", "$ / mes", "% asignado a cocina", "Notas"])
    fijos = [
        ("Nómina cocineras",        "", 1.0,  "Sueldos brutos + prestaciones"),
        ("Renta — parte cocina",    "", "",   "Si la cocina es compartida, % del espacio"),
        ("Luz cocina",              "", "",   "Estimado o % del recibo"),
        ("Gas",                     "", 1.0,  "Recarga mensual de tanque"),
        ("Agua cocina",             "", "",   ""),
        ("Mantenimiento equipo",    "", 1.0,  "Promedio mensual"),
        ("Limpieza / químicos",     "", 1.0,  ""),
        ("Empaques cocina interna", "", 1.0,  "Bolsas, film, contenedores"),
        ("Mermas no registradas",   "", 1.0,  "Buffer por desperdicios sin contabilizar"),
        ("Otros (especificar)",     "", 1.0,  ""),
    ]
    for f in fijos:
        rows.append(list(f))
    last = 4 + len(fijos)  # última fila de fijos
    # Fila vacía
    rows.append(["", "", "", ""])
    # Total
    total_row_idx = len(rows) + 1  # 1-indexed
    rows.append(["TOTAL costos fijos / mes asignados a cocina",
                 f"=SUMPRODUCT(B5:B{last},C5:C{last})", "", ""])
    # Espacio
    rows.append(["", "", "", ""])
    rows.append(["", "", "", ""])
    # MO calculada
    mo_title_row = len(rows) + 1
    rows.append(["🧮 TARIFA MANO DE OBRA (driver principal)", "", "", ""])
    rows.append(["Nómina cocineras / mes (total)", "", "", "Sueldos brutos del equipo"])
    nom_row = len(rows)
    rows.append(["Horas trabajadas / mes (todo el equipo)", "", "", "Ej: 3 × 8h × 26 días = 624 h"])
    hrs_row = len(rows)
    rows.append(["$/hora MO", f'=IF(OR(B{nom_row}="",B{hrs_row}="",B{hrs_row}=0),"",B{nom_row}/B{hrs_row})', "", "Calculado"])
    hr_row = len(rows)
    rows.append(["$/minuto MO  ← este se usa para estimar col E", f'=IF(B{hr_row}="","",B{hr_row}/60)', "", "Multiplique por min/unidad"])
    rows.append(["", "", "", ""])
    rows.append(["", "", "", ""])
    rows.append(["📦 VOLUMEN MENSUAL (para prorratear gas/luz)", "", "", ""])
    rows.append(["Unidades totales procesadas / mes", "", "", ""])
    vol_row = len(rows)
    rows.append(["Servicios $/u sugerido (gas+luz / volumen)",
                 f'=IF(OR(B{vol_row}="",B{vol_row}=0),"",(SUMIFS(B5:B{last},A5:A{last},"Gas")+SUMIFS(B5:B{last},A5:A{last},"Luz cocina"))/B{vol_row})',
                 "", ""])

    ws.update("A1", rows, value_input_option="USER_ENTERED")

    sid = ws.id
    requests = []
    # Encabezados
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 4},
        "cell": {"userEnteredFormat": {
            "textFormat": {"fontSize": 14, "bold": True, "foregroundColor": VERDE_OSC},
            "horizontalAlignment": "LEFT"}},
        "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}})
    requests.append({"mergeCells": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 4},
        "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {
        "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 4},
        "mergeType": "MERGE_ALL"}})
    # Fila headers (fila 4 → idx 3)
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 4},
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_OSC,
            "textFormat": {"foregroundColor": BLANCO, "bold": True},
            "horizontalAlignment": "CENTER"}},
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}})
    # Inputs B y C (idx 1, 2) en filas de fijos
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": last,
                  "startColumnIndex": 1, "endColumnIndex": 3},
        "cell": {"userEnteredFormat": {"backgroundColor": VERDE_CLARO}},
        "fields": "userEnteredFormat.backgroundColor"}})
    # Fila TOTAL — destacada
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": total_row_idx - 1, "endRowIndex": total_row_idx,
                  "startColumnIndex": 0, "endColumnIndex": 4},
        "cell": {"userEnteredFormat": {
            "backgroundColor": VERDE_L,
            "textFormat": {"bold": True, "foregroundColor": VERDE_OSC, "fontSize": 12}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    # Bloque MO
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": mo_title_row - 1, "endRowIndex": mo_title_row,
                  "startColumnIndex": 0, "endColumnIndex": 4},
        "cell": {"userEnteredFormat": {
            "textFormat": {"fontSize": 14, "bold": True, "foregroundColor": VERDE_OSC}}},
        "fields": "userEnteredFormat.textFormat"}})
    requests.append({"mergeCells": {
        "range": {"sheetId": sid, "startRowIndex": mo_title_row - 1, "endRowIndex": mo_title_row,
                  "startColumnIndex": 0, "endColumnIndex": 4},
        "mergeType": "MERGE_ALL"}})
    # Formato $ y %
    # Col B en filas de fijos = $
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": last,
                  "startColumnIndex": 1, "endColumnIndex": 2},
        "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "\"$\"#,##0.00"}}},
        "fields": "userEnteredFormat.numberFormat"}})
    # Col C en filas de fijos = %
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": last,
                  "startColumnIndex": 2, "endColumnIndex": 3},
        "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0%"}}},
        "fields": "userEnteredFormat.numberFormat"}})
    # Col B en total
    requests.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": total_row_idx - 1, "endRowIndex": total_row_idx,
                  "startColumnIndex": 1, "endColumnIndex": 2},
        "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "\"$\"#,##0.00"}}},
        "fields": "userEnteredFormat.numberFormat"}})
    # Anchos
    for i, w in enumerate([300, 130, 140, 350]):
        requests.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": w}, "fields": "pixelSize"}})

    ss.batch_update({"requests": requests})


def build_como_usar(ws, ss):
    rows = [
        ["📖 CÓMO USAR ESTE EXCEL", ""],
        ["", ""],
        ["1.", "Llene COSTOS FIJOS COCINA (hoja 2) primero — meta los $/mes reales."],
        ["",   "    Llene también nómina + horas trabajadas para que salga $/min MO."],
        ["",   "    Llene volumen mensual procesado para que salgan servicios $/u."],
        ["2.", "Vaya a COSTO COCINA (hoja 1). Por cada producto:"],
        ["",   "    D = Costo crudo $/unidad (del Maestro)"],
        ["",   "    E = Mano de obra $/unidad (min × tarifa de hoja 2)"],
        ["",   "    F = Servicios $/unidad (de hoja 2)"],
        ["",   "    G = Mermas % (10% típico)"],
        ["",   "    I = Margen Cocina %"],
        ["3.", "El Excel calcula: H (costo total = punto equilibrio), J (precio venta),"],
        ["",   "    K (% punto equilibrio), L (% final → Maestro)"],
        ["4.", "Dos números clave para Ud.:"],
        ["",   "    K = lo que cuesta producir (sin ganar) — para tomar decisiones de precio"],
        ["",   "    L = % final que va al Maestro col H (ya con margen)"],
        ["5.", "M = ID-Maestro. Linkea a la fila del Maestro donde va el % de ese producto."],
        ["",   ""],
        ["REGLAS:", ""],
        ["•", "Celdas VERDE CLARO = inputs (las llena usted)."],
        ["•", "Celdas BLANCAS o resaltadas = fórmulas (no las toque)."],
        ["•", "Celdas VERDE FUERTE (L) = el resultado clave que va al Maestro."],
    ]
    ws.update("A1", rows, value_input_option="USER_ENTERED")
    sid = ws.id
    requests = [
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 80}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
            "properties": {"pixelSize": 800}, "fields": "pixelSize"}},
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 2},
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontSize": 16, "bold": True, "foregroundColor": VERDE_OSC}}},
            "fields": "userEnteredFormat.textFormat"}},
    ]
    ss.batch_update({"requests": requests})


if __name__ == "__main__":
    main()
