#!/usr/bin/env bash
# Genera (sin enviar) los reportes de los días faltantes 08-13 sep 2026.
set -u
SCRIPT=/home/tito/.openclaw/scripts/tito_reporte_diario_donTiti.py
for f in 08/09/2026 09/09/2026 10/09/2026 11/09/2026 12/09/2026 13/09/2026; do
  echo "===== generando $f ====="
  /usr/bin/python3 "$SCRIPT" --fecha "$f" --enviar ninguno
  echo "rc=$? para $f"
done
echo "LISTO recuperación"
