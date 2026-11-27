#!/usr/bin/env python3
"""
nomina_lunes_check.py — cron lunes que arma la nómina completa de la
semana pasada en el formato de Andrónica y la sube a Drive.

Flujo:
1. Calcula semana ISO pasada (lunes-domingo previos).
2. Descarga SESAME de esa semana con download_sesame.js.
3. Corre nomina_generar_semana.py → xlsx con formato Andrónica.
4. Sube el xlsx a Drive como Google Sheet en "Nominas Excel".
5. Corre backup .db.gz + .xlsx a Drive.
6. Manda WA a Rafael con el link DIRECTO al Sheet.

Reintentos: si SESAME falla, espera 30min y reintenta hasta 3 veces.
Si después de 3 falla, manda WA de alerta a Rafael.

Instalado 13-jul-2026 (integración generador 13-jul tarde).
"""

import io
import json
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

STAFF_WA = "+5216861445614"
SESAME_SCRIPT = Path("/home/tito/.openclaw/scripts/sesame_bot/download_sesame.js")
GENERADOR = Path("/home/tito/.openclaw/scripts/nomina_generar_semana.py")
BACKUP_BD = Path("/home/tito/.openclaw/scripts/tito_bd_backup.py")
LOG_DIR = Path("/home/tito/.openclaw/logs")
NOMINA_DIR = Path("/home/tito/.openclaw/data/nomina")
OAUTH_TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")

DRIVE_FOLDER_NOMINAS = "1qBpjmHZr_-F-bBo793J_7I6Q1yPWEHnU"
MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

MAX_REINTENTOS = 3
ESPERA_ENTRE_REINTENTOS_SEG = 30 * 60


def semana_pasada():
    hoy = date.today()
    lunes_esta = hoy - timedelta(days=hoy.weekday())
    lunes_pasada = lunes_esta - timedelta(days=7)
    domingo_pasada = lunes_pasada + timedelta(days=6)
    _, isoweek, _ = lunes_pasada.isocalendar()
    return isoweek, lunes_pasada, domingo_pasada


def sh(cmd, timeout, log):
    log(f"$ {' '.join(str(c) for c in cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.stdout: log(r.stdout.rstrip()[:2000])
        if r.stderr: log(f"stderr: {r.stderr.rstrip()[:500]}")
        return r.returncode == 0, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT tras {timeout}s")
        return False, "", "timeout"


def descargar_sesame(sem, desde, hasta, log):
    cmd = ["node", str(SESAME_SCRIPT),
           "--from", desde.isoformat(),
           "--to", hasta.isoformat(),
           "--sem", str(sem)]
    ok, _, _ = sh(cmd, timeout=600, log=log)
    out = NOMINA_DIR / f"sesame_export_sem{sem}.xlsx"
    return ok and out.exists(), out


def generar_nomina(sem, desde, hasta, sesame_path, log):
    output = Path(f"/tmp/nomina_sem{sem}_tito.xlsx")
    cmd = ["python3", str(GENERADOR),
           "--sem", str(sem),
           "--from", desde.isoformat(),
           "--to", hasta.isoformat(),
           "--sesame", str(sesame_path),
           "--output", str(output)]
    ok, stdout, _ = sh(cmd, timeout=300, log=log)
    resumen = None
    if ok:
        try:
            resumen = json.loads(stdout.split("\n{")[-1] if "{" not in stdout[:100] else stdout[stdout.index("{"):])
        except Exception:
            resumen = None
    return ok and output.exists(), output, resumen


def subir_drive(xlsx_path, sem, desde, hasta, log):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    td = json.loads(OAUTH_TOKENS.read_text())
    creds = Credentials(**td)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    drv = build("drive", "v3", credentials=creds)

    # Nombre: "Nómina - Semana XX (D al D mes YYYY)"
    if desde.month == hasta.month:
        rango = f"{desde.day} al {hasta.day} {MESES_ES[desde.month-1]} {desde.year}"
    else:
        rango = f"{desde.day} {MESES_ES[desde.month-1]} al {hasta.day} {MESES_ES[hasta.month-1]} {hasta.year}"
    nombre = f"Nómina - Semana {sem} ({rango})"

    media = MediaFileUpload(str(xlsx_path),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=False)

    r = drv.files().list(
        q=f"name = '{nombre}' and '{DRIVE_FOLDER_NOMINAS}' in parents and trashed = false",
        fields="files(id,name)"
    ).execute()
    existing = r.get("files", [])
    if existing:
        fid = existing[0]["id"]
        r = drv.files().update(fileId=fid, media_body=media, fields="id,webViewLink").execute()
        log(f"Drive UPDATED: {nombre}")
    else:
        meta = {"name": nombre, "parents": [DRIVE_FOLDER_NOMINAS],
                "mimeType": "application/vnd.google-apps.spreadsheet"}
        r = drv.files().create(body=meta, media_body=media,
                                fields="id,webViewLink").execute()
        log(f"Drive CREATED: {nombre}")
    return r["id"], r["webViewLink"]


def correr_backup(log):
    ok, _, _ = sh(["python3", str(BACKUP_BD)], timeout=300, log=log)
    return ok


def enviar_wa(msg, log):
    log(f"→ WA a {STAFF_WA}")
    subprocess.run([
        "openclaw", "message", "send",
        "--channel", "whatsapp",
        "--target", STAFF_WA,
        "--message", msg,
    ], check=False)


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"nomina_lunes_{date.today().isoformat()}.log"
    lf = log_path.open("a")

    def log(msg):
        line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
        lf.write(line + "\n"); lf.flush()
        print(line)

    sem, desde, hasta = semana_pasada()
    log(f"=== Cron nómina lunes — sem {sem} ({desde} a {hasta}) ===")

    # 1) SESAME con reintentos
    ok = False
    for intento in range(1, MAX_REINTENTOS + 1):
        log(f"SESAME intento {intento}/{MAX_REINTENTOS}")
        ok, sesame_path = descargar_sesame(sem, desde, hasta, log)
        if ok:
            log(f"SESAME OK: {sesame_path}")
            break
        log(f"SESAME falló en intento {intento}")
        if intento < MAX_REINTENTOS:
            log(f"Esperando {ESPERA_ENTRE_REINTENTOS_SEG // 60} min...")
            time.sleep(ESPERA_ENTRE_REINTENTOS_SEG)

    if not ok:
        enviar_wa(
            f"⚠️ Rafael, no pude descargar SESAME sem {sem} "
            f"({desde.strftime('%d/%m')}-{hasta.strftime('%d/%m')}) "
            f"después de {MAX_REINTENTOS} intentos. Revísalo.\nLog: {log_path}",
            log,
        )
        lf.close(); sys.exit(1)

    # 2) Generar nómina completa
    log("Generando nómina con formato Andrónica...")
    ok_gen, xlsx_path, resumen = generar_nomina(sem, desde, hasta, sesame_path, log)
    if not ok_gen:
        enviar_wa(
            f"⚠️ Rafael, SESAME sí bajó pero el generador falló para sem {sem}. "
            f"Revíselo. Log: {log_path}",
            log,
        )
        lf.close(); sys.exit(1)

    # 3) Subir a Drive
    try:
        sheet_id, sheet_link = subir_drive(xlsx_path, sem, desde, hasta, log)
    except Exception as e:
        log(f"ERROR subida Drive: {e}")
        sheet_link = "(subida a Drive falló, xlsx local en " + str(xlsx_path) + ")"

    # 3.5) Flaguear asistencia (verde / NO CHECO) — SIEMPRE, con dedup de duplicados.
    # Desde la sem 30 ya no hay horario s{N}_*.json (SESAME es la fuente): si hay horario,
    # se usa el flagueo por horario; si no, cae al flagueo SESAME-only (descanso por patrón).
    import glob as _glob
    flag_ok = False
    hay_horario = bool(_glob.glob(f"/home/tito/.openclaw/data/nomina/horarios/s{sem}_*.json"))
    flagger = "nomina_flaguear.py" if hay_horario else "nomina_flaguear_sesame.py"
    flag_args = (["--semana", str(sem)] if hay_horario else ["--sem", str(sem)])
    try:
        fr = subprocess.run(
            ["python3", f"/home/tito/.openclaw/scripts/{flagger}"] + flag_args,
            capture_output=True, text=True, timeout=180)
        flag_ok = fr.returncode == 0
        # si el de horario falla, intentar el SESAME-only como respaldo
        if not flag_ok and hay_horario:
            fr = subprocess.run(
                ["python3", "/home/tito/.openclaw/scripts/nomina_flaguear_sesame.py", "--sem", str(sem)],
                capture_output=True, text=True, timeout=180)
            flag_ok = fr.returncode == 0
        log(f"Flagueo asistencia ({flagger}): " + ("OK" if flag_ok else f"falló rc={fr.returncode} {fr.stderr[-200:]}"))
    except Exception as e:
        log(f"[warn] flagueo falló: {e}")

    # 4) Backup BD
    log("Corriendo backup BD...")
    ok_bk = correr_backup(log)
    log(f"Backup BD: {'OK' if ok_bk else 'falla'}")

    # 5) WA con link directo al Sheet
    matched = (resumen or {}).get("sesame_matched", "?")
    total = (resumen or {}).get("empleados", "?")
    msg = (
        f"Buenas Rafael. Nómina semana {sem} lista "
        f"({desde.strftime('%d/%m')} al {hasta.strftime('%d/%m')}).\n\n"
        f"✅ SESAME descargado y cruzado ({matched}/{total} empleados).\n"
        f"✅ Formato Andrónica aplicado.\n"
        f"{'✅' if flag_ok else '⚠️'} Asistencia flageada (verde / no checó).\n"
        f"{'✅' if ok_bk else '⚠️'} Backup BD en Drive.\n\n"
        f"Sheet: {sheet_link}"
    )
    enviar_wa(msg, log)
    log("=== Fin ===")
    lf.close()


if __name__ == "__main__":
    main()
