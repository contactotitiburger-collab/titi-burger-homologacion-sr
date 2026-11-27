#!/usr/bin/env python3
"""
nancy_novedades_watch.py — corre diario a las 5pm (cron).

Flujo:
1. Baja la hoja "Novedades" del Sheet Cambios de saldos.
2. Compara con el snapshot anterior guardado en state/.
3. Si hay cambios (nuevas filas, modificadas o borradas):
   - Regenera el mensaje de confirmación para Nancy (formato template)
   - Manda por WA a Rafael el mensaje + resumen del diff
   - Guarda el nuevo snapshot
4. Si no hay cambios, no hace nada (silencio).

Regla clave: cada vez que Nancy toca la hoja, todo lo derivado se actualiza.
"""
import json, subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

STAFF_WA = "+5216861445614"
SA_FILE = "/home/tito/.openclaw/credentials/google/service-account.json"
SHEET_ID = "141Tcn1ZYHQQYjbgWM0DZCXT9YX1hExdFKfarLz5mBo8"  # Cambios de saldos Nomina
SNAPSHOT = Path("/home/tito/.openclaw/state/nancy_novedades_snapshot.json")
LOG = Path("/home/tito/.openclaw/logs/nancy_novedades_watch.log")


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    with LOG.open("a") as f: f.write(line + "\n")
    print(line)


def sheets_client():
    c = service_account.Credentials.from_service_account_file(
        SA_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    return build("sheets", "v4", credentials=c)


def drive_client():
    c = service_account.Credentials.from_service_account_file(
        SA_FILE, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    return build("drive", "v3", credentials=c)


def leer_novedades(sh):
    vals = sh.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="'Novedades'!A1:H100"
    ).execute().get('values', [])
    filas = {}
    for i, r in enumerate(vals, 1):
        if i == 1: continue
        if not any(str(c).strip() for c in r): continue
        # Normalizar longitud
        while len(r) < 8: r.append('')
        filas[i] = r
    return filas


def diff(anterior, actual):
    nuevas = {i: r for i, r in actual.items() if i not in anterior}
    borradas = {i: r for i, r in anterior.items() if i not in actual}
    modificadas = {i: (anterior[i], r) for i, r in actual.items()
                    if i in anterior and anterior[i] != r}
    return nuevas, borradas, modificadas


def resumen_diff(nuevas, borradas, modificadas):
    partes = []
    if nuevas:
        partes.append(f"*Nuevas filas:* {len(nuevas)}")
        for i, r in nuevas.items():
            partes.append(f"  R{i}: {r[2]} — {r[3]} {r[4]} — {r[5]}")
    if modificadas:
        partes.append(f"*Modificadas:* {len(modificadas)}")
        for i, (a, r) in modificadas.items():
            partes.append(f"  R{i}: {r[2]} — {r[3]} {r[4]}")
    if borradas:
        partes.append(f"*Borradas:* {len(borradas)}")
        for i, r in borradas.items():
            partes.append(f"  R{i}: {r[2]} — {r[3]} {r[4]}")
    return "\n".join(partes)


def enviar_wa(msg):
    subprocess.run(["openclaw", "message", "send",
                    "--channel", "whatsapp", "--target", STAFF_WA,
                    "--message", msg], check=False)


def main():
    log("=== chequeando novedades Nancy ===")
    sh = sheets_client()
    actual = leer_novedades(sh)
    log(f"Filas actuales: {len(actual)}")

    if not SNAPSHOT.exists():
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps({str(k): v for k, v in actual.items()}, ensure_ascii=False))
        log("Snapshot inicial guardado. No hay diff.")
        return

    anterior = {int(k): v for k, v in json.loads(SNAPSHOT.read_text()).items()}
    nuevas, borradas, modificadas = diff(anterior, actual)

    if not (nuevas or borradas or modificadas):
        log("Sin cambios.")
        return

    log(f"Cambios: {len(nuevas)} nuevas / {len(modificadas)} mod / {len(borradas)} borradas")

    drv = drive_client()
    meta = drv.files().get(fileId=SHEET_ID, fields='modifiedTime').execute()
    resumen = resumen_diff(nuevas, borradas, modificadas)
    msg = (
        f"📋 Nancy actualizó la hoja de Novedades ({meta['modifiedTime'][:16]} UTC).\n\n"
        f"{resumen}\n\n"
        f"Total filas ahora: {len(actual)}. "
        f"Regenera el mensaje para Nancy con el template si toca cerrar la semana."
    )
    enviar_wa(msg)
    log("WA enviado a Rafael.")

    SNAPSHOT.write_text(json.dumps({str(k): v for k, v in actual.items()}, ensure_ascii=False))
    log("Snapshot actualizado.")


if __name__ == "__main__":
    main()
