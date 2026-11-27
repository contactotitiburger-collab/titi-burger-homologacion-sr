#!/usr/bin/env python3
"""Avance con LOGIN EN PAGINA (formulario + cookie de sesion), no el popup del navegador.
Asi, al cambiar de app (WhatsApp) y volver, el login SIGUE en pantalla y no se bloquea solo.
El bloqueo (corto, 30s) solo cuenta cuando se envia una clave incorrecta, no al navegar.
Credenciales fuera del repo: credentials/avance_lector/usuarios.json"""
import http.server, json, os, time, secrets, html
from pathlib import Path
from collections import defaultdict
from urllib.parse import parse_qs

CREDS_FILE = Path("/home/tito/.openclaw/credentials/avance_lector/usuarios.json")
DIRECTORIO = "/home/tito/.openclaw/workspace/tito-lector/avance"
PUERTO = 8100
MAX_INTENTOS = 10
BLOQUEO_SEGUNDOS = 30          # bloqueo corto (por ahora)
SESION_DURACION = 30*24*3600   # 30 dias logueado

USUARIOS = json.loads(CREDS_FILE.read_text())
CLAVES = set(USUARIOS.values())    # cualquier clave valida entra (sin pedir usuario)
SESIONES = {}
intentos = defaultdict(list)
bloqueado = {}

def nueva_sesion():
    t = secrets.token_urlsafe(24); SESIONES[t] = time.time()+SESION_DURACION; return t
def sesion_ok(tok):
    exp = SESIONES.get(tok)
    if exp and exp > time.time(): return True
    SESIONES.pop(tok, None); return False

LOGIN = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Titi Burger - Avance</title><style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#FBFAF7;color:#211F1B;padding:20px}
.card{background:#fff;border:1px solid #E7E1D7;border-radius:18px;box-shadow:0 8px 30px rgba(33,31,27,.08);
padding:32px 26px;width:100%;max-width:360px;text-align:center}
.logo{font-size:46px;line-height:1}
h1{font-size:1.35rem;margin:10px 0 2px}
.sub{color:#6E675C;margin:0 0 20px;font-size:.9rem}
label{display:block;text-align:left;font-size:.8rem;font-weight:600;color:#6E675C;margin:0 0 6px}
input{width:100%;padding:14px;font-size:1.05rem;border:1.5px solid #E0D8CC;border-radius:12px;background:#FBFAF7;margin-bottom:14px}
input:focus{outline:none;border-color:#C6341C;background:#fff}
button{width:100%;padding:14px;font-size:1.05rem;font-weight:700;color:#fff;background:#C6341C;border:none;border-radius:12px;cursor:pointer}
button:active{background:#a82c18}
.hint{color:#9a9186;font-size:.8rem;margin:16px 0 0}
.err{background:#FBEDE9;color:#C6341C;border:1px solid #EFC9BF;border-radius:10px;padding:11px;font-size:.9rem;margin:0 0 14px;text-align:left}
</style></head><body><div class="card">
<div class="logo">&#127828;</div>
<h1>Avance del proyecto</h1>
<p class="sub">Titi Burger</p>
__ERROR__
<form method="post" action="/login">
<label>Clave</label>
<input type="password" name="clave" autocomplete="current-password" autofocus placeholder="Escribe o pega tu clave">
<button type="submit">Entrar</button>
</form>
<p class="hint">Puedes pegar la clave que te llego por WhatsApp. Una vez dentro, no te la vuelve a pedir.</p>
</div></body></html>"""

def login_html(error=""):
    err = '<p class="err">'+html.escape(error)+'</p>' if error else ''
    return LOGIN.replace("__ERROR__", err)

class H(http.server.SimpleHTTPRequestHandler):
    timeout = 10
    def __init__(self,*a,**k): super().__init__(*a, directory=DIRECTORIO, **k)
    def ip(self): return self.headers.get("CF-Connecting-IP") or self.client_address[0]
    def token(self):
        for p in self.headers.get("Cookie","").split(";"):
            p=p.strip()
            if p.startswith("sesion="): return p[7:]
        return ""
    def pagina_login(self, code=200, error=""):
        b=login_html(error).encode()
        self.send_response(code)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(b)))
        self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if sesion_ok(self.token()): return super().do_GET()
        self.pagina_login()
    def do_POST(self):
        if self.path.split("?")[0] != "/login":
            self.send_response(404); self.end_headers(); return
        ip=self.ip(); ahora=time.time()
        if ip in bloqueado and ahora < bloqueado[ip]:
            return self.pagina_login(error="Demasiados intentos. Espera %d segundos." % int(bloqueado[ip]-ahora))
        ln=int(self.headers.get("Content-Length","0") or 0)
        datos=parse_qs(self.rfile.read(ln).decode("utf-8","replace")) if ln else {}
        clave=(datos.get("clave",[""])[0]).strip()
        if clave in CLAVES:
            intentos.pop(ip,None); bloqueado.pop(ip,None)
            tok=nueva_sesion()
            self.send_response(303)
            self.send_header("Set-Cookie","sesion=%s; Path=/; HttpOnly; Secure; SameSite=Lax" % (tok,))
            self.send_header("Location","/")
            self.end_headers(); return
        intentos[ip]=[t for t in intentos[ip] if ahora-t<BLOQUEO_SEGUNDOS]
        intentos[ip].append(ahora)
        if len(intentos[ip])>=MAX_INTENTOS: bloqueado[ip]=ahora+BLOQUEO_SEGUNDOS
        self.pagina_login(error="Clave incorrecta. Intentalo de nuevo.")
    def log_message(self,*a): pass

if __name__=="__main__":
    os.chdir(DIRECTORIO)
    with http.server.ThreadingHTTPServer(("100.64.29.43",PUERTO),H) as s: s.serve_forever()
