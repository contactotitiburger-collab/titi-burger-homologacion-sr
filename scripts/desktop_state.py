#!/usr/bin/env python3
"""Registro y limpieza de archivos que Tito deja en el Escritorio de Windows.

Comandos:
  add <path>          Registra un archivo con fecha de hoy (usar tras copiar al Desktop).
  cleanup [--date D]  Borra los archivos registrados con esa fecha (default: hoy).
  list                Lista todo lo registrado.

Estado: ~/.openclaw/state/desktop_tito_files.json
Log:    ~/.openclaw/logs/desktop_cleanup.log
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

STATE = Path.home() / ".openclaw/state/desktop_tito_files.json"
LOG = Path.home() / ".openclaw/logs/desktop_cleanup.log"


def load() -> list[dict]:
    if not STATE.exists():
        return []
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return []


def save(data: list[dict]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a") as f:
        f.write(f"{ts}  {msg}\n")
    print(msg, flush=True)


def cmd_add(path: str) -> None:
    p = Path(path).resolve()
    data = load()
    today = date.today().isoformat()
    # evitar duplicados exactos
    data = [e for e in data if e.get("path") != str(p)]
    data.append({"path": str(p), "added_date": today, "added_at": datetime.now().isoformat(timespec="seconds")})
    save(data)
    log(f"add: {p} ({today})")


def cmd_cleanup(target_date: str | None) -> None:
    d = target_date or date.today().isoformat()
    data = load()
    keep, borrados = [], []
    for e in data:
        if e.get("added_date") == d:
            p = Path(e["path"])
            if p.exists():
                try:
                    p.unlink()
                    borrados.append(str(p))
                except Exception as ex:
                    log(f"ERROR borrando {p}: {ex}")
                    keep.append(e)
            else:
                borrados.append(str(p) + " (ya no existía)")
        else:
            keep.append(e)
    save(keep)
    log(f"cleanup {d}: {len(borrados)} archivos procesados")
    for b in borrados:
        log(f"  · {b}")


def cmd_list() -> None:
    data = load()
    if not data:
        print("(vacío)"); return
    for e in sorted(data, key=lambda x: x.get("added_at", "")):
        p = Path(e["path"])
        marca = "✓" if p.exists() else "✗"
        print(f"  {marca}  {e.get('added_date')}  {e.get('path')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("path")
    c = sub.add_parser("cleanup"); c.add_argument("--date", default=None)
    sub.add_parser("list")
    args = ap.parse_args()
    if args.cmd == "add":
        cmd_add(args.path)
    elif args.cmd == "cleanup":
        cmd_cleanup(args.date)
    elif args.cmd == "list":
        cmd_list()


if __name__ == "__main__":
    main()
