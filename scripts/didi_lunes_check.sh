#!/bin/bash
# Corre cada lunes ~11am — busca reporte de DiDi en Yahoo y procesa.
# Instalado por Tito 11-jul-2026 a petición de Staff.

LOG=/home/tito/.openclaw/logs/didi_lunes.log
mkdir -p /home/tito/.openclaw/logs

{
  echo "=========================================="
  echo "$(date -Iseconds) — Corriendo DiDi lunes check"
  python3 /home/tito/.openclaw/scripts/didi_procesa_reporte.py
} >> "$LOG" 2>&1
