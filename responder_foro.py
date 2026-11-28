#!/usr/bin/env python3
"""Tito contesta una pregunta del foro de la pagina de avance.
Uso: python3 responder_foro.py <id> "respuesta"     |  python3 responder_foro.py --pendientes"""
import json, sys, time, fcntl
from pathlib import Path
F = Path(__file__).resolve().parent / "foro.json"
foro = json.loads(F.read_text(encoding="utf-8")) if F.exists() else []
if len(sys.argv) == 2 and sys.argv[1] == "--pendientes":
    for h in foro:
        if not h["respuestas"]: print(f'#{h["id"]} {h["usuario"]} {h["fecha"]}: {h["texto"]}')
    sys.exit(0)
if len(sys.argv) != 3: sys.exit(__doc__)
hid, txt = int(sys.argv[1]), sys.argv[2].strip()
with open(F, "r+", encoding="utf-8") as fh:
    fcntl.flock(fh, fcntl.LOCK_EX)
    foro = json.load(fh)
    h = next(x for x in foro if x["id"] == hid)
    h["respuestas"].append({"usuario": "tito", "fecha": time.strftime("%Y-%m-%d %H:%M"), "texto": txt})
    fh.seek(0); fh.truncate(); json.dump(foro, fh, ensure_ascii=False, indent=1)
print("respondida", hid)
