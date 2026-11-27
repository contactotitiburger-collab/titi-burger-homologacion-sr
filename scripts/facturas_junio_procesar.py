#!/usr/bin/env python3
"""Descarga los XML/adjuntos de las facturas junio 2026 identificadas en el scan y suma totales."""
import imaplib
import json
import re
import email
from email import policy
from email.header import decode_header
from pathlib import Path
from collections import defaultdict
import xml.etree.ElementTree as ET

CREDS = json.loads((Path.home()/".openclaw/credentials/yahoo/creds.json").read_text())
OUT_DIR = Path.home()/".openclaw/data/facturas_junio_2026"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def dec(s):
    if not s: return ""
    try:
        return "".join(t.decode(e or "utf-8", errors="ignore") if isinstance(t, bytes) else t
                       for t, e in decode_header(s))
    except: return str(s)

# leer scan previo para saber qué IDs bajar
scan = json.load(open("/tmp/facturas_junio.json"))
todos = scan["hallazgos"]

# filtrar los que valen la pena descargar (excluir gmail personales no proveedor, cruceros, boletines)
BLACKLIST = ["elimparcial", "norwegian", "capacitaciongubernamental", "aviso.telnor", "fondosbc"]
whitelist = [h for h in todos if not any(b in h["from"].lower() for b in BLACKLIST)]
print(f"De {len(todos)}, descargo {len(whitelist)} candidatos reales.")

M = imaplib.IMAP4_SSL(CREDS.get("imap_host") or "imap.mail.yahoo.com")
M.login(CREDS.get("user") or CREDS.get("email"), CREDS.get("app_password") or CREDS.get("password"))

resultados = []
totales_por_emisor = defaultdict(lambda: {"count": 0, "total": 0.0, "muestra": ""})

def get_ns(t):
    m = re.match(r'\{([^}]+)\}', t)
    return m.group(1) if m else ""

for h in whitelist:
    carp = h["carpeta"]
    try:
        M.select(f'"{carp}"', readonly=True)
        # buscar por From + Date estrictos
        fr_addr = re.search(r'<([^>]+)>', h["from"]) or re.search(r'(\S+@\S+)', h["from"])
        if not fr_addr: continue
        addr = fr_addr.group(1) if fr_addr.groups() else fr_addr.group(0)
        # buscar por From y Subject
        typ, data = M.search(None, f'FROM "{addr}" SUBJECT "{h["subject"][:40].split("=?")[0].strip()}"')
        ids = data[0].split() if data and data[0] else []
        if not ids:
            typ, data = M.search(None, f'FROM "{addr}"')
            ids = data[0].split() if data and data[0] else []
        # tomar el que coincide fecha (aproximado)
        for uid in ids[-5:]:  # último 5, más rápido
            typ, d = M.fetch(uid, "(BODY.PEEK[])")
            if not d or not d[0]: continue
            raw = d[0][1]
            msg = email.message_from_bytes(raw, policy=policy.default)
            # buscar adjuntos xml o pdf
            for part in msg.walk():
                cd = part.get("Content-Disposition") or ""
                fname = part.get_filename() or ""
                fname = dec(fname)
                if not fname: continue
                if fname.lower().endswith((".xml", ".pdf")):
                    contenido = part.get_payload(decode=True)
                    if not contenido: continue
                    safe_name = re.sub(r'[^\w.-]', '_', fname)[:60]
                    dest = OUT_DIR / f"{addr.replace('@','_at_')}__{uid.decode()}__{safe_name}"
                    if not dest.exists():
                        dest.write_bytes(contenido)
                    if fname.lower().endswith(".xml"):
                        try:
                            root = ET.fromstring(contenido)
                            ns = get_ns(root.tag)
                            total = root.get("Total") or root.get("total")
                            if total:
                                total_f = float(total)
                                emisor = None
                                for child in root:
                                    if child.tag.endswith("Emisor"):
                                        emisor = child.get("Nombre") or child.get("Rfc")
                                        break
                                emisor = emisor or addr
                                totales_por_emisor[emisor]["count"] += 1
                                totales_por_emisor[emisor]["total"] += total_f
                                totales_por_emisor[emisor]["muestra"] = safe_name
                                resultados.append({
                                    "emisor": emisor, "total": total_f, "archivo": str(dest),
                                    "fecha": root.get("Fecha", ""), "from": addr,
                                })
                        except Exception as ex:
                            pass
            break  # 1 correo por hallazgo
    except Exception as e:
        print(f"ERROR {addr}: {e}")

M.logout()

# guardar
Path("/tmp/facturas_junio_totales.json").write_text(json.dumps({
    "por_emisor": dict(totales_por_emisor),
    "detalle": resultados,
    "total_general": sum(v["total"] for v in totales_por_emisor.values()),
}, indent=2, ensure_ascii=False))

print("\n=== TOTALES POR EMISOR (JUNIO 2026) ===")
for emisor, info in sorted(totales_por_emisor.items(), key=lambda x: -x[1]["total"]):
    print(f"  ${info['total']:>13,.2f}  ({info['count']:>2})  {emisor[:70]}")
print(f"\nTOTAL GENERAL: ${sum(v['total'] for v in totales_por_emisor.values()):,.2f}")
