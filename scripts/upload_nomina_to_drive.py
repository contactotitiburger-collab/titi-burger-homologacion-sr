#!/usr/bin/env python3
"""
upload_nomina_to_drive.py — sube un Excel local a Drive convirtiéndolo a Google Sheet.

Uso:
  python3 upload_nomina_to_drive.py \
      --file /tmp/nomina_sem22.xlsx \
      --name "Nómina - Semana 22 (25 al 31 may 2026) - v1" \
      --folder 1qBpjmHZr_-F-bBo793J_7I6Q1yPWEHnU

Emite JSON con {ok, id, name, webViewLink}.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--replace-existing", action="store_true",
                    help="Si ya existe uno con mismo nombre, moverlo a papelera antes.")
    args = ap.parse_args()

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    TOKENS_PATH = Path.home() / ".openclaw/credentials/google/oauth/tito_tokens.json"
    tokens = json.loads(TOKENS_PATH.read_text())
    creds = Credentials(
        token=tokens["token"],
        refresh_token=tokens["refresh_token"],
        token_uri=tokens["token_uri"],
        client_id=tokens["client_id"],
        client_secret=tokens["client_secret"],
        scopes=tokens["scopes"],
    )
    if not creds.valid:
        creds.refresh(Request())
        tokens["token"] = creds.token
        TOKENS_PATH.write_text(json.dumps(tokens, indent=2))

    svc = build("drive", "v3", credentials=creds)

    if args.replace_existing:
        # Buscar por nombre exacto dentro de la carpeta
        q = f"'{args.folder}' in parents and name = '{args.name}' and trashed=false"
        res = svc.files().list(q=q, fields="files(id,name)").execute()
        for f in res.get("files", []):
            try:
                svc.files().update(fileId=f["id"], body={"trashed": True}).execute()
            except HttpError:
                pass

    try:
        media = MediaFileUpload(
            args.file,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resumable=False,
        )
        metadata = {
            "name": args.name,
            "parents": [args.folder],
            "mimeType": "application/vnd.google-apps.spreadsheet",  # convertir a Sheet nativo
        }
        created = svc.files().create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        ).execute()
        print(json.dumps({"ok": True, **created}))
    except HttpError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
