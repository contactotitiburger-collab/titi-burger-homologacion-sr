#!/usr/bin/env python3
"""
Health loop nocturno de Tito — corre a las 22:00 todos los días.

Verifica que TODO lo que sostiene el reporte diario de ventas siga sano:
  1. Cron del sistema corriendo.
  2. Internet + portal de Soft Restaurant alcanzable.
  3. El reporte de AYER se generó (ventas_<ayer>.json existe y no está en ceros).
     — a las 22:00, el último reporte que debe existir es el del día anterior.
  4. Gateway de WhatsApp (openclaw) arriba.
  5. Disco con espacio (> 2 GB libres).

Manda UNA línea a Rafael por WhatsApp:
  ✅ si todo está sano   ·   ⚠️ con la lista de lo que falló.

Uso:
  tito_health_loop.py            -> corre chequeos y avisa a Rafael
  tito_health_loop.py --silencioso-si-ok  -> solo avisa si algo falla
"""
import json, subprocess, shutil, sys, socket
from datetime import datetime, timedelta
from pathlib import Path

RAFAEL_WA = "+5216861445614"
OUT = Path("/home/tito/.openclaw/data/reportes_diarios")
LOG = Path("/home/tito/.openclaw/logs/health_loop.log")
SR_PANEL = "https://admin.softrestaurant.com/"


def log(m):
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {m}"
    print(linea)
    with LOG.open("a") as f:
        f.write(linea + "\n")


def check_cron():
    r = subprocess.run(["pgrep", "-x", "cron"], capture_output=True, text=True)
    if r.returncode != 0:
        r = subprocess.run(["pgrep", "-f", "/usr/sbin/cron"], capture_output=True, text=True)
    return (r.returncode == 0, "cron del sistema" if r.returncode == 0 else "cron NO está corriendo")


def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=6).close()
        return True, "internet ok"
    except Exception as e:
        return False, f"sin internet ({type(e).__name__})"


def check_sr():
    try:
        r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                            "--max-time", "20", SR_PANEL],
                           capture_output=True, text=True)
        code = r.stdout.strip()
        ok = code.startswith(("2", "3"))
        return ok, f"Soft Restaurant HTTP {code}"
    except Exception as e:
        return False, f"Soft Restaurant inalcanzable ({type(e).__name__})"


def check_reporte_ayer():
    ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    j = OUT / f"ventas_{ayer}.json"
    if not j.exists():
        return False, f"FALTA el reporte de ayer ({ayer})"
    try:
        d = json.loads(j.read_text())
        total = sum(v.get("total", 0) for v in d.get("hoy", {}).values())
        if total <= 0:
            return False, f"reporte de ayer ({ayer}) salió en CEROS"
        return True, f"reporte de ayer ok (${total:,.0f})"
    except Exception as e:
        return False, f"reporte de ayer ilegible ({type(e).__name__})"


def check_whatsapp():
    # Gateway de openclaw: si el binario responde 'health'/'status' o el proceso vive.
    r = subprocess.run(["pgrep", "-f", "openclaw"], capture_output=True, text=True)
    if r.returncode == 0:
        return True, "gateway WhatsApp arriba"
    return False, "gateway WhatsApp NO detectado"


def check_disco():
    libre_gb = shutil.disk_usage("/").free / 1e9
    ok = libre_gb > 2
    return ok, f"disco {libre_gb:.1f} GB libres"


CHECKS = [
    ("Cron", check_cron),
    ("Internet", check_internet),
    ("Soft Restaurant", check_sr),
    ("Reporte de ayer", check_reporte_ayer),
    ("WhatsApp", check_whatsapp),
    ("Disco", check_disco),
]


def mandar_wa(mensaje):
    cmd = ["openclaw", "message", "send", "--channel", "whatsapp",
           "--target", RAFAEL_WA, "--message", mensaje]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        log("  aviso enviado a Rafael")
        return True
    log(f"  ERROR enviando aviso: {r.stderr.strip()[:200]}")
    return False


def main():
    silencioso = "--silencioso-si-ok" in sys.argv
    log("=== Health loop 22:00 ===")
    fallas = []
    detalles = []
    for nombre, fn in CHECKS:
        try:
            ok, detalle = fn()
        except Exception as e:
            ok, detalle = False, f"error en chequeo ({type(e).__name__}: {e})"
        estado = "ok" if ok else "FALLA"
        log(f"  [{estado}] {nombre}: {detalle}")
        detalles.append((nombre, ok, detalle))
        if not ok:
            fallas.append((nombre, detalle))

    hoy = datetime.now().strftime("%d/%m")
    if fallas:
        cuerpo = "\n".join(f"• {n}: {d}" for n, d in fallas)
        msg = f"⚠️ Tito — chequeo nocturno {hoy}\nEncontré {len(fallas)} problema(s):\n{cuerpo}"
        mandar_wa(msg)
        return 1

    if not silencioso:
        rep = next(d for n, ok, d in detalles if n == "Reporte de ayer")
        mandar_wa(f"✅ Tito — chequeo nocturno {hoy}: todo sano.\n{rep}.")
    log("Todo sano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
