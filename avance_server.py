#!/usr/bin/env python3
"""Servidor estatico con seguridad ligera (usuario/clave, sin base de datos).
Las credenciales viven FUERA del repo (no se suben a GitHub):
/home/tito/.openclaw/credentials/avance_lector/usuarios.json
Sirve /home/tito/.openclaw/workspace/tito-lector/avance en el puerto 8100."""
import base64, http.server, json, os
from pathlib import Path

CREDS_FILE = Path("/home/tito/.openclaw/credentials/avance_lector/usuarios.json")
DIRECTORIO = "/home/tito/.openclaw/workspace/tito-lector/avance"
PUERTO = 8100

USUARIOS = json.loads(CREDS_FILE.read_text())
VALIDOS = {base64.b64encode(f"{u}:{p}".encode()).decode() for u, p in USUARIOS.items()}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORIO, **kwargs)

    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic ") or auth[6:] not in VALIDOS:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Titi Lector"')
            self.end_headers()
            self.wfile.write(b"Acceso restringido.")
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass  # silencioso

if __name__ == "__main__":
    os.chdir(DIRECTORIO)
    with http.server.ThreadingHTTPServer(("100.64.29.43", PUERTO), Handler) as httpd:
        httpd.serve_forever()
