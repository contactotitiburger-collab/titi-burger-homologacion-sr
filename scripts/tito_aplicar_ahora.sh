#!/bin/bash
# tito_aplicar_ahora.sh — corre cada hora, aplica novedades y celulares
# a la nómina de la semana en curso.
#
# Se dispara por cron cada hora. Detecta la semana ISO actual automático.

set -eo pipefail

# Semana ISO actual (lunes-domingo). Ejemplo: 27 = 29-jun al 5-jul 2026.
SEM=$(date +%V)

# Log rotado
LOG=/tmp/tito-aplicar-ahora.log
{
  echo "=== $(date -Iseconds) — sem $SEM ==="
  /usr/bin/python3 /home/tito/.openclaw/scripts/tito_aplicar_novedades.py --sem "$SEM" 2>&1 || echo "novedades falló"
  /usr/bin/python3 /home/tito/.openclaw/scripts/tito_aplicar_celulares.py --sem "$SEM" 2>&1 || echo "celulares falló"
  echo ""
} >> "$LOG"
