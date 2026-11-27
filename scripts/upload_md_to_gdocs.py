#!/usr/bin/env python3
"""Sube un archivo .md como Google Doc, preservando formato vía conversión HTML.

Uso:
    upload_md_to_gdocs.py <ruta_md> <email_a_compartir> [titulo_doc]

Crea el doc bajo el Service Account y lo comparte como editor con el email.
El doc aparece en "Compartidos conmigo" de ese usuario.
"""

import sys
import io
from pathlib import Path
from markdown_it import MarkdownIt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SA_PATH = "/home/tito/.openclaw/credentials/google/service-account.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

# CSS mínimo para tablas — Drive lo respeta al convertir HTML a Doc.
CSS_INLINE = """
<style>
  body { font-family: Arial, sans-serif; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th, td { border: 1px solid #999; padding: 6px 10px; text-align: left; vertical-align: top; }
  th { background: #f0f0f0; }
  pre, code { font-family: 'Courier New', monospace; background: #f6f6f6; padding: 8px; }
  blockquote { border-left: 3px solid #ccc; padding-left: 12px; color: #555; }
</style>
"""


def md_to_html(md_text: str) -> str:
    """Convierte markdown a HTML preservando tablas, headings, listas."""
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    md.enable("table")
    md.enable("strikethrough")
    body = md.render(md_text)
    return f"<html><head>{CSS_INLINE}</head><body>{body}</body></html>"


def upload_as_gdoc(html: str, title: str) -> str:
    """Sube HTML como Google Doc. Devuelve file_id del doc creado."""
    creds = service_account.Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)

    media = MediaIoBaseUpload(
        io.BytesIO(html.encode("utf-8")),
        mimetype="text/html",
        resumable=False,
    )
    file = drive.files().create(
        body={
            "name": title,
            "mimeType": "application/vnd.google-apps.document",
        },
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=False,
    ).execute()
    return file["id"], file["webViewLink"]


def share_with(file_id: str, email: str, role: str = "writer") -> None:
    """Comparte el doc con un email con el rol indicado (writer / reader / commenter)."""
    creds = service_account.Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)
    drive.permissions().create(
        fileId=file_id,
        body={
            "type": "user",
            "role": role,
            "emailAddress": email,
        },
        sendNotificationEmail=False,
        fields="id",
    ).execute()


def main():
    if len(sys.argv) < 3:
        print("Uso: upload_md_to_gdocs.py <ruta_md> <email_a_compartir> [titulo_doc]", file=sys.stderr)
        sys.exit(2)

    md_path = Path(sys.argv[1]).expanduser().resolve()
    email = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else md_path.stem

    if not md_path.is_file():
        print(f"No se encontró el archivo: {md_path}", file=sys.stderr)
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")
    html = md_to_html(md_text)

    file_id, link = upload_as_gdoc(html, title)
    share_with(file_id, email, role="writer")

    print(f"OK")
    print(f"Doc creado: {title}")
    print(f"ID: {file_id}")
    print(f"Link: {link}")
    print(f"Compartido como editor con: {email}")
    print(f"Aparece en 'Compartidos conmigo' del usuario.")


if __name__ == "__main__":
    main()
