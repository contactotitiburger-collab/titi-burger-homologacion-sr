#!/usr/bin/env python3
"""
Extiende el OAuth de tito_tokens.json agregando el scope gmail.readonly
a los ya existentes (spreadsheets + drive).

Flujo:
1. Levanta HTTP server local en 127.0.0.1:8899.
2. Imprime la URL de consentimiento y también la deja como .url en el
   Escritorio de Windows para que Rafael la abra desde ahí.
3. Rafael abre el link, elige la cuenta contactotitiburger@gmail.com,
   autoriza, y Google redirige a http://localhost:8899/callback?code=...
4. El server captura el code, hace el token exchange y sobrescribe
   /home/tito/.openclaw/credentials/google/oauth/tito_tokens.json.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google_auth_oauthlib.flow import Flow

CLIENT_SECRET = Path("/home/tito/.openclaw/credentials/google/oauth/client_secret.json")
TOKENS = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
DESKTOP = Path("/mnt/c/Users/Conta/Desktop")

PORT = 8899
REDIRECT_URI = f"http://localhost:{PORT}/callback"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_result = {"code": None, "error": None}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        qs = parse_qs(parsed.query)
        if "code" in qs:
            _result["code"] = qs["code"][0]
            body = (
                "<html><body style='font-family:sans-serif;padding:40px'>"
                "<h1>Listo, Rafael 🎉</h1>"
                "<p>Ya puede cerrar esta ventana. Tito recibió el permiso.</p>"
                "</body></html>"
            ).encode()
        else:
            _result["error"] = qs.get("error", ["sin_code"])[0]
            body = f"<html><body><h1>Error</h1><pre>{_result['error']}</pre></body></html>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_a, **_kw):
        pass


def main():
    flow = Flow.from_client_secrets_file(str(CLIENT_SECRET), scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    # Deja el link como .url en Escritorio de Windows
    DESKTOP.mkdir(parents=True, exist_ok=True)
    url_file = DESKTOP / "Tito - autorizar Gmail.url"
    url_file.write_text(f"[InternetShortcut]\nURL={auth_url}\n", encoding="utf-8")
    print(f".url guardado en: {url_file}")
    print(f"\nURL (respaldo):\n{auth_url}\n")

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Server escuchando en http://localhost:{PORT}/callback")
    print("Esperando a que Rafael autorice (timeout 5 min)...")

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # Espera hasta 5 min
    import time
    for _ in range(300):
        if _result["code"] or _result["error"]:
            break
        time.sleep(1)
    server.shutdown()

    if _result["error"]:
        print(f"❌ Autorización con error: {_result['error']}", file=sys.stderr)
        sys.exit(1)
    if not _result["code"]:
        print("❌ Timeout esperando autorización.", file=sys.stderr)
        sys.exit(1)

    flow.fetch_token(code=_result["code"])
    creds = flow.credentials
    tokens = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }
    # Backup del anterior
    if TOKENS.exists():
        bak = TOKENS.with_suffix(".json.bak-antes-gmail")
        bak.write_bytes(TOKENS.read_bytes())
        print(f"Backup tokens viejos: {bak}")
    TOKENS.write_text(json.dumps(tokens, indent=2))
    print(f"✅ Tokens nuevos guardados en {TOKENS}")
    print(f"   Scopes: {tokens['scopes']}")

    # Borrar .url del Escritorio (ya no sirve)
    try:
        url_file.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    main()
