#!/usr/bin/env python3
"""Fase 1: recolectar correos de liquidaciones de Uber/Rappi/DiDi desde Yahoo (readonly)."""
import imaplib, email, json, re
from email.header import decode_header
from pathlib import Path
from datetime import datetime

creds = json.loads(Path("/home/tito/.openclaw/credentials/yahoo/creds.json").read_text())
OUT_DIR = Path("/home/tito/.openclaw/data/apps_correos")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Palabras clave por app (para búsqueda por FROM y SUBJECT)
BUSCAR = {
    "uber": {
        "from": ["uber.com", "ubereats.com", "uber-eats.com", "uber-mail.com"],
        "subject_keywords": ["Uber Eats", "Uber", "Pago", "Estado de cuenta", "Payment", "Liquidación", "Deposito", "Depósito"],
    },
    "rappi": {
        "from": ["rappi.com", "rappi.com.mx", "rappipay.com"],
        "subject_keywords": ["Rappi", "Liquidación", "Pago", "Payment", "Deposito", "Depósito"],
    },
    "didi": {
        "from": ["didi.com", "didi-food.com", "didiglobal.com", "d-food.com", "didifood.com"],
        "subject_keywords": ["DiDi", "Didi Food", "Liquidación", "Pago", "Deposito", "Depósito"],
    },
}

def decode_mime(s):
    if s is None: return ""
    parts = decode_header(s)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try: text = text.decode(enc or "utf-8", errors="replace")
            except: text = text.decode("utf-8", errors="replace")
        out.append(text)
    return "".join(out)

M = imaplib.IMAP4_SSL(creds["imap_host"], creds["imap_port"])
M.login(creds["user"], creds["password"])

# READONLY para no tocar nada
M.select("Inbox", readonly=True)

resultados = {"uber": [], "rappi": [], "didi": []}

# Buscar por FROM en Inbox
print("=== INBOX ===")
for app, cfg in BUSCAR.items():
    for from_dom in cfg["from"]:
        typ, ids = M.search(None, 'FROM', f'"{from_dom}"')
        n = len(ids[0].split()) if ids and ids[0] else 0
        if n > 0:
            print(f"  {app.upper():5s} FROM {from_dom:30s} → {n} correos")
            for msg_id in ids[0].split()[:200]:  # tope 200 por app/from
                resultados[app].append(msg_id)

# También buscar en carpetas relevantes: FACTURAS, cortes titi
for folder in ["FACTURAS", '"cortes titi  burgers"', "Archive"]:
    try:
        M.select(folder, readonly=True)
        print(f"\n=== {folder} ===")
        for app, cfg in BUSCAR.items():
            for from_dom in cfg["from"]:
                typ, ids = M.search(None, 'FROM', f'"{from_dom}"')
                n = len(ids[0].split()) if ids and ids[0] else 0
                if n > 0:
                    print(f"  {app.upper():5s} FROM {from_dom:30s} → {n} correos")
    except Exception as e:
        print(f"  Error en {folder}: {e}")

# Descargar los primeros N de Inbox para inspección
M.select("Inbox", readonly=True)
resumen_por_app = {"uber": [], "rappi": [], "didi": []}

for app, msg_ids in resultados.items():
    print(f"\n--- Descargando {app.upper()} (últimos 50 correos) ---")
    unique_ids = list(set(msg_ids))
    # Ordenar por id (más grande = más reciente)
    unique_ids.sort(key=lambda x: int(x), reverse=True)
    for mid in unique_ids[:50]:
        try:
            typ, data = M.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            asunto = decode_mime(msg.get("Subject"))
            remit = decode_mime(msg.get("From"))
            fecha = msg.get("Date")
            # Guardar el .eml completo
            fname = OUT_DIR / f"{app}_{mid.decode()}.eml"
            fname.write_bytes(data[0][1])
            resumen_por_app[app].append({
                "id": mid.decode(),
                "asunto": asunto,
                "remitente": remit,
                "fecha": fecha,
                "file": str(fname),
            })
        except Exception as e:
            print(f"  Error mid={mid}: {e}")

M.logout()

# Guardar índice
(OUT_DIR / "indice.json").write_text(json.dumps(resumen_por_app, indent=2, ensure_ascii=False))
print(f"\nÍndice: {OUT_DIR / 'indice.json'}")
for app, arr in resumen_por_app.items():
    print(f"  {app.upper()}: {len(arr)} correos descargados")
