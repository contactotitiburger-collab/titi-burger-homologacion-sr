#!/usr/bin/env python3
"""Servidor estatico con seguridad ligera: usuario/clave + bloqueo por fuerza bruta.
Las credenciales viven FUERA del repo (no se suben a GitHub):
/home/tito/.openclaw/credentials/avance_lector/usuarios.json
Sirve /home/tito/.openclaw/workspace/tito-lector/avance en el puerto 8100.

Nota de seguridad (auditoria 25-nov-2026): la IP real del visitante viene en el
header CF-Connecting-IP que inyecta el tunel de Cloudflare -- self.client_address
siempre es la IP local del tunel, usarla para el bloqueo bloquearia a todos por
el intento fallido de una sola persona."""
import base64, hmac, http.server, json, os, time
from pathlib import Path
from collections import defaultdict

CREDS_FILE = Path("/home/tito/.openclaw/credentials/avance_lector/usuarios.json")
DIRECTORIO = "/home/tito/.openclaw/workspace/tito-lector/avance"
PUERTO = 8100
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 15 * 60

USUARIOS = json.loads(CREDS_FILE.read_text())
VALIDOS = [base64.b64encode(f"{u}:{p}".encode()).decode() for u, p in USUARIOS.items()]

intentos_fallidos = defaultdict(list)  # ip -> [timestamps]
bloqueados_hasta = {}  # ip -> timestamp

def credencial_valida(valor):
    # hmac.compare_digest por cada credencial -> sin fuga de timing por posicion
    return any(hmac.compare_digest(valor, v) for v in VALIDOS)

class Handler(http.server.SimpleHTTPRequestHandler):
    timeout = 10  # mitiga slow-loris (auditoria 25-nov)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORIO, **kwargs)

    def ip_real(self):
        return self.headers.get("CF-Connecting-IP") or self.client_address[0]

    def do_GET(self):
        ip = self.ip_real()
        ahora = time.time()

        if ip in bloqueados_hasta:
            if ahora < bloqueados_hasta[ip]:
                self.send_response(429)
                self.send_header("Retry-After", str(int(bloqueados_hasta[ip] - ahora)))
                self.end_headers()
                self.wfile.write(b"Demasiados intentos. Espera unos minutos.")
                return
            del bloqueados_hasta[ip]
            intentos_fallidos.pop(ip, None)

        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic ") or not credencial_valida(auth[6:]):
            intentos_fallidos[ip] = [t for t in intentos_fallidos[ip] if ahora - t < BLOQUEO_SEGUNDOS]
            intentos_fallidos[ip].append(ahora)
            if len(intentos_fallidos[ip]) >= MAX_INTENTOS:
                bloqueados_hasta[ip] = ahora + BLOQUEO_SEGUNDOS
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Titi Lector"')
            self.end_headers()
            self.wfile.write(b"Acceso restringido.")
            return

        intentos_fallidos.pop(ip, None)
        super().do_GET()

    def log_message(self, fmt, *args):
        pass  # silencioso

if __name__ == "__main__":
    os.chdir(DIRECTORIO)
    with http.server.ThreadingHTTPServer(("100.64.29.43", PUERTO), Handler) as httpd:
        httpd.serve_forever()
