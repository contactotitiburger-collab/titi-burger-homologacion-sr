#!/usr/bin/env python3
"""Respaldo diario de todo el proyecto Tito Lector (bitacora, registro de horas,
objetivos, fases, scripts) -- guardado local en la Z2, aparte de GitHub.
Corre por systemd timer. Se queda con los ultimos 30 respaldos (uno por dia)."""
import tarfile
from datetime import datetime
from pathlib import Path

ORIGEN = Path("/home/tito/.openclaw/workspace/tito-lector")
DESTINO = Path("/home/tito/.openclaw/backups/tito-lector")
DESTINO.mkdir(parents=True, exist_ok=True)
MAX_RESPALDOS = 30

EXCLUIR = {"__pycache__", ".git"}

def filtro(tarinfo):
    partes = set(Path(tarinfo.name).parts)
    if partes & EXCLUIR:
        return None
    return tarinfo

fecha = datetime.now().strftime("%Y-%m-%d_%H%M")
archivo = DESTINO / f"tito-lector_{fecha}.tar.gz"
with tarfile.open(archivo, "w:gz") as tar:
    tar.add(ORIGEN, arcname="tito-lector", filter=filtro)

print(f"Respaldo guardado: {archivo} ({archivo.stat().st_size // 1024} KB)")

# limpiar respaldos viejos, quedarse solo con los ultimos MAX_RESPALDOS
respaldos = sorted(DESTINO.glob("tito-lector_*.tar.gz"))
for viejo in respaldos[:-MAX_RESPALDOS]:
    viejo.unlink()
    print(f"Borrado respaldo viejo: {viejo.name}")
