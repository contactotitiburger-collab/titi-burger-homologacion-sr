#!/usr/bin/env python3
"""Sincroniza Catálogo de Gastos → Presupuesto Mensual (tracker de pagos).

Cada minuto:
1. Lee el Sheet "Catálogo de Gastos" (Drive)
2. Detecta filas con fondo VERDE FULL → estas son las "activas para presupuesto"
3. Convierte "Monto que aparece" a monto MENSUAL según Frecuencia:
   - Semanal → × 4.33
   - Mensual → tal cual
   - Bimestral → ÷ 2
   - Anual → ÷ 12
   - Único → tal cual (nota como "único del mes")
4. Escribe al Sheet "Presupuesto Mensual - Titi Burger" con MERGE INTELIGENTE:
   - Filas ya existentes → preserva columnas ¿Pagado? / Fecha pago / Forma / Referencia / Notas
   - Filas nuevas (verde nuevo) → agrega en blanco esas columnas
   - Filas quitadas (ya no verde) → las marca como "QUITADO" pero no borra el histórico de pago

Objetivo: Rafael/Nancy pueden ir marcando en el mismo Sheet cómo se pagó cada rubro.

Log: ~/.openclaw/logs/presupuesto_mensual.log
Estado: ~/.openclaw/state/presupuesto_mensual.json
"""
import json
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
STATE = Path("/home/tito/.openclaw/state/presupuesto_mensual.json")
LOG = Path("/home/tito/.openclaw/logs/presupuesto_mensual.log")
LOG.parent.mkdir(parents=True, exist_ok=True)
STATE.parent.mkdir(parents=True, exist_ok=True)

CATALOGO_SHEET_ID = "19EkBZLxagM6t0ZK6M-9B0SzJGCSlIAwIV2UrsGZ63K0"
FOLDER_ORIGINALES = "1Bql9OzXtZ_OBNikYF3KEr0qJUA83f-U2"
# El presupuesto se movió a "Titiburger las originales / Presupuestos" el 20-jul-2026.
FOLDER_PRESUPUESTOS = "18_puRYz8VEqTiIPR7cCLP6UHShTUUn1s"
NOMBRE_MENSUAL = "Presupuesto Mensual - Titi Burger"

SEM_MES = 4.33

# Columnas del Presupuesto Mensual
COLS_CATALOGO = ["Concepto", "Fuente", "Monto original", "Frecuencia", "Tipo", "Estado catálogo"]
COLS_CALCULO = ["Monto MENSUAL"]
COLS_TRACKER = ["¿Pagado?", "Fecha pago", "Forma pago", "Referencia", "Notas de pago"]
ALL_COLS = COLS_CATALOGO + COLS_CALCULO + COLS_TRACKER


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    with LOG.open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def get_services():
    tok = json.loads(TOKENS.read_text())
    creds = Credentials(token=tok["token"], refresh_token=tok["refresh_token"],
        token_uri=tok["token_uri"], client_id=tok["client_id"],
        client_secret=tok["client_secret"], scopes=tok["scopes"])
    if not creds.valid:
        creds.refresh(Request())
        tok["token"] = creds.token
        TOKENS.write_text(json.dumps(tok, indent=2))
    return build("sheets", "v4", credentials=creds), build("drive", "v3", credentials=creds)


def es_verde_full(fmt):
    """Verde BRILLANTE que Rafael pinta a propósito (green>=0.7, red<=0.4, blue<=0.4).
    Excluye los verdes decorativos del Catálogo original (headers de sección)."""
    if not fmt: return False
    bg = fmt.get("backgroundColor") or {}
    r, g, b = bg.get("red", 0), bg.get("green", 0), bg.get("blue", 0)
    if r == 1 and g == 1 and b == 1: return False
    return g >= 0.7 and r <= 0.4 and b <= 0.4


def a_mensual(monto_str, frecuencia_str):
    if monto_str is None or str(monto_str).strip() == "":
        return None, "sin monto"
    try:
        monto = float(str(monto_str).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None, f"ilegible: {monto_str}"
    freq = (frecuencia_str or "").strip().lower()
    if not freq or freq == "n/a":
        return monto, "único (tal cual)"
    if "semanal" in freq:
        return round(monto * SEM_MES, 2), "semanal × 4.33"
    if "mensual" in freq:
        return monto, "mensual (tal cual)"
    if "bimestral" in freq:
        return round(monto / 2, 2), "bimestral ÷ 2"
    if "anual" in freq:
        return round(monto / 12, 2), "anual ÷ 12"
    if "único" in freq or "unico" in freq:
        return monto, "único (tal cual)"
    return monto, f"freq desconocida: {freq}"


def leer_catalogo(sheets):
    r = sheets.spreadsheets().get(
        spreadsheetId=CATALOGO_SHEET_ID,
        ranges=["A1:H200"],
        includeGridData=True,
        fields="sheets(data(rowData(values(formattedValue,effectiveFormat(backgroundColor)))))"
    ).execute()
    hojas = r.get("sheets", [])
    if not hojas: return []
    rows = hojas[0]["data"][0].get("rowData", [])
    out = []
    for row in rows:
        cells = row.get("values", [])
        vals = [c.get("formattedValue", "") for c in cells]
        fmts = [c.get("effectiveFormat", {}) for c in cells]
        verdes = [es_verde_full(f) for f in fmts[:5]]
        casi_todas = sum(verdes) >= 2
        out.append({"valores": vals, "verde": casi_todas})
    return out


def obtener_o_crear_presupuesto(sheets, drive):
    q = f"'{FOLDER_PRESUPUESTOS}' in parents and name = '{NOMBRE_MENSUAL}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed=false"
    r = drive.files().list(q=q, fields="files(id,name)").execute()
    if r.get("files"):
        return r["files"][0]["id"]
    log(f"Creando Sheet '{NOMBRE_MENSUAL}'…")
    sh = sheets.spreadsheets().create(body={"properties": {"title": NOMBRE_MENSUAL}}, fields="spreadsheetId").execute()
    sid = sh["spreadsheetId"]
    drive.files().update(fileId=sid, addParents=FOLDER_PRESUPUESTOS, removeParents="root", fields="id").execute()
    log(f"Creado {sid}")
    return sid


def leer_presupuesto_actual(sheets, sheet_id):
    """Lee el presupuesto mensual actual para preservar la info del tracker."""
    try:
        r = sheets.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="A1:L500"
        ).execute()
        values = r.get("values", [])
        if not values: return {}
        # buscar fila de headers
        header_row = None
        for i, row in enumerate(values):
            if row and "Concepto" in row and "¿Pagado?" in row:
                header_row = i
                break
        if header_row is None: return {}
        headers = values[header_row]
        idx = {h: headers.index(h) for h in ALL_COLS if h in headers}
        by_concepto = {}
        for row in values[header_row + 1:]:
            if not row or not row[idx.get("Concepto", 0)]:
                continue
            concepto = row[idx["Concepto"]]
            tracker = {c: row[idx[c]] if idx.get(c) is not None and idx[c] < len(row) else ""
                       for c in COLS_TRACKER}
            by_concepto[concepto] = tracker
        return by_concepto
    except Exception as e:
        log(f"leer_presupuesto_actual ERROR: {e}")
        return {}


def escribir_presupuesto(sheets, sheet_id, verdes, tracker_previo):
    mes_actual = datetime.now().strftime("%B %Y").upper()
    ahora = datetime.now().strftime("%d %b %Y · %H:%M")

    contenido = [
        [f"PRESUPUESTO MENSUAL · TITI BURGER · {mes_actual}"],
        [f"Última sincronización: {ahora}  ·  Fuente: Catálogo de Gastos (filas en verde)"],
        [],
        ["Marca en VERDE una fila del Catálogo → aparece aquí en <1 min."],
        ["Al pagar: llena 'Fecha pago' + 'Forma pago' + 'Referencia'. Esa info NO se borra al re-sincronizar."],
        [],
        ALL_COLS,
    ]

    filas_ordenadas = []
    total = 0.0
    conceptos_activos = set()
    for r in verdes:
        v = r["valores"] + [""] * (8 - len(r["valores"]))
        concepto, fuente, monto_orig, freq, monto_mensual_cat, tipo, estado, notas = v[:8]
        if not concepto:
            continue
        conceptos_activos.add(concepto)
        mensual, calc = a_mensual(monto_orig, freq)
        if mensual is not None:
            total += mensual
        tr = tracker_previo.get(concepto, {c: "" for c in COLS_TRACKER})
        filas_ordenadas.append([
            concepto, fuente, monto_orig, freq, tipo, estado,
            f"${mensual:,.2f}" if mensual is not None else "—",
            tr.get("¿Pagado?", ""),
            tr.get("Fecha pago", ""),
            tr.get("Forma pago", ""),
            tr.get("Referencia", ""),
            tr.get("Notas de pago", ""),
        ])

    # filas del histórico que YA NO están verdes (mantener con marca QUITADO)
    for concepto, tr in tracker_previo.items():
        if concepto in conceptos_activos:
            continue
        # solo si tienen info de pago capturada — sino se van
        if any(tr.get(c) for c in COLS_TRACKER):
            filas_ordenadas.append([
                concepto, "—", "—", "—", "—", "QUITADO del catálogo verde",
                "—",
                tr.get("¿Pagado?", ""),
                tr.get("Fecha pago", ""),
                tr.get("Forma pago", ""),
                tr.get("Referencia", ""),
                tr.get("Notas de pago", ""),
            ])

    filas_ordenadas.sort(key=lambda x: (x[5] == "QUITADO del catálogo verde", x[0].lower()))

    contenido.extend(filas_ordenadas)
    contenido.extend([
        [],
        ["", "", "", "", "", "TOTAL MENSUAL",  f"${total:,.2f}"],
        ["", "", "", "", "", "Equivalente semanal (÷4.33)", f"${total / SEM_MES:,.2f}"],
    ])

    # limpiar + escribir
    sheets.spreadsheets().values().clear(spreadsheetId=sheet_id, range="A1:Z500").execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id, range="A1",
        valueInputOption="RAW",
        body={"values": contenido},
    ).execute()

    # formato bonito: bold headers, background del título, freeze pane
    requests = [
        # título
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1,
                                  "startColumnIndex": 0, "endColumnIndex": len(ALL_COLS)},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.12, "green": 0.22, "blue": 0.4},
                            "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                           "bold": True, "fontSize": 14},
                            "horizontalAlignment": "CENTER",
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        # merge título
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1,
                                  "startColumnIndex": 0, "endColumnIndex": len(ALL_COLS)},
                        "mergeType": "MERGE_ALL"}},
        # headers columnas
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 6, "endRowIndex": 7,
                                  "startColumnIndex": 0, "endColumnIndex": len(ALL_COLS)},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.18, "green": 0.36, "blue": 0.6},
                            "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
                            "horizontalAlignment": "CENTER",
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        # freeze
        {"updateSheetProperties": {"properties": {"sheetId": 0,
                                                  "gridProperties": {"frozenRowCount": 7}},
                                   "fields": "gridProperties.frozenRowCount"}},
    ]
    sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()

    log(f"Escritas {len(filas_ordenadas)} filas · Total ${total:,.2f}/mes")
    return total, len(filas_ordenadas)


def sincronizar():
    sheets, drive = get_services()
    catalogo = leer_catalogo(sheets)
    verdes = [r for r in catalogo if r["verde"]]
    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    # detectar si hay cambio (por # de verdes o hash rápido)
    concepts = tuple(sorted(r["valores"][0] for r in verdes if r["valores"] and r["valores"][0]))
    hash_ahora = hash(concepts)
    if prev.get("hash_conceptos") == hash_ahora and prev.get("count") == len(verdes):
        # sin cambios; solo actualizar timestamp una vez cada 15 min máximo
        last = prev.get("updated_at", "")
        if last and (datetime.now() - datetime.fromisoformat(last)).total_seconds() < 900:
            return  # nada que hacer
    log(f"Catálogo: {len(catalogo)} filas · verdes: {len(verdes)}")
    sheet_id = obtener_o_crear_presupuesto(sheets, drive)
    tracker_previo = leer_presupuesto_actual(sheets, sheet_id)
    log(f"Tracker previo con {len(tracker_previo)} conceptos con info de pago")
    total, n = escribir_presupuesto(sheets, sheet_id, verdes, tracker_previo)
    STATE.write_text(json.dumps({
        "count": len(verdes), "total_mensual": total, "sheet_id": sheet_id,
        "hash_conceptos": hash_ahora,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }, indent=2))


if __name__ == "__main__":
    try:
        sincronizar()
    except Exception as e:
        log(f"ERROR: {e}")
        raise
