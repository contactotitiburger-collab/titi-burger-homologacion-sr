#!/usr/bin/env python3
"""
Recupera reportes diarios de ventas que NO se enviaron
(típicamente porque la compu estuvo sin internet o apagada a medianoche).

Lógica:
  - Revisa los últimos DIAS_ATRAS días cerrados (ayer hacia atrás).
  - Si NO existe ventas_YYYY-MM-DD.json para ese día, lo genera y lo manda
    llamando al script normal (tito_reporte_diario_donTiti.py --enviar ambos).
  - Para no spamear cuando un día genuinamente no tiene datos, lleva un
    contador de intentos por día; después de MAX_INTENTOS deja de reintentar.

Pensado para correr en cron VARIAS veces al día. En cuanto vuelve el internet,
el siguiente disparo recupera los días perdidos y ya no vuelve a tocarlos
(porque el .json ya existe).
"""
import json, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

DIAS_ATRAS   = 8   # cubre un apagón de hasta una semana completa
MAX_INTENTOS = 4
OUT   = Path("/home/tito/.openclaw/data/reportes_diarios")
STATE = OUT / ".recuperar_intentos.json"
SCRIPT = "/home/tito/.openclaw/scripts/tito_reporte_diario_donTiti.py"
LOG = Path("/home/tito/.openclaw/logs/reporte_diario_recuperar.log")

def log(m):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}  {m}"
    print(line)
    with LOG.open("a") as f:
        f.write(line + "\n")

def cargar_intentos():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            return {}
    return {}

def guardar_intentos(d):
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=1))

def main():
    intentos = cargar_intentos()
    hoy = datetime.now().date()
    recuperados = 0

    for n in range(1, DIAS_ATRAS + 1):
        d = hoy - timedelta(days=n)
        iso = d.strftime("%Y-%m-%d")
        json_dia = OUT / f"ventas_{iso}.json"

        if json_dia.exists():
            continue  # ese día ya está reportado

        veces = intentos.get(iso, 0)
        if veces >= MAX_INTENTOS:
            continue  # ya lo intentamos suficiente; no spamear

        fecha = d.strftime("%d/%m/%Y")
        log(f"Falta reporte del {fecha} (intento {veces+1}/{MAX_INTENTOS}) — recuperando…")
        r = subprocess.run(
            [sys.executable, SCRIPT, "--fecha", fecha, "--enviar", "ambos", "--con-formaspago"],
            capture_output=True, text=True, timeout=900)
        intentos[iso] = veces + 1
        guardar_intentos(intentos)

        if json_dia.exists():
            log(f"  ✓ recuperado y enviado: {fecha}")
            recuperados += 1
        else:
            log(f"  ✗ sin datos todavía para {fecha} (rc={r.returncode}). Reintentaré luego.")

    if recuperados == 0:
        log("Nada que recuperar — todo al día.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
