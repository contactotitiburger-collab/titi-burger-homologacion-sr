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
import threading
SES_FILE = CREDS_FILE.parent / "sesiones.json"     # sesiones guardadas: reiniciar el servicio ya no saca a nadie
LECTOR = Path(DIRECTORIO).parent
PREG_FILE = LECTOR / "preguntas_felix.json"
RESP_FILE = LECTOR / "respuestas_felix.json"
REP_FILE = LECTOR / "reportes.json"
FORO_FILE = LECTOR / "foro.json"
VIS_FILE = LECTOR / "visitas.json"   # ultima y anterior visita de cada persona (para "Lo nuevo desde tu ultima visita")
ADJ_DIR = LECTOR / "foro_archivos"; ADJ_DIR.mkdir(exist_ok=True)   # fotos, audios y archivos del chat
MAX_ADJ = 25 * 1024 * 1024
import re as _re, subprocess as _sp, urllib.parse as _up, mimetypes as _mt
EXT_OK = {".jpg",".jpeg",".png",".gif",".webp",".heic",".mp3",".m4a",".aac",".ogg",".oga",".opus",".wav",".webm",".mp4",".mov",".3gp",
          ".pdf",".xlsx",".xls",".csv",".docx",".doc",".pptx",".txt",".zip"}
def _kind(ext, ctype):
    if ext in (".jpg",".jpeg",".png",".gif",".webp",".heic"): return "imagen"
    if ext in (".mp3",".m4a",".aac",".ogg",".oga",".opus",".wav") or (ext == ".webm" and ctype.startswith("audio")): return "audio"
    if ext in (".mp4",".mov",".3gp",".webm"): return "video"
    return "archivo"
def _meta(aid):
    try: return json.loads((ADJ_DIR / f"{aid}.json").read_text(encoding="utf-8"))
    except Exception: return None
def _transcribir(aid, ruta):
    """Audio -> texto con whisper.cpp (offline, gratis). Corre en un hilo aparte."""
    wav = ADJ_DIR / f"{aid}_16k.wav"; voz = Path("/home/tito/.openclaw/voz/whisper.cpp")
    try:
        _sp.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ruta), "-ar", "16000", "-ac", "1", str(wav)], timeout=180, check=True)
        r = _sp.run([str(voz / "build/bin/whisper-cli"), "-m", str(voz / "models/ggml-small.bin"), "-l", "es", "-nt", "-np", "-f", str(wav)], capture_output=True, text=True, timeout=600)
        txt = " ".join(x.strip() for x in r.stdout.splitlines() if x.strip())
    except Exception as e:
        txt = ""
    finally:
        wav.unlink(missing_ok=True)
    with LOCK:
        m = _meta(aid) or {}; m["transcripcion"] = txt or "(no se pudo transcribir)"
        (ADJ_DIR / f"{aid}.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
def _miniatura(aid, ruta):
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(ruta)); im.thumbnail((1280, 1280)); im.convert("RGB").save(ADJ_DIR / f"{aid}_t.jpg", "JPEG", quality=82)
    except Exception:
        pass   # preguntas y respuestas (foro); Tito contesta con responder_foro.py
REPEST_FILE = LECTOR / "reportes_estado.json"   # aprobaciones y comentarios de cada reporte       # bitacora: cada respuesta se agrega, la ultima por pregunta gana
LOCK = threading.Lock()
try:
    SESIONES = {k: tuple(v) for k, v in json.loads(SES_FILE.read_text()).items()}
except Exception:
    SESIONES = {}
intentos = defaultdict(list)
bloqueado = {}

def _guardar_ses():
    tmp = SES_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(SESIONES)); os.chmod(tmp, 0o600); tmp.replace(SES_FILE)
def nueva_sesion(usuario):
    t = secrets.token_urlsafe(24)
    with LOCK:
        SESIONES[t] = (time.time()+SESION_DURACION, usuario); _guardar_ses()
    return t
def sesion_usuario(tok):
    v = SESIONES.get(tok)
    if v and v[0] > time.time(): return v[1]
    if v: SESIONES.pop(tok, None)
    return None
def sesion_ok(tok): return sesion_usuario(tok) is not None

def leer_respuestas():
    try: return json.loads(RESP_FILE.read_text(encoding="utf-8"))
    except Exception: return []

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
    def json_resp(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        yo = sesion_usuario(self.token())
        if self.path.split("?")[0] == "/api/preguntas":
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            preg = json.loads(PREG_FILE.read_text(encoding="utf-8"))
            ult = {}
            for r in leer_respuestas(): ult[r["id"]] = r
            return self.json_resp({"yo": yo, "preguntas": preg, "respuestas": ult})
        if self.path.split("?")[0] == "/api/yo":
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            try: vis = json.loads(VIS_FILE.read_text(encoding="utf-8"))
            except Exception: vis = {}
            v = vis.get(yo, {})
            return self.json_resp({"yo": yo, "anterior": v.get("anterior", 0)})
        if self.path.split("?")[0] == "/api/foro":
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            try: foro = json.loads(FORO_FILE.read_text(encoding="utf-8"))
            except Exception: foro = []
            for h in foro:
                for a in h.get("adjuntos", []) + [a for r in h["respuestas"] for a in r.get("adjuntos", [])]:
                    m = _meta(a["id"]) or {}
                    if m.get("transcripcion"): a["transcripcion"] = m["transcripcion"]
            return self.json_resp({"yo": yo, "hilos": foro})
        if self.path.startswith("/api/archivo/"):
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            aid = self.path.split("/api/archivo/")[1].split("?")[0]
            if not _re.fullmatch(r"[0-9a-f]{16}", aid): return self.json_resp({"error": "no existe"}, 404)
            m = _meta(aid)
            if not m: return self.json_resp({"error": "no existe"}, 404)
            mini = "t=1" in self.path and (ADJ_DIR / f"{aid}_t.jpg").exists()
            ruta = ADJ_DIR / (f"{aid}_t.jpg" if mini else aid + m["ext"])
            ctype = "image/jpeg" if mini else (_mt.guess_type("x" + m["ext"])[0] or "application/octet-stream")
            if m["ext"] == ".webm": ctype = "audio/webm" if m["kind"] == "audio" else "video/webm"
            inline = m["kind"] in ("imagen", "audio", "video") or m["ext"] == ".pdf"
            data = ruta.read_bytes(); total = len(data); ini, fin, code = 0, total - 1, 200
            rng = self.headers.get("Range", "")
            mm = _re.match(r"bytes=(\d*)-(\d*)", rng)
            if mm and total:
                if mm.group(1): ini = int(mm.group(1)); fin = int(mm.group(2)) if mm.group(2) else total - 1
                elif mm.group(2): ini = max(0, total - int(mm.group(2)))
                fin = min(fin, total - 1); code = 206
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "sandbox")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "private, max-age=86400")
            self.send_header("Content-Disposition", ("inline" if inline else "attachment") + "; filename*=UTF-8''" + _up.quote(m["nombre"]))
            if code == 206: self.send_header("Content-Range", f"bytes {ini}-{fin}/{total}")
            self.send_header("Content-Length", str(fin - ini + 1)); self.end_headers()
            self.wfile.write(data[ini:fin + 1]); return
        if self.path.split("?")[0] == "/api/reportes":
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            try: est = json.loads(REPEST_FILE.read_text(encoding="utf-8"))
            except Exception: est = {}
            return self.json_resp({"yo": yo, "estado": est})
        if yo and (self.path.split("?")[0].endswith("/") or self.path.split("?")[0].endswith("index.html")):
            ahora = time.time()
            with LOCK:
                try: vis = json.loads(VIS_FILE.read_text(encoding="utf-8"))
                except Exception: vis = {}
                v = vis.setdefault(yo, {})
                if ahora - v.get("ultima", 0) > 1800: v["anterior"] = v.get("ultima", 0)   # visita nueva si pasaron 30 min
                v["ultima"] = ahora
                VIS_FILE.write_text(json.dumps(vis), encoding="utf-8")
        if yo: return super().do_GET()
        self.pagina_login()
    def do_POST(self):
        if self.path.split("?")[0] == "/api/responder":
            yo = sesion_usuario(self.token())
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            if yo not in ("felix", "rafael", "tito"): return self.json_resp({"error": "esta persona no contesta estas preguntas"}, 403)
            ln = int(self.headers.get("Content-Length", "0") or 0)
            if ln > 20000: return self.json_resp({"error": "muy largo"}, 413)
            try: d = json.loads(self.rfile.read(ln).decode("utf-8"))
            except Exception: return self.json_resp({"error": "datos mal formados"}, 400)
            preg = {q["id"]: q for q in json.loads(PREG_FILE.read_text(encoding="utf-8"))}
            q = preg.get(d.get("id")); r = d.get("respuesta")
            if not q: return self.json_resp({"error": "pregunta no existe"}, 400)
            if q["tipo"] == "opcion" and r not in q["opciones"]: return self.json_resp({"error": "opcion no valida"}, 400)
            if q["tipo"] == "campos":
                nombres = [c if isinstance(c, str) else c["nombre"] for c in q["campos"]]
                if isinstance(r, str) and r in q.get("atajos", []): pass
                elif not isinstance(r, dict): return self.json_resp({"error": "datos mal formados"}, 400)
                else: r = {k: str(r.get(k, ""))[:200].strip() for k in nombres}
            if q["tipo"] == "texto": r = str(r or "")[:2000].strip()
            reg = {"id": q["id"], "respuesta": r, "usuario": yo, "fecha": time.strftime("%Y-%m-%d %H:%M")}
            with LOCK:
                todas = leer_respuestas(); todas.append(reg)
                tmp = RESP_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(todas, ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(RESP_FILE)
            return self.json_resp({"ok": True, "registro": reg})
        if self.path.split("?")[0] == "/api/subir":
            yo = sesion_usuario(self.token())
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            ln = int(self.headers.get("Content-Length", "0") or 0)
            if ln <= 0 or ln > MAX_ADJ: return self.json_resp({"error": "el archivo pesa más de 25 MB"}, 413)
            nombre = _up.unquote(self.headers.get("X-Nombre", "archivo"))[:120] or "archivo"
            nombre = _re.sub(r"[\\/\x00-\x1f]", "_", nombre)
            ext = Path(nombre).suffix.lower(); ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ext not in EXT_OK: return self.json_resp({"error": "ese tipo de archivo no se acepta"}, 400)
            aid = secrets.token_hex(8); ruta = ADJ_DIR / (aid + ext)
            restante = ln
            with open(ruta, "wb") as fh:
                while restante > 0:
                    trozo = self.rfile.read(min(65536, restante))
                    if not trozo: break
                    fh.write(trozo); restante -= len(trozo)
            kind = _kind(ext, ctype)
            if kind == "video":   # el celular marca .webm/.mp4 como video aunque sea solo audio: se revisa con ffprobe
                try:
                    pr = _sp.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(ruta)], capture_output=True, text=True, timeout=30)
                    if "video" not in pr.stdout: kind = "audio"
                except Exception: pass
            m = {"id": aid, "nombre": nombre, "ext": ext, "kind": kind, "tam": ruta.stat().st_size, "usuario": yo, "fecha": time.strftime("%Y-%m-%d %H:%M")}
            (ADJ_DIR / f"{aid}.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            if kind == "audio": threading.Thread(target=_transcribir, args=(aid, ruta), daemon=True).start()
            if kind == "imagen": threading.Thread(target=_miniatura, args=(aid, ruta), daemon=True).start()
            return self.json_resp({"ok": True, "adjunto": {"id": aid, "nombre": nombre, "kind": kind, "tam": m["tam"]}})
        if self.path.split("?")[0] == "/api/foro":
            yo = sesion_usuario(self.token())
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            ln = int(self.headers.get("Content-Length", "0") or 0)
            if ln > 20000: return self.json_resp({"error": "muy largo"}, 413)
            try: d = json.loads(self.rfile.read(ln).decode("utf-8"))
            except Exception: return self.json_resp({"error": "datos mal formados"}, 400)
            txt = str(d.get("texto") or "")[:3000].strip()
            adj = []
            for aid in (d.get("adjuntos") or [])[:10]:
                m = _meta(str(aid)) if _re.fullmatch(r"[0-9a-f]{16}", str(aid)) else None
                if m and m["usuario"] == yo: adj.append({"id": m["id"], "nombre": m["nombre"], "kind": m["kind"], "tam": m["tam"]})
            if not txt and not adj: return self.json_resp({"error": "escribe tu pregunta o agrega un archivo"}, 400)
            ahora = time.strftime("%Y-%m-%d %H:%M")
            with LOCK:
                try: foro = json.loads(FORO_FILE.read_text(encoding="utf-8"))
                except Exception: foro = []
                if d.get("accion") == "responder":
                    h = next((x for x in foro if x["id"] == d.get("id")), None)
                    if not h: return self.json_resp({"error": "esa pregunta no existe"}, 400)
                    h["respuestas"].append({"usuario": yo, "fecha": ahora, "texto": txt, "adjuntos": adj})
                else:
                    nid = max([x["id"] for x in foro] + [0]) + 1
                    foro.append({"id": nid, "usuario": yo, "fecha": ahora, "texto": txt, "adjuntos": adj, "respuestas": []})
                tmp = FORO_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(foro, ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(FORO_FILE)
            return self.json_resp({"ok": True})
        if self.path.split("?")[0] == "/api/reporte":
            yo = sesion_usuario(self.token())
            if not yo: return self.json_resp({"error": "sin sesion"}, 401)
            ln = int(self.headers.get("Content-Length", "0") or 0)
            if ln > 20000: return self.json_resp({"error": "muy largo"}, 413)
            try: d = json.loads(self.rfile.read(ln).decode("utf-8"))
            except Exception: return self.json_resp({"error": "datos mal formados"}, 400)
            ids = {r["id"] for r in json.loads(REP_FILE.read_text(encoding="utf-8"))}
            rid = d.get("id"); acc = d.get("accion"); txt = str(d.get("texto") or "")[:3000].strip()
            if rid not in ids or acc not in ("aprobar", "comentar"): return self.json_resp({"error": "reporte o accion no valida"}, 400)
            if acc == "aprobar" and yo not in ("rafael", "felix", "dontiti"): return self.json_resp({"error": "esta persona no aprueba reportes"}, 403)
            if acc == "comentar" and not txt: return self.json_resp({"error": "comentario vacio"}, 400)
            ahora = time.strftime("%Y-%m-%d %H:%M")
            with LOCK:
                try: est = json.loads(REPEST_FILE.read_text(encoding="utf-8"))
                except Exception: est = {}
                e = est.setdefault(rid, {"aprobado": [], "comentarios": []})
                if acc == "aprobar" and not any(a["usuario"] == yo for a in e["aprobado"]):
                    e["aprobado"].append({"usuario": yo, "fecha": ahora})
                if txt: e["comentarios"].append({"usuario": yo, "fecha": ahora, "texto": txt})
                tmp = REPEST_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(REPEST_FILE)
            return self.json_resp({"ok": True})
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
            usuario = next((u for u, k in USUARIOS.items() if k == clave), "desconocido")
            tok=nueva_sesion(usuario)
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
