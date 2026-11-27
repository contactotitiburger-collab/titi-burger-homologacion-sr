#!/usr/bin/env python3
"""Cron cada 10 min: detecta una foto NUEVA en el inbound de WhatsApp y,
si llegó una, lanza a Tito (claude headless) para que la clasifique y, si es
un horario de personal, actualice la nómina S29 y mande el borrador flageado
a Rafael. Rafael pidió esto el 20-jul-2026.
"""
import os, glob, json, subprocess, time
from pathlib import Path

INBOX = Path("/home/tito/.openclaw/media/inbound")
MARKER = Path("/home/tito/.openclaw/state/horarios_watch_marker.json")
PROMPT = Path("/home/tito/.openclaw/scripts/horarios_procesar_prompt.txt")
LOG = Path("/home/tito/.openclaw/logs/horarios_watch.log")
MARKER.parent.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(m):
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {m}\n")

def newest_image():
    imgs = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        imgs += glob.glob(str(INBOX / ext))
    if not imgs:
        return None, 0
    newest = max(imgs, key=os.path.getmtime)
    return newest, os.path.getmtime(newest)

def main():
    prev = json.loads(MARKER.read_text()) if MARKER.exists() else {"last_mtime": 0}
    img, mt = newest_image()
    if not img:
        return
    if mt <= prev.get("last_mtime", 0):
        return  # nada nuevo
    # hay imagen nueva -> procesar
    log(f"imagen nueva: {img}")
    MARKER.write_text(json.dumps({"last_mtime": mt, "last_img": img}))
    prompt = PROMPT.read_text().replace("__IMAGE_PATH__", img)
    # lanzar Tito headless en segundo plano (no bloquear el cron)
    try:
        subprocess.Popen(
            ["/home/tito/.npm-global/bin/claude", "-p", prompt,
             "--dangerously-skip-permissions"],
            stdout=open("/home/tito/.openclaw/logs/horarios_procesar.log", "a"),
            stderr=subprocess.STDOUT,
            cwd="/home/tito",
            start_new_session=True,
        )
        log("lanzado claude headless para procesar")
    except Exception as e:
        log(f"ERROR lanzando claude: {e}")

if __name__ == "__main__":
    main()
