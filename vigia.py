#!/usr/bin/env python3
"""Vigia rapido (corre en la Z2): revisa cada 1 s si cambió algo de la página (chat privado, foro, respuestas, reportes).
Al ver un mensaje nuevo de Rafael en el chat privado prende 'Tito está escribiendo…' al instante. Imprime qué cambió y termina."""
import json, time, hashlib
from pathlib import Path
B = Path(__file__).resolve().parent
ARCH = ["chat_rafael.json", "foro.json", "respuestas_felix.json", "reportes_estado.json"]
def firma(): return {a: (B / a).stat().st_mtime if (B / a).exists() else 0 for a in ARCH}
antes = firma()
while True:
    time.sleep(1)
    ahora = firma()
    cambio = [a for a in ARCH if ahora[a] != antes[a]]
    if cambio:
        time.sleep(0.3)
        if "chat_rafael.json" in cambio:
            try:
                ch = json.loads((B / "chat_rafael.json").read_text(encoding="utf-8"))
                if ch and ch[-1]["usuario"] == "rafael": (B / ".tito_escribiendo").touch()
            except Exception: pass
        print("CAMBIO:", ", ".join(cambio), time.strftime("%H:%M:%S"), flush=True)
        break
