#!/usr/bin/env python3
"""
Auto-vigilante: avisa a Rafael cuando L Montejano o Montecarlo (u otra carreta
nueva) aparezcan en la red Tailscale, para conectar su SQL y prender su forma de
pago en el reporte diario.

Corre por cron. Manda UNA sola vez por carreta nueva (guarda estado) para no spamear.
"""
import subprocess, json, re
from pathlib import Path
from datetime import datetime

RAFAEL_WA = "+5216861445614"
STATE = Path("/home/tito/.openclaw/state/carretas_sql_vistas.json")
LOG = Path("/home/tito/.openclaw/logs/watch_carretas_sql.log")

# Servidores de carreta que YA están conectados (no avisar de estos).
YA_CONECTADOS = {"tbcurt-servidor", "tbhrio-servidor", "tbsm-servidor", "tbvir-servidor"}


def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {m}\n")


def nodos_servidor():
    r = subprocess.run(["tailscale", "status"], capture_output=True, text=True)
    nodos = set()
    for ln in r.stdout.splitlines():
        m = re.search(r"\s([a-z0-9\-]*servidor)\s", ln, re.I)
        if m:
            nodos.add(m.group(1).lower())
    return nodos


def mandar_wa(msg):
    subprocess.run(["openclaw", "message", "send", "--channel", "whatsapp",
                    "--target", RAFAEL_WA, "--message", msg],
                   capture_output=True, text=True)


def main():
    vistas = set()
    if STATE.exists():
        try:
            vistas = set(json.loads(STATE.read_text()))
        except Exception:
            vistas = set()

    presentes = nodos_servidor()
    nuevas = [n for n in presentes if n not in YA_CONECTADOS and n not in vistas]

    if nuevas:
        lista = ", ".join(nuevas)
        log(f"NUEVAS carretas en la red: {lista}")
        mandar_wa(
            f"🟢 Tito: veo una carreta nueva en la red ({lista}). "
            "Si es Montejano o Montecarlo, dame luz verde y conecto su SQL para "
            "prender su forma de pago en el reporte diario.")
        vistas |= set(nuevas)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(sorted(vistas), ensure_ascii=False))
    else:
        log("sin carretas nuevas")


if __name__ == "__main__":
    main()
