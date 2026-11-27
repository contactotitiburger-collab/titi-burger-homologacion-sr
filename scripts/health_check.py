#!/usr/bin/env python3
"""Chequeo de salud de Titi Burger (tablero de inventario + lectores).
Corre por el timer systemd titi-salud.timer.

Revisa:
  1) Las 6 carretas + la base de referencia de Felix: que el SQL responda
     (SQL Browser UDP 1434 = la compu prendida y el SQL arriba).
  2) El tablero de inventario (http 8099) responde 200.
  3) La pagina de avance (8100) responde (401 = arriba, pide clave).
  4) Frescura: inv_data.json regenerado hace < 40 min (el timer es de 15 min).

Si algo FALLA, manda UN WhatsApp a Rafael. Anti-spam: solo avisa cuando el
conjunto de fallos CAMBIA (nuevo problema) o cuando todo se RECUPERA.
Si todo esta bien y antes tambien, no manda nada.
"""
import json, socket, subprocess, time, urllib.request
from pathlib import Path

RAFAEL_WA = "+5216861445614"
CREDS = Path("/home/tito/.openclaw/credentials/sr_sql")
INV_DATA = Path("/home/tito/.openclaw/workspace/titi-inventario-demo/inv_data.json")
ESTADO = Path("/home/tito/.openclaw/scripts/.health_state.json")
LOG = Path("/home/tito/.openclaw/logs/health_check.log")

# nombre credencial -> etiqueta legible
SUCURSALES = {
    "montejano": "Montejano",
    "hacienda_del_rio": "Hacienda del Río",
    "montecarlo": "Montecarlo",
    "villas_del_rey": "Villas del Rey",
    "san_marcos": "San Marcos",
    "cine_curto": "Cine Curto",
    "felix": "Base Félix (ref)",
}

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M')} {m}\n")

def sql_vivo(host):
    """True si el SQL Browser (UDP 1434) responde -> compu prendida y SQL arriba."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
    try:
        s.sendto(b"\x02", (host, 1434))
        s.recvfrom(65535)
        return True
    except Exception:
        return False
    finally:
        s.close()

def http_ok(url, codes_ok):
    try:
        urllib.request.urlopen(url, timeout=8)
        return True
    except urllib.error.HTTPError as e:
        return e.code in codes_ok
    except Exception:
        return False

def revisar():
    fallos = []
    # 1) sucursales
    for nombre, etiqueta in SUCURSALES.items():
        try:
            cred = json.loads((CREDS / f"{nombre}.json").read_text())
        except Exception:
            continue
        if not sql_vivo(cred["server"]):
            fallos.append(f"🔴 {etiqueta}: SQL no responde (compu apagada o sin red)")
    # 2) tablero
    if not http_ok("http://127.0.0.1:8099/", {200}):
        fallos.append("🔴 Tablero de inventario caído (puerto 8099)")
    # 3) pagina de avance (401 = arriba con login)
    if not http_ok("http://100.64.29.43:8100/", {200, 401}):
        fallos.append("🔴 Página de avance caída (puerto 8100)")
    # 4) frescura del tablero
    try:
        edad_min = (time.time() - INV_DATA.stat().st_mtime) / 60
        if edad_min > 40:
            fallos.append(f"🟠 Tablero sin actualizar hace {int(edad_min)} min (el refresco automático pudo atorarse)")
    except Exception:
        fallos.append("🔴 No existe inv_data.json (el refresco nunca corrió)")
    return fallos

def enviar_wa(msg):
    subprocess.run(["openclaw", "message", "send", "--channel", "whatsapp",
                    "--target", RAFAEL_WA, "--message", msg], check=False)

def main():
    fallos = revisar()
    clave = "|".join(sorted(fallos))
    try:
        prev = json.loads(ESTADO.read_text()).get("clave", "")
    except Exception:
        prev = ""

    if clave == prev:
        log(f"sin cambios ({'OK' if not fallos else str(len(fallos))+' fallos'})")
    elif fallos:
        enviar_wa("⚠️ *Titi — chequeo de salud*\n\n" + "\n".join(fallos) +
                  "\n\n(Te aviso solo cuando cambia. Cuando se arregle te mando el OK.)")
        log(f"ALERTA enviada: {clave}")
    else:
        enviar_wa("✅ *Titi — todo recuperado.* El tablero y las 6 sucursales responden bien otra vez.")
        log("RECUPERADO enviado")

    ESTADO.write_text(json.dumps({"clave": clave, "ts": int(time.time())}))

if __name__ == "__main__":
    main()
