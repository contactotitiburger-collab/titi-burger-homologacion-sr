#!/bin/bash
# One-shot: deshabilita el sistema de "preguntas a Nancy" (retirado 21-jul-2026 por Rafael).
# Programado para hoy 21-jul 20:00. Se auto-elimina del crontab al terminar.
set -e
LOG=/home/tito/.openclaw/logs/deshabilitar_nancy.log
BK=/home/tito/.openclaw/backups
ts=$(date '+%Y-%m-%d %H:%M:%S')
mkdir -p "$BK"

# 1) respaldo del crontab actual
crontab -l > "$BK/crontab_antes_deshabilitar_nancy_$(date +%Y%m%d_%H%M%S).bak" 2>/dev/null || true

# 2) comentar las líneas de los crons de preguntas Nancy (reversible: solo se comentan)
crontab -l 2>/dev/null | sed \
  -e '/nancy_novedades_watch\.py/    s|^\([0-9*]\)|# [OFF 21-jul preguntas-nancy] \1|' \
  -e '/nomina_aplicar_respuestas\.py/ s|^\([0-9*]\)|# [OFF 21-jul preguntas-nancy] \1|' \
  | grep -v 'deshabilitar_preguntas_nancy\.sh' \
  | crontab -

echo "$ts  OFF: nancy_novedades_watch (5pm) + nomina_aplicar_respuestas (mié 2pm). Cron one-shot autoeliminado." >> "$LOG"

# 3) avisar a Rafael
/usr/bin/openclaw message send --channel whatsapp --target "+5216861445614" \
  --message "🍔 Hecho: deshabilité el sistema de preguntas a Nancy (crons nancy_novedades_watch de las 5pm y nomina_aplicar_respuestas de los miércoles). La nómina se sigue generando el lunes normal. Si quieres reactivar algo, nomás dime." >> "$LOG" 2>&1 || echo "$ts  (aviso WA falló, revisar)" >> "$LOG"
