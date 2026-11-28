#!/usr/bin/env python3
"""Tito escribe en el chat privado con Rafael (chat_rafael.json).
Uso: python3 responder_privado.py "texto"   |   python3 responder_privado.py --ultimos [n]"""
import json, sys, time, fcntl
from pathlib import Path
F = Path(__file__).resolve().parent / "chat_rafael.json"
if not F.exists(): F.write_text("[]", encoding="utf-8")
if len(sys.argv) >= 2 and sys.argv[1] == "--ultimos":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    for m in json.loads(F.read_text(encoding="utf-8"))[-n:]:
        print(f'#{m["id"]} {m["usuario"]} {m["fecha"]}: {m["texto"]}', [(a["kind"], a["id"]) for a in m.get("adjuntos", [])])
    sys.exit(0)
if len(sys.argv) != 2: sys.exit(__doc__)
with open(F, "r+", encoding="utf-8") as fh:
    fcntl.flock(fh, fcntl.LOCK_EX)
    ch = json.load(fh)
    ch.append({"id": max([x["id"] for x in ch] + [0]) + 1, "usuario": "tito", "fecha": time.strftime("%Y-%m-%d %H:%M"), "texto": sys.argv[1].strip(), "adjuntos": []})
    fh.seek(0); fh.truncate(); json.dump(ch, fh, ensure_ascii=False, indent=1)
print("enviado")
