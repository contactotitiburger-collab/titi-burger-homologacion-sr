#!/usr/bin/env python3
"""
nomina_aplicar_respuestas.py — cron lunes/martes 3pm.

Flujo:
1. Encuentra el Sheet de preguntas de la semana pasada.
2. Lee columna "Respuesta Nancy" — si tiene texto en una celda flageada,
   la anota como "respondida" y la aplica al Sheet Reglas.
3. Regenera la nómina con reglas actualizadas.
4. Sube versión final a Drive.
5. Manda WA a Rafael con el link y resumen de qué se aplicó.
"""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

STAFF_WA = "+5216861445614"
SA_FILE = "/home/tito/.openclaw/credentials/google/service-account.json"
SA_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]
GENERADOR = "/home/tito/.openclaw/scripts/nomina_generar_semana.py"
LOG_DIR = Path("/home/tito/.openclaw/logs")
SESAME_DIR = Path("/home/tito/.openclaw/data/nomina")
REGLAS_ID = None  # se resuelve por nombre en runtime
NOMINAS_FOLDER = "1qBpjmHZr_-F-bBo793J_7I6Q1yPWEHnU"

MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]


def semana_pasada():
    hoy = date.today()
    lunes_esta = hoy - timedelta(days=hoy.weekday())
    lunes_pasada = lunes_esta - timedelta(days=7)
    domingo_pasada = lunes_pasada + timedelta(days=6)
    _, iso, _ = lunes_pasada.isocalendar()
    return iso, lunes_pasada, domingo_pasada


def clientes():
    c = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SA_SCOPES)
    return build("drive", "v3", credentials=c), build("sheets", "v4", credentials=c)


def encontrar_sheet_preguntas(drv, sem):
    r = drv.files().list(
        q=f"name contains 'Preguntas Nancy - S{sem}' and trashed = false",
        fields="files(id,name)"
    ).execute()
    files = r.get("files", [])
    return files[0]["id"] if files else None


def leer_respuestas_nancy(sh, preg_id):
    """
    Devuelve dict {fila: respuesta_texto} SOLO de la columna 'RESPUESTA NANCY'
    (col AN, agregada formalmente al Sheet de preguntas).
    Ignora vacías, guiones, y números sueltos (que indican basura, no respuesta real).
    """
    respuestas = {}
    meta = sh.spreadsheets().get(spreadsheetId=preg_id).execute()
    sheet_name = meta["sheets"][0]["properties"]["title"]
    # Verificar que el header AN6 diga literalmente "RESPUESTA NANCY"
    header = sh.spreadsheets().values().get(
        spreadsheetId=preg_id, range=f"'{sheet_name}'!AN6"
    ).execute().get("values", [])
    if not header or not header[0] or "RESPUESTA NANCY" not in header[0][0].upper():
        print("[warn] no encontré col 'RESPUESTA NANCY' formal — no aplico nada")
        return {}
    # Leer respuestas filas 9-40
    resp = sh.spreadsheets().values().get(
        spreadsheetId=preg_id, range=f"'{sheet_name}'!AN9:AN40"
    ).execute().get("values", [])
    for i, row in enumerate(resp):
        if not row: continue
        v = str(row[0]).strip()
        if not v or v == "-": continue
        # Debe tener al menos 3 caracteres alfabéticos para ser respuesta real
        if sum(1 for ch in v if ch.isalpha()) < 3: continue
        respuestas[9 + i] = v
    return respuestas


def encontrar_reglas_id(drv):
    r = drv.files().list(
        q="name = 'Reglas de Nómina - Nancy' and trashed = false",
        fields="files(id)"
    ).execute()
    files = r.get("files", [])
    return files[0]["id"] if files else None


def aplicar_a_reglas(sh, reglas_id, respuestas_por_fila_preguntas):
    """Guarda cada respuesta como nota en Reglas (col K = Actualizado por Nancy)."""
    # Mapa filaExcel → filaSheetReglas (mismo orden empleados, offset diferente)
    # Fila 9 en Preguntas ≡ empleado 1 = fila 2 en Reglas (headers en 1)
    if not respuestas_por_fila_preguntas:
        return 0
    updates = []
    for fila_p, texto in respuestas_por_fila_preguntas.items():
        fila_reglas = fila_p - 9 + 2
        # Agregar timestamp + respuesta a col J (Notas Nancy) y K (Actualizado)
        updates.append({"range": f"J{fila_reglas}", "values": [[texto]]})
        updates.append({"range": f"K{fila_reglas}", "values": [[datetime.now().strftime("%Y-%m-%d %H:%M")]]})
    if updates:
        sh.spreadsheets().values().batchUpdate(
            spreadsheetId=reglas_id,
            body={"data": updates, "valueInputOption": "USER_ENTERED"}
        ).execute()
    return len(respuestas_por_fila_preguntas)


def regenerar_nomina(sem, desde, hasta):
    sesame = SESAME_DIR / f"sesame_export_sem{sem}.xlsx"
    if not sesame.exists():
        return None, f"Falta SESAME de sem {sem}"
    output = Path(f"/tmp/nomina_sem{sem}_actualizada.xlsx")
    r = subprocess.run(["python3", GENERADOR,
                        "--sem", str(sem),
                        "--from", desde.isoformat(), "--to", hasta.isoformat(),
                        "--sesame", str(sesame),
                        "--output", str(output)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return None, r.stderr[-500:]
    return output, None


def subir_a_drive(drv, xlsx, sem, desde, hasta):
    if desde.month == hasta.month:
        rango = f"{desde.day} al {hasta.day} {MESES[desde.month-1]} {desde.year}"
    else:
        rango = f"{desde.day} {MESES[desde.month-1]} al {hasta.day} {MESES[hasta.month-1]} {hasta.year}"
    nombre = f"Nómina - Semana {sem} ({rango})"
    r = drv.files().list(
        q=f"name = '{nombre}' and '{NOMINAS_FOLDER}' in parents and trashed = false",
        fields="files(id)"
    ).execute()
    ex = r.get("files", [])
    media = MediaFileUpload(str(xlsx),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if ex:
        r = drv.files().update(fileId=ex[0]["id"], media_body=media,
                                fields="id,webViewLink").execute()
    else:
        meta = {"name": nombre, "parents": [NOMINAS_FOLDER],
                "mimeType": "application/vnd.google-apps.spreadsheet"}
        r = drv.files().create(body=meta, media_body=media,
                                fields="id,webViewLink").execute()
    return r["webViewLink"]


def enviar_wa(msg):
    import os
    if os.environ.get("NOMINA_NO_WA") == "1":
        return  # suprimido cuando lo corre Tito manual
    subprocess.run(["openclaw", "message", "send",
                    "--channel", "whatsapp", "--target", STAFF_WA,
                    "--message", msg], check=False)


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"nomina_aplicar_{date.today().isoformat()}.log"
    with log_path.open("a") as lf:
        def log(m):
            line = f"{datetime.now().isoformat(timespec='seconds')} {m}"
            lf.write(line + "\n"); lf.flush(); print(line)

        sem, desde, hasta = semana_pasada()
        log(f"=== Aplicar respuestas Nancy — sem {sem} ({desde} a {hasta}) ===")

        drv, sh = clientes()

        preg_id = encontrar_sheet_preguntas(drv, sem)
        if not preg_id:
            log(f"No hay Sheet de preguntas para S{sem}. Nada que aplicar.")
            return

        respuestas = leer_respuestas_nancy(sh, preg_id)
        log(f"Respuestas encontradas: {len(respuestas)}")

        reglas_id = encontrar_reglas_id(drv)
        if reglas_id and respuestas:
            n = aplicar_a_reglas(sh, reglas_id, respuestas)
            log(f"Aplicadas a Reglas: {n}")

        xlsx, err = regenerar_nomina(sem, desde, hasta)
        if err:
            log(f"ERROR regenerar: {err}")
            enviar_wa(f"⚠️ Rafael, no pude regenerar nómina S{sem}: {err}")
            return
        link = subir_a_drive(drv, xlsx, sem, desde, hasta)
        log(f"Nómina actualizada: {link}")

        msg = (
            f"Nómina S{sem} actualizada.\n\n"
            f"Respuestas de Nancy aplicadas: {len(respuestas)}.\n\n"
            f"Link: {link}"
        )
        # Re-aplicar highlights de diff vs Nancy (se borran al regenerar)
        try:
            subprocess.run(["python3", "/home/tito/.openclaw/scripts/nomina_highlights_diff_nancy.py"],
                           check=False, timeout=60)
        except Exception as e:
            log(f"[warn] highlights fallaron: {e}")

        enviar_wa(msg)
        log("=== Fin ===")


if __name__ == "__main__":
    main()
