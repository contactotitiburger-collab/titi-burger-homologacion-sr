#!/usr/bin/env python3
"""Helper de Drive/Sheets para Tito (OAuth tito_tokens). Reusable.

Uso:
  tito_drive.py ls <folder_id>                 lista hijos de un folder
  tito_drive.py find <nombre>                  busca por nombre (contains)
  tito_drive.py tree <folder_id> [prof]        árbol
  tito_drive.py mkfolder <nombre> <parent_id>  crea folder, imprime id
  tito_drive.py mksheet <nombre> <parent_id>   crea Google Sheet vacío, imprime id
  tito_drive.py upload <archivo> <parent_id> [nombre]  sube archivo local, imprime id
"""
import sys, json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKENS_PATH = Path.home() / ".openclaw/credentials/google/oauth/tito_tokens.json"

def _svc(kind="drive"):
    t = json.loads(TOKENS_PATH.read_text())
    creds = Credentials(
        token=t["token"], refresh_token=t["refresh_token"],
        token_uri=t["token_uri"], client_id=t["client_id"],
        client_secret=t["client_secret"], scopes=t["scopes"])
    if not creds.valid:
        creds.refresh(Request())
        t["token"] = creds.token
        TOKENS_PATH.write_text(json.dumps(t, indent=2))
    if kind == "sheets":
        return build("sheets", "v4", credentials=creds)
    return build("drive", "v3", credentials=creds)

def ls(folder_id):
    d = _svc()
    q = f"'{folder_id}' in parents and trashed=false"
    res = d.files().list(q=q, fields="files(id,name,mimeType,modifiedTime)",
                         orderBy="name", pageSize=1000).execute()
    for f in res.get("files", []):
        tipo = "DIR " if f["mimeType"].endswith("folder") else "file"
        print(f"{tipo}  {f['id']}  {f['name']}")

def find(nombre):
    d = _svc()
    q = f"name contains '{nombre}' and trashed=false"
    res = d.files().list(q=q, fields="files(id,name,mimeType,parents)",
                         pageSize=100).execute()
    for f in res.get("files", []):
        tipo = "DIR " if f["mimeType"].endswith("folder") else "file"
        print(f"{tipo}  {f['id']}  {f['name']}  parents={f.get('parents')}")

def tree(folder_id, prof=3, _ind=0):
    d = _svc()
    q = f"'{folder_id}' in parents and trashed=false"
    res = d.files().list(q=q, fields="files(id,name,mimeType)",
                         orderBy="folder,name", pageSize=1000).execute()
    for f in res.get("files", []):
        es_dir = f["mimeType"].endswith("folder")
        print("  "*_ind + ("📁 " if es_dir else "📄 ") + f["name"] + f"   [{f['id']}]")
        if es_dir and _ind+1 < prof:
            tree(f["id"], prof, _ind+1)

def mkfolder(nombre, parent):
    d = _svc()
    meta = {"name": nombre, "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent]}
    f = d.files().create(body=meta, fields="id").execute()
    print(f["id"])

def mksheet(nombre, parent):
    d = _svc()
    meta = {"name": nombre, "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [parent]}
    f = d.files().create(body=meta, fields="id").execute()
    print(f["id"])

def upload(archivo, parent, nombre=None):
    d = _svc()
    archivo = Path(archivo)
    nombre = nombre or archivo.name
    mime = mimetypes.guess_type(str(archivo))[0] or "application/octet-stream"
    media = MediaFileUpload(str(archivo), mimetype=mime, resumable=True)
    meta = {"name": nombre, "parents": [parent]}
    f = d.files().create(body=meta, media_body=media, fields="id").execute()
    print(f["id"])

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "ls": ls(sys.argv[2])
    elif cmd == "find": find(sys.argv[2])
    elif cmd == "tree": tree(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    elif cmd == "mkfolder": mkfolder(sys.argv[2], sys.argv[3])
    elif cmd == "mksheet": mksheet(sys.argv[2], sys.argv[3])
    elif cmd == "upload": upload(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
