#!/usr/bin/env python3
"""
tito_bd_backup.py — backup diario de la BD de nómina.

- Copia   ~/.openclaw/data/nomina/nomina.db -> ~/.openclaw/backups/nomina_YYYY-MM-DD.db.gz
- Sube    la copia comprimida al Drive del usuario (OAuth) en
          "Titi Burger/Nomina/Backups/"
- Mantiene solo los últimos 30 backups locales (borra los viejos).
"""

import gzip
import io
import json
import os
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from openpyxl import Workbook

DB_PATH = Path("/home/tito/.openclaw/data/nomina/nomina.db")
BACKUP_DIR = Path("/home/tito/.openclaw/backups")
TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
MAX_BACKUPS_LOCAL = 30
DRIVE_PATH = ["Titi Burger", "Nómina", "Historial y Copias"]


def _creds():
    with open(TOKENS) as f:
        td = json.load(f)
    c = Credentials(**td)
    if not c.valid and c.refresh_token:
        c.refresh(Request())
    return c


def _ensure_drive_folder(drv, path_parts):
    """Crea (si no existe) la cadena de carpetas y devuelve el id de la última."""
    parent = "root"
    for name in path_parts:
        q = (f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
             f"and '{parent}' in parents and trashed = false")
        r = drv.files().list(q=q, fields="files(id,name)", spaces="drive").execute()
        files = r.get("files", [])
        if files:
            parent = files[0]["id"]
        else:
            meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]}
            fld = drv.files().create(body=meta, fields="id").execute()
            parent = fld["id"]
    return parent


def hacer_backup_local():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        print(f"ERROR: no existe la BD en {DB_PATH}", file=sys.stderr)
        return None

    fecha = date.today().isoformat()
    out = BACKUP_DIR / f"nomina_{fecha}.db.gz"

    # Copia consistente: usar sqlite3 backup API sería lo ideal;
    # como es un archivo simple sin conexiones activas garantizadas,
    # abrimos con VACUUM INTO para snapshot atómico.
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    src = sqlite3.connect(str(DB_PATH))
    src.execute(f"VACUUM INTO '{tmp.name}'")
    src.close()

    with open(tmp.name, "rb") as fin, gzip.open(out, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    os.unlink(tmp.name)

    print(f"OK backup local: {out}  ({out.stat().st_size} bytes)")
    return out


def hacer_backup_xlsx():
    """Exporta la BD entera a un Excel legible (una pestaña por tabla)."""
    fecha = date.today().isoformat()
    out = BACKUP_DIR / f"nomina_{fecha}.xlsx"
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tablas = [r[0] for r in cur.fetchall()]

    wb = Workbook()
    wb.remove(wb.active)  # quitar hoja default
    for t in tablas:
        ws = wb.create_sheet(title=t[:31])  # límite Excel
        cur.execute(f"SELECT * FROM {t}")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        ws.append(cols)
        for r in rows:
            ws.append([r[c] for c in cols])
    conn.close()
    wb.save(str(out))
    print(f"OK backup xlsx: {out}  ({out.stat().st_size} bytes, {len(tablas)} tablas)")
    return out


def limpiar_viejos():
    for patron in ("nomina_*.db.gz", "nomina_*.xlsx"):
        ficheros = sorted(BACKUP_DIR.glob(patron))
        if len(ficheros) > MAX_BACKUPS_LOCAL:
            for f in ficheros[:-MAX_BACKUPS_LOCAL]:
                f.unlink()
                print(f"  borrado: {f.name}")


def subir_a_drive(local_file: Path):
    creds = _creds()
    drv = build("drive", "v3", credentials=creds)
    folder_id = _ensure_drive_folder(drv, DRIVE_PATH)
    with open(local_file, "rb") as fh:
        data = io.BytesIO(fh.read())
    if local_file.suffix == ".gz":
        mime = "application/gzip"
    elif local_file.suffix == ".xlsx":
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        mime = "application/octet-stream"
    media = MediaIoBaseUpload(data, mimetype=mime, resumable=False)
    # Si ya existe un archivo con ese nombre en la carpeta, hacer update en vez de create
    existing = drv.files().list(
        q=f"name = '{local_file.name}' and '{folder_id}' in parents and trashed = false",
        fields="files(id,name)"
    ).execute().get("files", [])
    if existing:
        fid = existing[0]["id"]
        r = drv.files().update(fileId=fid, media_body=media, fields="id,name").execute()
        print(f"OK Drive (updated): {r.get('name')}  id={r.get('id')}")
    else:
        meta = {"name": local_file.name, "parents": [folder_id]}
        r = drv.files().create(body=meta, media_body=media, fields="id,name,webViewLink").execute()
        print(f"OK Drive (created): {r.get('name')}  id={r.get('id')}")
    return r


def main():
    out_gz = hacer_backup_local()
    if not out_gz:
        sys.exit(1)
    out_xlsx = hacer_backup_xlsx()
    for f in (out_gz, out_xlsx):
        try:
            subir_a_drive(f)
        except Exception as e:
            print(f"WARN Drive ({f.name}): {e}", file=sys.stderr)
    limpiar_viejos()


if __name__ == "__main__":
    main()
