#!/usr/bin/env bash
# Agrega permisos de rsync/scp a la config de Claude Code (Tito) en el Z2.
# Lo corre Rafael con:  ! bash /home/tito/.openclaw/scripts/tito-add-transfer-perms.sh
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home() / '.claude/settings.json'
d = json.loads(p.read_text())
a = d['permissions']['allow']
rules = ['Bash(rsync *)', 'Bash(rsync:*)', 'Bash(scp *)']
added = [r for r in rules if r not in a]
a.extend(added)
p.write_text(json.dumps(d, indent=2))
print('OK — reglas agregadas:', added, '| total:', len(a))
PY
