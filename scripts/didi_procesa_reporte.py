#!/usr/bin/env python3
"""Cada lunes: revisa Yahoo por correos de DiDi con reporte semanal, procesa y avisa a Staff."""
import imaplib, email, json, subprocess, os
from email.header import decode_header
from pathlib import Path
from datetime import datetime, timedelta

creds = json.loads(Path("/home/tito/.openclaw/credentials/yahoo/creds.json").read_text())
OUT = Path("/home/tito/.openclaw/data/didi_reportes_semanales")
OUT.mkdir(parents=True, exist_ok=True)
STAFF_WA = "+526862040488"  # WhatsApp Staff (Rafael)

def decode_mime(s):
    if s is None: return ""
    parts = decode_header(s)
    return "".join(t.decode(e or "utf-8", errors="replace") if isinstance(t, bytes) else t for t, e in parts)

M = imaplib.IMAP4_SSL(creds["imap_host"], creds["imap_port"])
M.login(creds["user"], creds["password"])
M.select("Inbox", readonly=True)

# Buscar correos DiDi de los últimos 3 días
since_dt = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
found = []
for from_dom in ["didi.com", "didi-food.com", "didiglobal.com"]:
    typ, ids = M.search(None, 'FROM', f'"{from_dom}"', 'SINCE', since_dt)
    for mid in ids[0].split():
        typ, data = M.fetch(mid, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])
        asunto = decode_mime(msg.get("Subject"))
        fecha = msg.get("Date", "")
        # Buscar adjuntos
        attachments = []
        for part in msg.walk():
            if part.get("Content-Disposition"):
                fn = decode_mime(part.get_filename() or "")
                if fn and any(fn.lower().endswith(ext) for ext in [".xlsx", ".csv", ".xls", ".zip"]):
                    dest = OUT / f"{datetime.now().strftime('%Y%m%d')}_{fn}"
                    dest.write_bytes(part.get_payload(decode=True))
                    attachments.append(str(dest))
        found.append({"asunto": asunto, "fecha": fecha, "adjuntos": attachments})

M.logout()

if not found:
    print(f"{datetime.now().isoformat()} — Sin correos DiDi nuevos hoy")
    exit(0)

# Notificar a Staff por WhatsApp (via openclaw)
resumen = f"🍟 Reporte DiDi recibido ({len(found)} correo{'s' if len(found)>1 else ''}):\n\n"
for f in found:
    resumen += f"• {f['asunto'][:80]}\n  adjuntos: {len(f['adjuntos'])}\n"
resumen += "\nYa los descargué. Cuando quieras procesamos los números en el Excel."

# Enviar por WhatsApp
try:
    subprocess.run([
        "openclaw", "message", "send",
        "--to", STAFF_WA,
        "--text", resumen,
    ], timeout=30, check=False)
    print(f"{datetime.now().isoformat()} — WhatsApp enviado a Staff: {len(found)} correos")
except Exception as e:
    print(f"Error WA: {e}")

# Guardar índice
Path("/home/tito/.openclaw/data/didi_reportes_semanales/ultimo_check.json").write_text(
    json.dumps({"fecha": datetime.now().isoformat(), "correos": found}, indent=2, default=str, ensure_ascii=False)
)
